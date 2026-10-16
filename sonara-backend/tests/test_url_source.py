import pytest

from sonara_vocal_remover.errors import (
    BlockedUrlError,
    InvalidUrlError,
    UnsupportedUrlSchemeError,
)
from sonara_vocal_remover.sources.url import _validate_url


def test_rejects_ftp_scheme():
    with pytest.raises(UnsupportedUrlSchemeError):
        _validate_url("ftp://example.com/song.wav")


def test_rejects_file_scheme():
    with pytest.raises(UnsupportedUrlSchemeError):
        _validate_url("file:///etc/passwd")


def test_rejects_localhost():
    with pytest.raises(BlockedUrlError):
        _validate_url("http://localhost/song.wav")


def test_rejects_loopback_ip():
    with pytest.raises(BlockedUrlError):
        _validate_url("http://127.0.0.1/song.wav")


def test_rejects_private_10_range():
    with pytest.raises(BlockedUrlError):
        _validate_url("http://10.0.0.5/song.wav")


def test_rejects_private_192_168_range():
    with pytest.raises(BlockedUrlError):
        _validate_url("http://192.168.1.1/song.wav")


def test_rejects_link_local():
    with pytest.raises(BlockedUrlError):
        _validate_url("http://169.254.169.254/latest/meta-data")  # cloud metadata endpoint


def test_rejects_youtube():
    with pytest.raises(BlockedUrlError):
        _validate_url("https://www.youtube.com/watch?v=abc123")


def test_rejects_youtu_be():
    with pytest.raises(BlockedUrlError):
        _validate_url("https://youtu.be/abc123")


def test_rejects_spotify():
    with pytest.raises(BlockedUrlError):
        _validate_url("https://open.spotify.com/track/abc123")


def test_rejects_soundcloud():
    with pytest.raises(BlockedUrlError):
        _validate_url("https://soundcloud.com/artist/track")


def test_rejects_malformed_url():
    # A string with no scheme at all is correctly caught by the scheme
    # check (empty scheme != http/https), not the URL-parsing branch.
    with pytest.raises(UnsupportedUrlSchemeError):
        _validate_url("not a url at all")


def test_rejects_url_with_no_hostname():
    with pytest.raises(InvalidUrlError):
        _validate_url("https:///path-with-no-host")


def test_accepts_public_https_url(monkeypatch):
    import socket
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *_: [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))])
    _validate_url("https://example.com/audio/song.mp3")
