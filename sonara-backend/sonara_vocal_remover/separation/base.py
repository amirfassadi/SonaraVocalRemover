"""
SeparationEngine abstraction.

htdemucs is the initial (and currently only) implementation. Future
engines/model variants implement this same interface so VocalRemovalService
never needs model-specific logic.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from sonara_vocal_remover.separation_result import SeparationResult


class SeparationEngine(ABC):
    @abstractmethod
    def separate(self, audio_path: Path, output_dir: Path) -> SeparationResult:
        """
        Run source separation on the given audio file and write
        vocals.wav / instrumental.wav into output_dir. Must raise a
        SonaraError subclass on failure (missing model, OOM, corrupted
        audio, etc.) — never leak raw third-party exceptions.
        """
        raise NotImplementedError
