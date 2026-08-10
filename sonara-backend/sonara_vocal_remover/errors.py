"""
Application-level exceptions.

Low-level exceptions from the downloader, FFmpeg, or the separation model
are translated into one of these so callers (CLI, API) get consistent,
meaningful errors instead of raw stack traces from third-party libraries.
"""


class SonaraError(Exception):
    """Base class for all application-level errors."""


# --- Input errors -----------------------------------------------------

class InvalidLocalFileError(SonaraError):
    """Local file does not exist, isn't readable, or has an unsupported extension."""


class InvalidUrlError(SonaraError):
    """URL is malformed or cannot be parsed."""


class UnsupportedUrlSchemeError(SonaraError):
    """URL scheme is not http/https."""


class BlockedUrlError(SonaraError):
    """URL was rejected by SSRF / private-network / platform-page protections."""


class UrlDownloadError(SonaraError):
    """Generic download failure (connection error, HTTP error, etc.)."""


class DownloadTimeoutError(UrlDownloadError):
    """Download exceeded the configured connect or total timeout."""


class FileTooLargeError(UrlDownloadError):
    """Remote resource exceeded the configured max download size."""


class TooManyRedirectsError(UrlDownloadError):
    """Remote resource exceeded the configured max redirect count."""


class UnsupportedAudioFormatError(SonaraError):
    """Audio format/extension is not in the supported list."""


class CorruptedAudioError(SonaraError):
    """Audio file could not be decoded."""


# --- Environment / processing errors -----------------------------------

class MissingFFmpegError(SonaraError):
    """FFmpeg is not installed or not on PATH."""


class MissingModelError(SonaraError):
    """Separation model weights could not be loaded/found."""


class InsufficientGPUMemoryError(SonaraError):
    """CUDA device ran out of memory during separation."""


class InvalidOutputPathError(SonaraError):
    """Output directory could not be created or written to."""


class ProcessingFailureError(SonaraError):
    """Separation engine failed for a reason not covered above."""
