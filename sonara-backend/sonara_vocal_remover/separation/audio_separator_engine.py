"""Optional, lazily imported RoFormer adapter. One instance can serve many jobs."""
import os
from pathlib import Path
from .base import SeparationEngine
from ..errors import MissingModelError, ProcessingFailureError
from ..separation_result import SeparationResult

class AudioSeparatorEngine(SeparationEngine):
    def __init__(self, definition, device='cpu', cache_dir=None):
        self.definition = definition
        self.device = device
        root = Path(os.environ.get('SONARA_MODEL_CACHE', 'model_cache')).resolve()
        self.cache_dir = Path(cache_dir) if cache_dir else root / definition.id
        self.separator = None

    def load(self):
        if self.separator is not None:
            return
        from audio_separator.separator import Separator
        separator = Separator(model_file_dir=str(self.cache_dir), output_format='WAV',
                              normalization_threshold=1.0, sample_rate=44100,
                              mdxc_params={'batch_size': 1, **self.definition.runtime.get('mdxc_params', {})})
        actual = separator.torch_device.type
        if actual != self.device:
            raise ProcessingFailureError(f'Requested {self.device}, engine selected {actual}; no device fallback allowed.')
        separator.load_model(model_filename=self.definition.backend['model_filename'])
        self.separator = separator

    def separate(self, audio_path, output_dir):
        try:
            self.load()
            output_dir = Path(output_dir).resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
            self.separator.output_dir = str(output_dir)
            self.separator.model_instance.output_dir = str(output_dir)
            self.separator.separate(str(audio_path), custom_output_names={
                'Vocals': 'vocals', 'Instrumental': 'instrumental', 'Other': 'instrumental'})
            stems = {name: output_dir / f'{name}.wav' for name in ('vocals', 'instrumental')}
            if not all(p.is_file() and p.stat().st_size > 44 for p in stems.values()):
                raise ProcessingFailureError('The model did not produce both karaoke stems.')
            return SeparationResult(model=self.definition.id, device=self.device, source_origin='', stems=stems)
        except (MissingModelError, ProcessingFailureError):
            raise
        except ImportError as exc:
            raise MissingModelError('Install requirements-worker.txt before using this backend.') from exc
        except Exception as exc:
            raise ProcessingFailureError('Audio separation failed; see worker logs.') from exc
