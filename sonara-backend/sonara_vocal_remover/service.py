"""
VocalRemovalService: the single orchestration point used by both the CLI
and the Python API (and, indirectly, the FastAPI wrapper in api/main.py).

process(source, output_dir) is the canonical entry point. input_path /
input_url keyword arguments are thin convenience wrappers around it — see
README "Python API" section.
"""

from dataclasses import replace
from pathlib import Path
from typing import Optional

from sonara_vocal_remover.config import DEFAULT_DEVICE, DEFAULT_MODEL
from sonara_vocal_remover.errors import InvalidOutputPathError, MissingModelError, SonaraError
from sonara_vocal_remover.models import ModelRegistry
from sonara_vocal_remover.separation.base import SeparationEngine
from sonara_vocal_remover.separation.demucs_engine import DemucsSeparationEngine
from sonara_vocal_remover.separation.msst_engine import MSSTSeparationEngine
from sonara_vocal_remover.separation_result import SeparationResult
from sonara_vocal_remover.sources.base import InputSource
from sonara_vocal_remover.sources.local_file import LocalFileSource
from sonara_vocal_remover.sources.url import UrlSource


class VocalRemovalService:
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        device: str = DEFAULT_DEVICE,
        engine: Optional[SeparationEngine] = None,
    ):
        self._model = model
        self._device = device
        self._registry = ModelRegistry()
        self._engine = engine
        if self._engine is None:
            self._engine = self._resolve_engine_for_model(model)

    def _resolve_engine_for_model(self, model: str) -> SeparationEngine:
        """
        Resolve the appropriate separation engine for a given model.
        
        For the default model (htdemucs), use DemucsSeparationEngine directly.
        For any other model, look it up in the registry and select the engine
        based on the model's backend.name metadata.
        
        Unknown models raise MissingModelError (no fallback).
        """
        if model == DEFAULT_MODEL:
            # Default model always uses Demucs
            return DemucsSeparationEngine(model=model, device=self._device)

        # For non-default models, they must exist in the registry
        try:
            definition = self._registry.get(model)
        except MissingModelError:
            # Re-raise: unknown model is an error, not a fallback
            raise

        backend_name = str((definition.backend or {}).get("name", "")).lower()
        if backend_name == "msst":
            return MSSTSeparationEngine(model_definition=definition, device=self._device)
        elif backend_name == "demucs":
            return DemucsSeparationEngine(model=model, device=self._device)
        else:
            raise MissingModelError(
                f"Model '{model}' has unknown backend '{backend_name}'. "
                f"Supported backends: msst, demucs."
            )

    def _resolve_engine(self, definition):
        backend_name = str((definition.backend or {}).get("name", "")).lower()
        if backend_name == "msst":
            self._engine = MSSTSeparationEngine(model_definition=definition, device=self._device)
        else:
            self._engine = DemucsSeparationEngine(model=definition.id, device=self._device)
        return self._engine

    def process(
        self,
        source: Optional[InputSource] = None,
        output_dir: str = "output",
        *,
        input_path: Optional[str] = None,
        input_url: Optional[str] = None,
    ) -> SeparationResult:
        if source is None:
            if input_path is not None:
                source = LocalFileSource(input_path)
            elif input_url is not None:
                source = UrlSource(input_url)
            else:
                raise SonaraError(
                    "Must provide one of: source=, input_path=, input_url="
                )

        out_dir = Path(output_dir)
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise InvalidOutputPathError(f"Cannot create output dir '{out_dir}': {exc}") from exc

        audio = source.acquire()
        try:
            result = self._engine.separate(audio.path, out_dir)
        finally:
            audio.cleanup()

        return replace(result, source_origin=audio.origin)
