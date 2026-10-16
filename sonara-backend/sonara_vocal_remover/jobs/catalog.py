"""Operator-prepared, content-addressed model receipts; never download on upload."""
import hashlib
import importlib.metadata
import json
from dataclasses import asdict
from pathlib import Path
from ..models import ModelRegistry


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def snapshot(model_id, cache):
    definition = ModelRegistry().get(model_id)
    if not definition.status.get('enabled') or definition.backend.get('name') != 'audio_separator':
        raise ValueError('model_not_available')
    receipt = json.loads((cache / model_id / 'receipt.json').read_text())
    if receipt['definition_digest'] != digest(asdict(definition)) or not receipt['files']:
        raise ValueError('model_changed')
    for name, expected in receipt['files'].items():
        p = (cache / model_id / name).resolve()
        if not p.is_relative_to((cache / model_id).resolve()) or p.stat().st_size != expected['size']:
            raise ValueError('model_artifact_changed')
    return {'definition': asdict(definition), 'receipt': receipt, 'revision': digest(receipt)}


def available(cache):
    result = []
    for model in ModelRegistry().list_enabled():
        try:
            item = snapshot(model.id, cache)
        except (OSError, ValueError, KeyError, importlib.metadata.PackageNotFoundError):
            continue
        result.append({'id': model.id, 'name': model.name, 'revision': item['revision']})
    return result


def verify(snapshot_data, cache):
    model_id = snapshot_data['definition']['id']
    receipt = snapshot_data['receipt']
    if importlib.metadata.version('audio-separator') != receipt['package_version']:
        raise ValueError('runtime_changed')
    for name, expected in receipt['files'].items():
        path = (cache / model_id / name).resolve()
        if not path.is_relative_to((cache / model_id).resolve()) or sha256(path) != expected['sha256']:
            raise ValueError('model_artifact_changed')
