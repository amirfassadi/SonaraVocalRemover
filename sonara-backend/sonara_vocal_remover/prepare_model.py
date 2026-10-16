"""Run offline from web requests: python -m sonara_vocal_remover.prepare_model MODEL_ID."""
import argparse
import importlib.metadata
import json
import os
from dataclasses import asdict
from .jobs.settings import Settings
from .jobs.catalog import digest, sha256
from .models import ModelRegistry
from .separation.audio_separator_engine import AudioSeparatorEngine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('model_id')
    args = parser.parse_args()
    settings = Settings()
    if settings.device == 'cpu':
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
    definition = ModelRegistry().get(args.model_id)
    if definition.backend.get('name') != 'audio_separator' or not definition.status.get('enabled'):
        parser.error('Choose an enabled audio_separator model.')
    cache = settings.cache / definition.id
    cache.mkdir(parents=True, exist_ok=True)
    receipt = cache / 'receipt.json'
    receipt.unlink(missing_ok=True)
    engine = AudioSeparatorEngine(definition, settings.device, cache)
    engine.load()
    files = {str(p.relative_to(cache)): {'sha256': sha256(p), 'size': p.stat().st_size}
             for p in sorted(cache.rglob('*')) if p.is_file() and p.name != 'receipt.json'}
    if not files:
        raise RuntimeError('No downloaded artifacts found.')
    data = {'definition_digest': digest(asdict(definition)), 'files': files,
            'package_version': importlib.metadata.version('audio-separator')}
    receipt.write_text(json.dumps(data, indent=2))
    print(f'Prepared {definition.id}; revision {digest(data)}. Audio quality is not yet certified.')

if __name__ == '__main__':
    main()
