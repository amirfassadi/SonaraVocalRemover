from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SeparationResult:
    """Standard output shape returned to both the CLI and the Python API."""

    vocals_path: Path
    instrumental_path: Path
    model: str
    device: str
    source_origin: str  # "local_file" | "url"
