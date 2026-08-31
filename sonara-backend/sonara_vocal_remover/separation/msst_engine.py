from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from sonara_vocal_remover.config import DEFAULT_PROCESSING_TIMEOUT_SECONDS
from sonara_vocal_remover.errors import (
    InsufficientGPUMemoryError,
    MissingModelError,
    ProcessingFailureError,
    ProcessingTimeoutError,
)
from sonara_vocal_remover.models.definition import ModelDefinition
from sonara_vocal_remover.separation.base import SeparationEngine
from sonara_vocal_remover.separation_result import SeparationResult


def _terminate_process_tree(proc: subprocess.Popen[str]) -> None:
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


class MSSTSeparationEngine(SeparationEngine):
    def __init__(
        self,
        model_definition: ModelDefinition | dict,
        *,
        device: str = "cpu",
        timeout_seconds: float = DEFAULT_PROCESSING_TIMEOUT_SECONDS,
        model_cache_dir: str | Path | None = None,
    ):
        self._definition = model_definition if isinstance(model_definition, ModelDefinition) else ModelDefinition.from_mapping(model_definition)
        self._device = device
        self._timeout_seconds = timeout_seconds
        backend_root = Path(__file__).resolve().parents[2]
        self._model_cache_dir = Path(model_cache_dir) if model_cache_dir is not None else backend_root / "model_cache"

    @property
    def model_definition(self) -> ModelDefinition:
        return self._definition

    def _resolve_model_artifacts(self) -> tuple[Path, Path]:
        backend = self._definition.backend or {}
        model_type = str(backend.get("model_type") or self._definition.architecture.get("type") or "")
        artifacts = self._definition.artifacts or {}
        config_meta = artifacts.get("config", {})
        checkpoint_meta = artifacts.get("checkpoint", {})
        config_name = str(config_meta.get("filename") or "")
        checkpoint_name = str(checkpoint_meta.get("filename") or "")

        if not config_name:
            raise MissingModelError(f"Model '{self._definition.id}' is missing an artifact config filename.")
        if not checkpoint_name:
            raise MissingModelError(f"Model '{self._definition.id}' is missing an artifact checkpoint filename.")

        config_path = self._model_cache_dir / config_name
        checkpoint_path = self._model_cache_dir / checkpoint_name

        if not config_path.exists():
            raise MissingModelError(f"MSST config artifact '{config_path}' for model '{self._definition.id}' is missing.")
        if not checkpoint_path.exists():
            raise MissingModelError(f"MSST checkpoint artifact '{checkpoint_path}' for model '{self._definition.id}' is missing.")

        return config_path, checkpoint_path

    def _build_command(self, audio_path: Path, output_dir: Path) -> list[str]:
        backend = self._definition.backend or {}
        model_type = str(backend.get("model_type") or self._definition.architecture.get("type") or "")
        config_path, checkpoint_path = self._resolve_model_artifacts()

        return [
            sys.executable,
            "-m",
            "msst",
            "inference",
            "--model-type",
            model_type,
            "--config",
            str(config_path),
            "--checkpoint",
            str(checkpoint_path),
            "--input",
            str(audio_path),
            "--output",
            str(output_dir),
            "--device",
            self._device,
        ]

    def _generate_instrumental_if_needed(self, audio_path: Path, output_dir: Path) -> None:
        vocals_path = output_dir / "vocals.wav"
        instrumental_path = output_dir / "instrumental.wav"
        if not vocals_path.exists() or instrumental_path.exists():
            return

        if shutil.which("ffmpeg") is None:
            raise ProcessingFailureError(
                "MSST output is missing instrumental.wav and FFmpeg is not available to generate it."
            )

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(audio_path),
            "-i",
            str(vocals_path),
            "-filter_complex",
            "[1:a]volume=-1[a_vocals];[0:a][a_vocals]amix=inputs=2:duration=shortest:dropout_transition=0",
            str(instrumental_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            raise ProcessingFailureError(
                f"Could not derive instrumental.wav from mixture and vocals: {stderr[-500:]}"
            ) from exc

    def separate(self, audio_path: Path, output_dir: Path) -> SeparationResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        required_outputs = self._definition.outputs.get("required", [])
        config_path, checkpoint_path = self._resolve_model_artifacts()
        cmd = self._build_command(audio_path, output_dir)

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
                f"MSST separation exceeded timeout of {self._timeout_seconds} seconds"
            )
        except FileNotFoundError as exc:
            raise ProcessingFailureError(
                "Could not invoke the `msst` module. Is it installed?"
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
            stderr_text = (stderr or "").strip()
            if "CUDA out of memory" in stderr_text or "out of memory" in stderr_text.lower():
                raise InsufficientGPUMemoryError(
                    "GPU ran out of memory during MSST separation. Try --device cpu "
                    "or a shorter/lower-quality input."
                )
            if "not found" in stderr_text.lower() or "No such file" in stderr_text:
                raise MissingModelError(
                    f"MSST model assets not found for '{self._definition.id}': {stderr_text[-500:]}"
                )
            raise ProcessingFailureError(
                f"MSST separation failed (exit {result_returncode}): {stderr_text[-1000:]}"
            )

        vocals_path = output_dir / "vocals.wav"
        if not vocals_path.exists():
            raise ProcessingFailureError(
                f"Expected MSST vocals output not found under {output_dir}. stderr: {(stderr or '')[-500:]}"
            )

        optional_outputs = self._definition.outputs.get("optional", [])
        if "instrumental" in required_outputs or "instrumental" in optional_outputs:
            instrumental_path = output_dir / "instrumental.wav"
            if not instrumental_path.exists():
                self._generate_instrumental_if_needed(audio_path, output_dir)
            if not instrumental_path.exists():
                raise ProcessingFailureError(
                    f"Expected MSST instrumental output not found under {output_dir}."
                )

        # Build stems dict from required and optional outputs
        stems = {}
        for stem_name in required_outputs:
            stem_path = output_dir / f"{stem_name}.wav"
            if stem_path.exists():
                stems[stem_name] = stem_path
        
        for stem_name in optional_outputs:
            stem_path = output_dir / f"{stem_name}.wav"
            if stem_path.exists():
                stems[stem_name] = stem_path

        return SeparationResult(
            model=self._definition.id,
            device=self._device,
            source_origin="",
            stems=stems,
        )
