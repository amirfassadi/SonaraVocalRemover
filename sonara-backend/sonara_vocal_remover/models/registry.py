from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import yaml

from sonara_vocal_remover.errors import MissingModelError, SonaraError
from sonara_vocal_remover.models.definition import ModelDefinition


class ModelRegistry:
    def __init__(self, models_dir: str | Path | None = None):
        backend_root = Path(__file__).resolve().parents[2]
        self._models_dir = Path(models_dir) if models_dir is not None else Path(os.environ.get("SONARA_MODELS_DIR", str(backend_root / "Models")))
        self._definitions: dict[str, ModelDefinition] = {}
        self._load()

    def _load(self) -> None:
        if not self._models_dir.exists():
            return

        seen: dict[str, Path] = {}
        for model_dir in sorted(self._models_dir.iterdir(), key=lambda p: p.name):
            if not model_dir.is_dir():
                continue
            model_file = model_dir / "model.yaml"
            if not model_file.exists():
                continue

            try:
                definition = ModelDefinition.from_yaml_path(model_file)
            except SonaraError:
                raise
            except Exception as exc:  # pragma: no cover - defensive guard
                raise SonaraError(f"Failed to load model definition '{model_file}': {exc}") from exc

            model_id = definition.id
            if model_id in seen:
                first_file = seen[model_id]
                raise SonaraError(
                    f"Duplicate model ID '{model_id}' found in '{first_file}' and '{model_file}'."
                )
            seen[model_id] = model_file
            self._definitions[model_id] = definition

    def list_all(self) -> list[ModelDefinition]:
        return list(self._definitions.values())

    def list_enabled(self) -> list[ModelDefinition]:
        return [definition for definition in self.list_all() if definition.status.get("enabled") is True]

    def get(self, model_id: str) -> ModelDefinition:
        if model_id not in self._definitions:
            raise MissingModelError(f"Model '{model_id}' was not found in the registry.")
        return self._definitions[model_id]

    @property
    def models_dir(self) -> Path:
        return self._models_dir
