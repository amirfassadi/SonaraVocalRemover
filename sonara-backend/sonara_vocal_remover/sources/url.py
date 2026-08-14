"""
UrlSource: downloads a directly-downloadable audio URL into a temporary
file, enforcing the security limits described in the README.

Security notes:
- Only http/https are accepted.
- Every hostname (including redirect targets) is resolved and checked
  against private/loopback/link-local ranges *before* connecting, to
  guard against SSRF and DNS-rebinding style bypasses.
- Redirects are followed manually (not via requests' built-in
  allow_redirects) so each hop can be re-validated and counted.
- Download size is enforced while streaming, not just via Content-Length
  (a malicious server can lie about or omit Content-Length).
"""

import ipaddress
import socket
import tempfile
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests

from sonara_vocal_remover.audio_resource import AudioResource
from sonara_vocal_remover.config import (
    BLOCKED_PLATFORM_HOSTS,
    DEFAULT_LIMITS,
    DownloadLimits,
    SUPPORTED_AUDIO_EXTENSIONS,
)
from sonara_vocal_remover.errors import (
    BlockedUrlError,
    DownloadTimeoutError,
    FileTooLargeError,
    InvalidUrlError,
    TooManyRedirectsError,
    UnsupportedAudioFormatError,
    UnsupportedUrlSchemeError,
    UrlDownloadError,
)
from sonara_vocal_remover.sources.base import InputSource

USER_AGENT = "SonaraVocalRemover/0.1 (+https://sonara.example/vocal-remover)"


def _is_private_or_reserved(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _validate_host_is_public(hostname: str) -> None:
    """Resolve hostname and reject if any resolved address is private/internal."""
    try:
        addrinfos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise InvalidUrlError(f"Could not resolve host '{hostname}': {exc}") from exc

    if not addrinfos:
        raise InvalidUrlError(f"Could not resolve host '{hostname}'")

    for family, _, _, _, sockaddr in addrinfos:
        ip_str = sockaddr[0]
        if _is_private_or_reserved(ip_str):
            raise BlockedUrlError(
                f"Access to internal/private address ({hostname} -> {ip_str}) is prohibited."
            )


def _validate_url(url: str) -> None:
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise InvalidUrlError(f"Invalid URL syntax: {url}") from exc

    if parsed.scheme not in DEFAULT_LIMITS.allowed_schemes:
        raise UnsupportedUrlSchemeError(
            f"Unsupported scheme '{parsed.scheme}'. Only http/https are allowed."
        )

    if not parsed.hostname:
        raise InvalidUrlError(f"URL has no hostname: {url}")

    hostname = parsed.hostname.lower()

    if hostname == "localhost" or hostname.endswith(".local"):
        raise BlockedUrlError(f"Access to '{hostname}' is prohibited.")

    for blocked in BLOCKED_PLATFORM_HOSTS:
        if hostname == blocked or hostname.endswith("." + blocked):
            raise BlockedUrlError(
                f"'{hostname}' is a platform page, not a direct audio resource. "
                "YouTube/Spotify/SoundCloud-style URLs are out of scope for the MVP."
            )

    _validate_host_is_public(hostname)


class UrlSource(InputSource):
    """Acquires audio by securely downloading a direct audio URL."""

    def __init__(self, url: str, limits: DownloadLimits = DEFAULT_LIMITS):
        self._url = url
        self._limits = limits

    def acquire(self) -> AudioResource:
        _validate_url(self._url)

        current_url = self._url
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

        for hop in range(self._limits.max_redirects + 1):
            try:
                response = session.get(
                    current_url,
                    stream=True,
                    allow_redirects=False,
                    timeout=(
                        self._limits.connect_timeout_seconds,
                        self._limits.total_timeout_seconds,
                    ),
                )
            except requests.exceptions.Timeout as exc:
                raise DownloadTimeoutError(f"Timed out downloading {current_url}") from exc
            except requests.exceptions.RequestException as exc:
                raise UrlDownloadError(f"Failed to download {current_url}: {exc}") from exc

            if response.is_redirect or response.status_code in (301, 302, 303, 307, 308):
                if hop >= self._limits.max_redirects:
                    raise TooManyRedirectsError(
                        f"Exceeded max redirects ({self._limits.max_redirects})"
                    )
                location = response.headers.get("Location")
                if not location:
                    raise UrlDownloadError("Redirect response missing Location header")
                # Resolve relative redirects (e.g., "/audio/song.mp3") relative to the current URL
                current_url = urljoin(current_url, location)
                _validate_url(current_url)  # re-validate every hop against SSRF/scheme rules
                continue

            if response.status_code >= 400:
                raise UrlDownloadError(
                    f"HTTP error {response.status_code} downloading {current_url}"
                )

            return self._save_stream_to_temp_file(response, current_url)

        raise TooManyRedirectsError(f"Exceeded max redirects ({self._limits.max_redirects})")

    def _save_stream_to_temp_file(self, response: requests.Response, url: str) -> AudioResource:
        # Prefer the URL's path extension; fall back to a generic suffix
        # if absent (e.g. content served without a file-like path).
        url_path = urlparse(url).path
        suffix = Path(url_path).suffix.lower() or ".audio"

        if suffix != ".audio" and suffix not in SUPPORTED_AUDIO_EXTENSIONS:
            raise UnsupportedAudioFormatError(
                f"Unsupported extension '{suffix}' in downloaded URL."
            )

        max_bytes = self._limits.max_size_bytes
        downloaded = 0

        fd, tmp_path_str = tempfile.mkstemp(prefix="sonara_dl_", suffix=suffix)
        tmp_path = Path(tmp_path_str)

        try:
            with open(fd, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 64):
                    if not chunk:
                        continue
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        raise FileTooLargeError(
                            f"Download exceeded max size of {max_bytes} bytes"
                        )
                    f.write(chunk)
        except FileTooLargeError:
            tmp_path.unlink(missing_ok=True)
            raise
        except requests.exceptions.RequestException as exc:
            tmp_path.unlink(missing_ok=True)
            raise UrlDownloadError(f"Download stream failed: {exc}") from exc

        if downloaded == 0:
            tmp_path.unlink(missing_ok=True)
            raise UrlDownloadError(f"Downloaded file is empty: {url}")

        return AudioResource(path=tmp_path, origin="url", is_temporary=True)
