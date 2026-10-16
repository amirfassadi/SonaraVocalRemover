import io
import json
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from api.main import create_app
from sonara_vocal_remover.jobs.settings import Settings
from sonara_vocal_remover.jobs.store import Store
from sonara_vocal_remover.jobs.worker import cleanup
from sonara_vocal_remover.jobs.media import normalize, validate_outputs
from sonara_vocal_remover.jobs import catalog
from sonara_vocal_remover.models import ModelRegistry

HEADERS = {'x-sonara-token': 'test-token', 'x-sonara-owner': 'a' * 32}
SNAPSHOT = {'definition': {'id': 'test-model'}, 'revision': 'fixed-revision', 'receipt': {}}

@pytest.fixture
def setup(tmp_path, monkeypatch):
    settings = Settings(root=tmp_path / 'data', cache=tmp_path / 'cache', token='test-token', min_free_bytes=0)
    monkeypatch.setattr(catalog, 'snapshot', lambda *_: SNAPSHOT)
    monkeypatch.setattr(catalog, 'available', lambda *_: [{'id': settings.default_model, 'name': 'Model', 'revision': 'fixed-revision'}])
    app = create_app(settings)
    app.state.store.tick()
    with TestClient(app, headers=HEADERS) as client:
        yield settings, app.state.store, client


def upload(client, body=b'file-data', filename='song.mp3'):
    return client.post('/api/jobs', params={'filename': filename}, content=body,
                       headers={'content-type': 'application/octet-stream'})


def test_stream_upload_returns_202_and_survives_store_reopen(setup):
    settings, store, client = setup
    response = upload(client)
    assert response.status_code == 202
    job_id = response.json()['job_id']
    assert Store(settings.root).get(job_id)['state'] == 'queued'
    assert (settings.root / job_id / 'input').read_bytes() == b'file-data'
    assert store.claim()['id'] == job_id
    assert client.get(f'/api/jobs/{job_id}').json()['state'] == 'running'


def test_owner_is_required_for_status_and_audio(setup):
    _, store, client = setup
    job_id = upload(client).json()['job_id']
    store.finish(job_id, 'succeeded')
    for suffix in ['', '/stems/instrumental', '/download']:
        assert client.get('/api/jobs/' + job_id + suffix, headers={'x-sonara-owner': 'b' * 32}).status_code == 404
    assert client.get('/api/models', headers={'x-sonara-token': 'wrong'}).status_code == 401


def test_queue_limit_rejects_fourth_and_cancel_frees_capacity(setup):
    settings, store, client = setup
    jobs = [upload(client).json()['job_id'] for _ in range(3)]
    assert upload(client).status_code == 429
    assert client.post(f'/api/jobs/{jobs[0]}/cancel').status_code == 202
    cleanup(settings, store)
    assert store.get(jobs[0])['state'] == 'cancelled'
    assert not (settings.root / jobs[0]).exists()
    assert upload(client).status_code == 202


def test_atomic_claim_and_admission(tmp_path):
    store = Store(tmp_path)
    def submit(i):
        try:
            store.create(str(i), 'owner', 'x', SNAPSHOT, 'cpu', 3)
            store.enqueue(str(i))
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(submit, range(20))) == 3
        claims = list(pool.map(lambda _: store.claim(), range(10)))
    assert len({job['id'] for job in claims if job}) == 3


def test_oversized_empty_unsupported_and_cleanup(setup):
    settings, store, client = setup
    settings.max_bytes = 4
    assert upload(client, b'12345').status_code == 413
    assert upload(client, b'').status_code == 422
    assert upload(client, b'123', 'file.exe').status_code == 422
    assert all(not (settings.root / row['id']).exists() for row in store.rows())


def test_no_worker_no_new_job(setup):
    _, store, client = setup
    with store.db() as db:
        db.execute('DELETE FROM heartbeat')
    assert client.get('/api/health/ready').status_code == 503
    assert upload(client).status_code == 503


def test_public_static_and_legacy_routes_are_unavailable(setup):
    _, _, client = setup
    assert client.get('/files/anything/vocals.wav').status_code == 404
    assert client.post('/api/separate').status_code == 410


def test_stems_range_delete_and_expiry(setup):
    settings, store, client = setup
    job_id = upload(client).json()['job_id']
    out = settings.root / job_id / 'output'
    out.mkdir()
    (out / 'instrumental.wav').write_bytes(b'0123456789')
    (out / 'vocals.wav').write_bytes(b'abcdefghij')
    store.finish(job_id, 'succeeded')
    data = client.get(f'/api/jobs/{job_id}').json()
    assert set(data['stems']) == {'vocals','instrumental'}
    response = client.get(data['stems']['instrumental'], headers={'Range': 'bytes=2-5'})
    assert response.status_code == 206
    assert response.content == b'2345'
    assert client.delete(f'/api/jobs/{job_id}').status_code == 202
    assert client.get(data['stems']['instrumental']).status_code == 410
    cleanup(settings, store)
    assert not out.exists()


def test_expired_output_denied_before_janitor_runs(setup):
    settings, store, client = setup
    job_id = upload(client).json()['job_id']
    store.finish(job_id, 'succeeded')
    settings.retention = -1
    assert client.get(f'/api/jobs/{job_id}').json()['state'] == 'expired'
    assert client.get(f'/api/jobs/{job_id}/stems/vocals').status_code == 410
    cleanup(settings, store)
    assert store.get(job_id)['state'] == 'expired'


def test_snapshot_immutable_after_default_changes(setup):
    settings, store, client = setup
    job_id = upload(client).json()['job_id']
    settings.default_model = 'another-model'
    assert store.get(job_id)['model']['revision'] == 'fixed-revision'
    assert store.get(job_id)['model']['definition']['id'] == 'test-model'


def write_audio(path, seconds=0.2):
    with wave.open(str(path), 'wb') as audio:
        audio.setparams((1, 2, 44100, 0, 'NONE', 'not compressed'))
        audio.writeframes(b'\x01\x00' * int(44100 * seconds))


def test_real_ffmpeg_normalization_and_duration_limits(tmp_path):
    source, target = tmp_path / 'in.wav', tmp_path / 'out.wav'
    write_audio(source)
    assert normalize(source, target, 1) == pytest.approx(0.2)
    with wave.open(str(target)) as audio:
        assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (2, 2, 44100)
    with pytest.raises(ValueError):
        normalize(source, target, 0.1)
    source.write_bytes(b'not audio')
    with pytest.raises(Exception):
        normalize(source, target, 1)


def test_validates_both_outputs(tmp_path):
    for name in ('vocals','instrumental'):
        write_audio(tmp_path / f'{name}.wav')
    validate_outputs(tmp_path, 0.2)
    write_audio(tmp_path / 'vocals.wav', 0.5)
    with pytest.raises(ValueError):
        validate_outputs(tmp_path, 0.2)


def test_disabled_model_has_no_fallback():
    from sonara_vocal_remover.service import VocalRemovalService
    from sonara_vocal_remover.errors import MissingModelError
    with pytest.raises(MissingModelError, match='disabled'):
        VocalRemovalService(model='bs_roformer_viperx_12975')


def test_receipt_pins_weights_and_config(tmp_path, monkeypatch):
    model = ModelRegistry().get('bs_roformer_viperx')
    directory = tmp_path / model.id
    directory.mkdir()
    artifact = directory / 'weights.ckpt'
    artifact.write_bytes(b'weights')
    receipt = {'definition_digest': catalog.digest(asdict(model)), 'package_version': 'test',
               'files': {'weights.ckpt': {'size': 7, 'sha256': catalog.sha256(artifact)}}}
    (directory / 'receipt.json').write_text(json.dumps(receipt))
    monkeypatch.setattr(catalog.importlib.metadata, 'version', lambda _: 'test')
    snap = catalog.snapshot(model.id, tmp_path)
    catalog.verify(snap, tmp_path)
    artifact.write_bytes(b'changed')
    with pytest.raises(ValueError, match='artifact_changed'):
        catalog.verify(snap, tmp_path)
