from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class SeparationResult:
    """
    Standard output shape returned to both the CLI and the Python API.
    
    Supports both legacy vocal-removal (vocals_path/instrumental_path) and 
    modern multi-stem separation (stems dict). For multi-stem models, stems
    contains all output stems by name. For legacy Demucs, stems will contain
    both 'vocals' and 'instrumental' entries.
    """

    model: str
    device: str
    source_origin: str  # "local_file" | "url"
    stems: Dict[str, Path] = field(default_factory=dict)
    
    # Legacy fields for backward compatibility with vocal-removal workflows
    @property
    def vocals_path(self) -> Path:
        """For backward compatibility: return vocals stem if available."""
        return self.stems.get("vocals", Path(""))
    
    @property
    def instrumental_path(self) -> Path:
        """For backward compatibility: return instrumental stem if available."""
        return self.stems.get("instrumental", Path(""))
