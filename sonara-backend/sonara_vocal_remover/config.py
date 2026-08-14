"""
Central configuration and security defaults for Sonara Vocal Remover.

These values mirror the "Required Limits" table in the project README.
They are intentionally conservative starting points and can be overridden
per-call (e.g. via CLI flags or API parameters).
"""

from dataclasses import dataclass, field
from typing import FrozenSet


@dataclass(frozen=True)
class DownloadLimits:
    """Security limits enforced by UrlSource's downloader."""

    allowed_schemes: FrozenSet[str] = frozenset({"http", "https"})
    max_size_bytes: int = 200 * 1024 * 1024  # 200 MB
    connect_timeout_seconds: float = 10.0
    total_timeout_seconds: float = 60.0
    max_redirects: int = 3


# Formats considered supported for MVP. This is a deliberately curated list
# (formats FFmpeg decodes reliably and that are worth testing against),
# not "anything FFmpeg can technically decode". Enforced by validation code,
# not just documentation.
SUPPORTED_AUDIO_EXTENSIONS: FrozenSet[str] = frozenset(
    {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
)

# Hostnames/domains treated as "platform pages" rather than direct audio
# resources. These are explicitly out of scope for the MVP URL input path.
BLOCKED_PLATFORM_HOSTS: FrozenSet[str] = frozenset(
    {"youtube.com", "youtu.be", "open.spotify.com", "spotify.com", "soundcloud.com"}
)

# Target separation model. See README "Processing" section: this is a
# target, not a value pinned after benchmarking. Override with --model.
DEFAULT_MODEL = "htdemucs"
DEFAULT_DEVICE = "cpu"

# Processing timeout in seconds. Demucs processing time depends on track
# length and device (CPU is slower than CUDA). 600 seconds (10 minutes) is
# a reasonable MVP default that accommodates typical tracks on CPU.
DEFAULT_PROCESSING_TIMEOUT_SECONDS = 600.0

DEFAULT_LIMITS = DownloadLimits()
