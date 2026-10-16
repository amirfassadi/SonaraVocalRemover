"""
VocalRemovalService: synchronous orchestration for the CLI and Python API.
The asynchronous HTTP worker uses the same engine adapters with job lifecycle handling.

process(source, output_dir) is the canonical entry point. input_path /
input_url keyword arguments are thin convenience wrappers around it — see
docs/LEGACY_README.md "Python API" section.
"""

from dataclasses import replace
from pathlib import Path
from typing import Optional

from sonara_vocal_remover.config import DEFAULT_DEVICE, DEFAULT_MODEL
from sonara_vocal_remover.errors import InvalidOutputPathError, SonaraError
from sonara_vocal_remover.models import ModelRegistry
from sonara_vocal_remover.separation.base import SeparationEngine
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
        from .separation.factory import create_engine
        return create_engine(self._registry.get(model), self._device)

    def _resolve_engine(self, definition):
        from .separation.factory import create_engine
        self._engine = create_engine(definition, self._device)
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
