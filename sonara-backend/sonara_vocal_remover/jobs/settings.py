import os
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Settings:
    root: Path = field(default_factory=lambda: Path(os.environ.get('SONARA_DATA_DIR', 'sonara-data')).resolve())
    cache: Path = field(default_factory=lambda: Path(os.environ.get('SONARA_MODEL_CACHE', 'model_cache')).resolve())
    token: str = field(default_factory=lambda: os.environ.get('SONARA_API_TOKEN', ''))
    default_model: str = field(default_factory=lambda: os.environ.get('SONARA_DEFAULT_MODEL', 'bs_roformer_viperx'))
    device: str = field(default_factory=lambda: os.environ.get('SONARA_DEVICE', 'cpu'))
    max_bytes: int = 200 * 1024 * 1024
    max_seconds: int = 600
    max_pending: int = 3
    min_free_bytes: int = 2 * 1024**3
    timeout: int = field(default_factory=lambda: int(os.environ.get('SONARA_JOB_TIMEOUT', '600')))
    retention: int = 86400
