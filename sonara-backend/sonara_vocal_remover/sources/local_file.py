from pathlib import Path

from sonara_vocal_remover.audio_resource import AudioResource
from sonara_vocal_remover.config import SUPPORTED_AUDIO_EXTENSIONS
from sonara_vocal_remover.errors import InvalidLocalFileError, UnsupportedAudioFormatError
from sonara_vocal_remover.sources.base import InputSource


class LocalFileSource(InputSource):
    """Acquires audio from a file already on disk."""

    def __init__(self, path: str, is_temporary: bool = False):
        self._path = Path(path)
        self._is_temporary = is_temporary

    def acquire(self) -> AudioResource:
        if not self._path.exists():
            raise InvalidLocalFileError(f"File not found: {self._path}")
        if not self._path.is_file():
            raise InvalidLocalFileError(f"Not a regular file: {self._path}")

        ext = self._path.suffix.lower()
        if ext not in SUPPORTED_AUDIO_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
            raise UnsupportedAudioFormatError(
                f"Unsupported extension '{ext}'. Supported: {supported}"
            )

        return AudioResource(path=self._path, origin="local_file", is_temporary=self._is_temporary)
