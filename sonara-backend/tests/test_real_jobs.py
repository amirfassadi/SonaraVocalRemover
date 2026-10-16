"""Opt-in integration: prepared real weights, real worker, no mocked separation.

SONARA_REAL_MODEL_CACHE=/absolute/prepared/cache python -m pytest -s .../test_real_jobs.py
Synthetic audio validates plumbing only, not perceptual quality or whole-song speed.
"""
import math
import os
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from api.main import create_app
from sonara_vocal_remover.jobs.settings import Settings

@pytest.mark.skipif(not os.environ.get('SONARA_REAL_MODEL_CACHE'), reason='opt-in prepared model integration')
def test_real_models_warm_reuse_and_switch(tmp_path):
    settings = Settings(root=tmp_path / 'data', cache=Path(os.environ['SONARA_REAL_MODEL_CACHE']), token='integration', min_free_bytes=0)
    env = {**os.environ, 'SONARA_DATA_DIR': str(settings.root), 'SONARA_MODEL_CACHE': str(settings.cache),
           'SONARA_DEVICE': 'cpu', 'OMP_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2'}
    source = tmp_path / 'synthetic.wav'
    with wave.open(str(source), 'wb') as audio:
        audio.setparams((2, 2, 44100, 0, 'NONE', 'not compressed'))
        audio.writeframes(b''.join(struct.pack('<hh', int(6000 * math.sin(2*math.pi*220*i/44100)),
                                               int(5000 * math.sin(2*math.pi*330*i/44100))) for i in range(88200)))
    process = subprocess.Popen([sys.executable, '-m', 'sonara_vocal_remover.jobs.worker'],
                               cwd=Path(__file__).resolve().parents[1], env=env)
    try:
        with TestClient(create_app(settings), headers={'x-sonara-token': 'integration', 'x-sonara-owner': 'a'*32}) as client:
            for _ in range(100):
                if client.get('/api/health/ready').status_code == 200:
                    break
                time.sleep(.1)
            else:
                pytest.fail('Worker/default model did not become ready')
            for model in ('bs_roformer_viperx', 'bs_roformer_viperx', 'melband_kim'):
                response = client.post('/api/jobs', params={'filename': source.name, 'model_id': model},
                                       content=source.read_bytes(), headers={'content-type': 'application/octet-stream'})
                assert response.status_code == 202, response.text
                job_id = response.json()['job_id']
                deadline = time.monotonic() + 620
                while time.monotonic() < deadline:
                    job = client.get('/api/jobs/' + job_id).json()
                    if job['state'] in ('succeeded','failed'):
                        break
                    time.sleep(.5)
                assert job['state'] == 'succeeded', job
                print(model, 'seconds:', job['finished_at'] - job['started_at'])
                for name, url in job['stems'].items():
                    result = client.get(url)
                    assert result.status_code == 200
                    out = tmp_path / f'{name}.wav'; out.write_bytes(result.content)
                    with wave.open(str(out)) as audio:
                        assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes()) == (2,2,44100,88200)
                assert client.get(f'/api/jobs/{job_id}/download').status_code == 200
    finally:
        process.terminate()
        process.wait(timeout=15)
