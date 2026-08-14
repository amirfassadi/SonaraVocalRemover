"""
Real Demucs-based separation engine.

Implementation note: this shells out to `python -m demucs` (two-stem mode)
rather than importing demucs' internal Python API directly. Demucs' CLI
surface is more stable across versions than its internal module layout,
and shelling out keeps torch/demucs as an optional, lazily-invoked
dependency — nothing else in this package needs to import torch.

Requires: `pip install demucs` (pulls in torch). See requirements.txt.
"""

import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from sonara_vocal_remover.config import DEFAULT_DEVICE, DEFAULT_MODEL, DEFAULT_PROCESSING_TIMEOUT_SECONDS
from sonara_vocal_remover.errors import (
    InsufficientGPUMemoryError,
    MissingFFmpegError,
    MissingModelError,
    ProcessingFailureError,
    ProcessingTimeoutError,
)
from sonara_vocal_remover.separation.base import SeparationEngine
from sonara_vocal_remover.separation_result import SeparationResult


def _terminate_process_tree(proc: subprocess.Popen[str]) -> None:
    """Terminate the full process tree spawned for Demucs.

    On Windows we prefer the native taskkill /T /F /PID ... mechanism because
    Windows has no process-group API equivalent to os.killpg(). On POSIX we
    start the child in a new session/process group and then signal the group.
    """
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return

        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
    finally:
        if proc.poll() is None:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                except Exception:
                    pass
                try:
                    proc.wait(timeout=10)
                except Exception:
                    pass


class DemucsSeparationEngine(SeparationEngine):
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        device: str = DEFAULT_DEVICE,
        timeout_seconds: float = DEFAULT_PROCESSING_TIMEOUT_SECONDS,
    ):
        self._model = model
        self._device = device
        self._timeout_seconds = timeout_seconds

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

        # Use Popen with manual timeout handling to ensure proper cleanup of child
        # and grandchild processes (e.g., data-loading workers spawned by torch).
        # CREATE_NEW_PROCESS_GROUP on Windows is used to give the Demucs process its
        # own process group for taskkill /T /PID targeting; it does not, by itself,
        # guarantee termination of the entire descendant tree.
        creationflags = 0
        popen_kwargs = {}
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True

        proc = None
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creationflags,
                **popen_kwargs,
            )
            stdout, stderr = proc.communicate(timeout=self._timeout_seconds)
            result_returncode = proc.returncode
        except subprocess.TimeoutExpired:
            try:
                _terminate_process_tree(proc)
                stdout, stderr = proc.communicate()
            except Exception:
                pass
            raise ProcessingTimeoutError(
                f"Demucs separation exceeded timeout of {self._timeout_seconds} seconds"
            )
        except FileNotFoundError as exc:
            raise ProcessingFailureError(
                "Could not invoke the `demucs` module. Is it installed? (pip install demucs)"
            ) from exc
        finally:
            if proc is not None:
                if proc.stdout is not None:
                    try:
                        proc.stdout.close()
                    except Exception:
                        pass
                if proc.stderr is not None:
                    try:
                        proc.stderr.close()
                    except Exception:
                        pass
                if proc.poll() is None:
                    try:
                        proc.wait(timeout=10)
                    except Exception:
                        pass

        if result_returncode != 0:
            stderr = stderr or ""
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
                f"Demucs separation failed (exit {result_returncode}): {stderr.strip()[-1000:]}"
            )

        track_name = audio_path.stem
        stem_dir = demucs_root / self._model / track_name
        raw_vocals = stem_dir / "vocals.wav"
        raw_instrumental = stem_dir / "no_vocals.wav"

        if not raw_vocals.exists() or not raw_instrumental.exists():
            raise ProcessingFailureError(
                f"Expected Demucs output not found under {stem_dir}. "
                f"stdout: {stdout.strip()[-500:]}"
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
