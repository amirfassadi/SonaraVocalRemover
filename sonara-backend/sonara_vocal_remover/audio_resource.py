"""
Canonical audio representation produced by any InputSource.

This is the single shape the separation engine consumes, regardless of
whether the audio originally came from a local file or a downloaded URL.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AudioResource:
    """A local, on-disk audio file ready for processing."""

    path: Path
    origin: str  # "local_file" | "url"
    is_temporary: bool  # True if this file should be cleaned up after processing

    def cleanup(self) -> None:
        """Delete the underlying file if it was created as a temporary artifact."""
        if self.is_temporary and self.path.exists():
            self.path.unlink(missing_ok=True)
