"""Backend selection stays here; orchestration never branches on model names."""
from .demucs_engine import DemucsSeparationEngine
from .msst_engine import MSSTSeparationEngine
from .audio_separator_engine import AudioSeparatorEngine
from ..errors import MissingModelError

BUILDERS = {
    'demucs': lambda d, device: DemucsSeparationEngine(model=d.id, device=device),
    'msst': lambda d, device: MSSTSeparationEngine(model_definition=d, device=device),
    'audio_separator': lambda d, device: AudioSeparatorEngine(d, device),
}

def create_engine(definition, device):
    if definition.status.get('enabled') is not True:
        raise MissingModelError(f"Model '{definition.id}' is disabled.")
    builder = BUILDERS.get(definition.backend.get('name'))
    if builder is None:
        raise MissingModelError(f"Unsupported backend for '{definition.id}'.")
    return builder(definition, device)
