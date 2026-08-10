"""
InputSource abstraction.

Every way of acquiring audio (local file today; URL today; YouTube, cloud
storage, uploads, etc. in the future) implements this same interface, so
the separation engine never needs to know where the audio came from.
"""

from abc import ABC, abstractmethod

from sonara_vocal_remover.audio_resource import AudioResource


class InputSource(ABC):
    """Base class for anything that can produce an AudioResource."""

    @abstractmethod
    def acquire(self) -> AudioResource:
        """
        Acquire the audio and return a canonical AudioResource pointing at
        a local file on disk. Must raise a SonaraError subclass (see
        errors.py) on failure — never leak raw third-party exceptions.
        """
        raise NotImplementedError
