"""
Real Demucs-based separation engine.

Implementation note: this shells out to `python -m demucs` (two-stem mode)
rather than importing demucs' internal Python API directly. Demucs' CLI
surface is more stable across versions than its internal module layout,
and shelling out keeps torch/demucs as an optional, lazily-invoked
dependency — nothing else in this package needs to import torch.

Requires: `pip install demucs` (pulls in torch). See requirements.txt.
"""

import shutil
import subprocess
import sys
from pathlib import Path

from sonara_vocal_remover.config import DEFAULT_DEVICE, DEFAULT_MODEL
from sonara_vocal_remover.errors import (
    InsufficientGPUMemoryError,
    MissingFFmpegError,
    MissingModelError,
    ProcessingFailureError,
)
from sonara_vocal_remover.separation.base import SeparationEngine
from sonara_vocal_remover.separation_result import SeparationResult


class DemucsSeparationEngine(SeparationEngine):
    def __init__(self, model: str = DEFAULT_MODEL, device: str = DEFAULT_DEVICE):
        self._model = model
        self._device = device

    def separate(self, audio_path: Path, output_dir: Path) -> SeparationResult:
        if shutil.which("ffmpeg") is None:
            raise MissingFFmpegError(
                "FFmpeg is not installed or not on PATH. Install it and try again."
            )

        output_dir.mkdir(parents=True, exist_ok=True)
        demucs_root = output_dir / "_demucs_raw"
        demucs_root.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            "-m",
            "demucs",
            "-n",
            self._model,
            "-d",
            self._device,
            "--two-stems",
            "vocals",
            "-o",
            str(demucs_root),
            str(audio_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=None,  # separation time is track-length dependent; caller controls overall timeout
            )
        except FileNotFoundError as exc:
            raise ProcessingFailureError(
                "Could not invoke the `demucs` module. Is it installed? (pip install demucs)"
            ) from exc

        if result.returncode != 0:
            stderr = result.stderr or ""
            if "CUDA out of memory" in stderr or "out of memory" in stderr.lower():
                raise InsufficientGPUMemoryError(
                    "GPU ran out of memory during separation. Try --device cpu "
                    "or a shorter/lower-quality input."
                )
            if "not found" in stderr.lower() and self._model in stderr:
                raise MissingModelError(
                    f"Could not load model '{self._model}': {stderr.strip()[-500:]}"
                )
            raise ProcessingFailureError(
                f"Demucs separation failed (exit {result.returncode}): {stderr.strip()[-1000:]}"
            )

        track_name = audio_path.stem
        stem_dir = demucs_root / self._model / track_name
        raw_vocals = stem_dir / "vocals.wav"
        raw_instrumental = stem_dir / "no_vocals.wav"

        if not raw_vocals.exists() or not raw_instrumental.exists():
            raise ProcessingFailureError(
                f"Expected Demucs output not found under {stem_dir}. "
                f"stdout: {result.stdout.strip()[-500:]}"
            )

        final_vocals = output_dir / "vocals.wav"
        final_instrumental = output_dir / "instrumental.wav"
        shutil.move(str(raw_vocals), str(final_vocals))
        shutil.move(str(raw_instrumental), str(final_instrumental))
        shutil.rmtree(demucs_root, ignore_errors=True)

        return SeparationResult(
            vocals_path=final_vocals,
            instrumental_path=final_instrumental,
            model=self._model,
            device=self._device,
            source_origin="",  # filled in by VocalRemovalService
        )
