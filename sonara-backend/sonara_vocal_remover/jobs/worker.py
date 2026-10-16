"""Linux single-host supervisor; warm model child is killed on cancel/timeout."""
import gc
import json
import logging
import multiprocessing as mp
import os
import shutil
import signal
import time
import zipfile
from pathlib import Path
from .catalog import verify
from .media import normalize, validate_outputs
from .settings import Settings
from .store import Store, TERMINAL
from ..models.definition import ModelDefinition
from ..separation.audio_separator_engine import AudioSeparatorEngine

log = logging.getLogger(__name__)


def inference_loop(connection, settings):
    os.setsid()
    # Kill this entire process group if the supervisor disappears (Linux).
    import ctypes
    libc = ctypes.CDLL(None)
    libc.prctl(1, signal.SIGTERM)
    signal.signal(signal.SIGTERM, lambda *_: os.killpg(os.getpid(), signal.SIGKILL))
    if os.getppid() == 1:
        return
    if settings.device == 'cpu':
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
    engine, key = None, None
    while True:
        job = connection.recv()
        try:
            folder = settings.root / job['id']
            duration = normalize(folder / 'input', folder / 'input.wav', settings.max_seconds)
            current = job['model']['revision']
            if key != current:
                engine = None
                gc.collect()
                verify(job['model'], settings.cache)
                definition = ModelDefinition(**job['model']['definition'])
                engine = AudioSeparatorEngine(definition, job['device'], settings.cache / definition.id)
                engine.load()
                # Loader must not silently replace any pinned asset.
                verify(job['model'], settings.cache)
                key = current
            output = folder / 'output'
            engine.separate(folder / 'input.wav', output)
            validate_outputs(output, duration)
            with zipfile.ZipFile(output / 'karaoke.zip', 'w', compression=zipfile.ZIP_STORED) as archive:
                for stem in ('vocals', 'instrumental'):
                    archive.write(output / f'{stem}.wav', f'{stem}.wav')
            connection.send({'state': 'succeeded'})
        except Exception:
            log.exception('Job failed: %s', job['id'])
            # A failed load must never poison the warm cache.
            engine, key = None, None
            connection.send({'state': 'failed', 'error': 'processing_failed'})


def stop_child(child):
    if child is None:
        return
    if child.is_alive():
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            if child.is_alive():
                child.kill()
        except OSError:
            child.kill()
    child.join(timeout=5)


def cleanup(settings, store):
    now = time.time()
    for row in store.rows():
        state = row['state']
        folder = settings.root / row['id']
        if state == 'running':
            continue
        if row['remove']:
            state = 'deleted'
        elif row['cancel'] and state not in TERMINAL:
            state = 'cancelled'
        elif state == 'succeeded' and now - row['finished'] >= settings.retention:
            state = 'expired'
        elif state == 'uploading' and now - row['created'] > 900:
            state = 'failed'
        if state != row['state']:
            store.finish(row['id'], state, 'upload_interrupted' if row['state'] == 'uploading' else None)
        if state in TERMINAL and state != 'succeeded':
            shutil.rmtree(folder, ignore_errors=True)


def main():
    import fcntl
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    store = Store(settings.root)
    lock = (settings.root / 'worker.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    for row in store.rows():
        if row['state'] == 'running':
            store.finish(row['id'], 'failed', 'worker_interrupted')
    child, parent = None, None
    shutdown = False
    def stop(*_):
        nonlocal shutdown
        shutdown = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        while not shutdown:
            store.tick()
            cleanup(settings, store)
            job = store.claim()
            if job is None:
                time.sleep(0.5)
                continue
            if child is None or not child.is_alive():
                if parent:
                    parent.close()
                parent, other = mp.get_context('spawn').Pipe()
                child = mp.get_context('spawn').Process(target=inference_loop, args=(other, settings))
                child.start()
                other.close()
            try:
                parent.send(job)
                started = time.monotonic()
                while True:
                    store.tick()
                    latest = store.get(job['id'])
                    if shutdown or latest['cancel'] or time.monotonic() - started > settings.timeout:
                        stop_child(child)
                        child = None
                        state = 'deleted' if latest['remove'] else ('cancelled' if latest['cancel'] else 'failed')
                        store.finish(job['id'], state, 'worker_interrupted' if shutdown else 'processing_timeout' if not latest['cancel'] else None)
                        break
                    if parent.poll(0.5):
                        result = parent.recv()
                        # Request cancellation wins even if result arrives at the same moment.
                        latest = store.get(job['id'])
                        state = 'deleted' if latest['remove'] else 'cancelled' if latest['cancel'] else result['state']
                        store.finish(job['id'], state, result.get('error'))
                        break
                    if not child.is_alive():
                        raise RuntimeError('Inference child exited')
            except Exception:
                log.exception('Worker interrupted job %s', job['id'])
                stop_child(child)
                child = None
                store.finish(job['id'], 'failed', 'worker_interrupted')
            finally:
                for name in ('input', 'input.wav'):
                    (settings.root / job['id'] / name).unlink(missing_ok=True)
                cleanup(settings, store)
    finally:
        stop_child(child)
        with store.db() as db:
            db.execute('DELETE FROM heartbeat')

if __name__ == '__main__':
    main()
