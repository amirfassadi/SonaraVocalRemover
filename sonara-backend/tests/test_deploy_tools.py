import importlib.util
import os
from pathlib import Path
import pytest
from sonara_vocal_remover.jobs.healthcheck import worker_ready
from sonara_vocal_remover.jobs.store import Store


def load_tool(name):
    path = Path(__file__).resolve().parents[2] / 'tools' / f'{name}.py'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_initialization_protects_credentials_and_existing_config(tmp_path):
    init = load_tool('init_deploy')
    output = tmp_path / 'private/.env'
    init.initialize(output, 'https://karaoke.example.com/')
    config = dict(line.split('=', 1) for line in output.read_text().splitlines())
    assert config['PUBLIC_ORIGIN'] == 'https://karaoke.example.com'
    assert len(config['SONARA_PASSWORD']) >= 12
    assert len(config['SONARA_API_TOKEN']) >= 32
    assert config['SONARA_API_TOKEN'] != config['SONARA_SESSION_SECRET']
    assert os.stat(output).st_mode & 0o777 == 0o600
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        init.initialize(output, 'https://other.example.com')
    assert output.read_bytes() == original
    for origin in ('http://example.com', 'https://example.com/path', 'https://user:pass@example.com', 'https://example.com?x=1', 'https://example.com\nX=Y'):
        with pytest.raises(ValueError):
            init.initialize(tmp_path / 'bad', origin)
    assert not (tmp_path / 'bad').exists()


def test_worker_health_is_read_only_and_rejects_stale_heartbeat(tmp_path):
    assert not worker_ready(tmp_path)
    assert not (tmp_path / 'jobs.sqlite').exists()
    store = Store(tmp_path)
    store.tick()
    assert worker_ready(tmp_path)
    with store.db() as db:
        db.execute('UPDATE heartbeat SET ts=100')
    assert worker_ready(tmp_path, now=110)
    assert not worker_ready(tmp_path, now=115)
    assert not worker_ready(tmp_path, now=99)


class Reply:
    def __init__(self, data, status=200):
        self.data, self.status_code = data, status
    def json(self):
        return self.data


def test_benchmark_measures_processing_and_cleans_up(tmp_path, monkeypatch):
    bench = load_tool('benchmark_karaoke')
    source = tmp_path / 'song.wav'; source.write_bytes(b'not-needed-for-http-test')
    calls = []
    class Session:
        def post(self, url, **kwargs):
            assert kwargs['data'].read() == source.read_bytes()
            return Reply({'job_id': 'abc', 'state': 'queued'}, 202)
        def get(self, url, **kwargs):
            return Reply({'job_id': 'abc', 'state': 'succeeded', 'model_id': 'candidate', 'model_revision': 'fixed',
                          'device': 'cuda', 'created_at': 100, 'started_at': 110, 'finished_at': 120})
        def delete(self, url, **kwargs):
            calls.append(url)
            return Reply({}, 202)
    monkeypatch.setattr(bench.time, 'sleep', lambda _: None)
    result = bench.run_job(Session(), 'https://host', source, 'candidate', duration=60, timeout=10)
    assert result['processing_seconds'] == 10
    assert result['rtf'] == pytest.approx(1/6)
    assert result['device'] == 'cuda'
    assert calls == ['https://host/api/jobs/abc']
    summary = bench.summarize([result, {**result, 'processing_seconds': 8}, {**result, 'processing_seconds': 12}])
    assert summary['candidate']['subsequent_median_seconds'] == 10


def test_benchmark_timeout_still_requests_cleanup(tmp_path, monkeypatch):
    bench = load_tool('benchmark_karaoke')
    source = tmp_path / 'song.wav'; source.touch()
    calls=[]
    class Session:
        def post(self, *args, **kwargs): return Reply({'job_id': 'abc', 'state': 'queued'}, 202)
        def delete(self, url, **kwargs): calls.append(url); return Reply({}, 202)
    with pytest.raises(TimeoutError):
        bench.run_job(Session(), 'https://host', source, 'candidate', 60, timeout=-1)
    assert calls == ['https://host/api/jobs/abc']


def test_cuda_initialization_requires_explicit_matching_wheel_index(tmp_path):
    init = load_tool('init_deploy')
    for device, index in (('cuda', None), ('cuda', 'https://download.pytorch.org/whl/cpu'),
                          ('cpu', 'https://download.pytorch.org/whl/cu128'),
                          ('cuda', 'https://untrusted.example/cu128'), ('bad', None)):
        with pytest.raises(ValueError):
            init.initialize(tmp_path / 'bad.env', 'https://karaoke.example.com', device, index)
    assert not (tmp_path / 'bad.env').exists()
    out = tmp_path / 'gpu.env'
    init.initialize(out, 'https://karaoke.example.com', 'cuda', 'https://download.pytorch.org/whl/cu128')
    assert 'SONARA_DEVICE=cuda\n' in out.read_text()
    assert 'TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128\n' in out.read_text()


def test_gpu_diagnostic_fails_if_cuda_is_unavailable():
    from types import SimpleNamespace
    from sonara_vocal_remover.jobs.gpu_check import inspect_gpu
    with pytest.raises(RuntimeError, match='CUDA unavailable'):
        inspect_gpu(SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)))
