from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from sonara_vocal_remover.errors import SonaraError


REQUIRED_FIELDS = (
    "id",
    "name",
    "architecture",
    "backend",
    "task",
    "outputs",
    "artifacts",
    "status",
)


@dataclass(frozen=True)
class ModelDefinition:
    id: str
    name: str
    provenance: dict[str, Any]
    architecture: dict[str, Any]
    backend: dict[str, Any]
    task: dict[str, Any]
    outputs: dict[str, Any]
    audio: dict[str, Any]
    artifacts: dict[str, Any]
    resources: dict[str, Any]
    runtime: dict[str, Any]
    benchmark: dict[str, Any]
    status: dict[str, Any]
    notes: list[str]

    @classmethod
    def from_yaml_path(cls, path: str | Path) -> "ModelDefinition":
        file_path = Path(path)
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except FileNotFoundError as exc:
            raise SonaraError(f"Model definition file not found: {file_path}") from exc
        except yaml.YAMLError as exc:
            raise SonaraError(f"Malformed YAML in model file '{file_path}': {exc}") from exc

        return cls.from_mapping(data, source=file_path)

    @classmethod
    def from_yaml_text(cls, text: str, *, source: str = "<string>") -> "ModelDefinition":
        try:
            data = yaml.safe_load(text) or {}
        except yaml.YAMLError as exc:
            raise SonaraError(f"Malformed YAML in model file '{source}': {exc}") from exc
        return cls.from_mapping(data, source=source)

    @classmethod
    def from_mapping(cls, data: dict[str, Any], *, source: str = "<memory>") -> "ModelDefinition":
        if not isinstance(data, dict):
            raise SonaraError(f"Model definition '{source}' must contain a YAML mapping at the top level.")

        missing = [field for field in REQUIRED_FIELDS if field not in data]
        if missing:
            joined = ", ".join(missing)
            raise SonaraError(f"Model definition '{source}' is missing required field(s): {joined}")

        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            provenance=data.get("provenance", {}),
            architecture=data.get("architecture", {}),
            backend=data.get("backend", {}),
            task=data.get("task", {}),
            outputs=data.get("outputs", {}),
            audio=data.get("audio", {}),
            artifacts=data.get("artifacts", {}),
            resources=data.get("resources", {}),
            runtime=data.get("runtime", {}),
            benchmark=data.get("benchmark", {}),
            status=data.get("status", {}),
            notes=list(data.get("notes", [])),
        )
