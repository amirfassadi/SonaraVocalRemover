"""Private streaming upload API. Run the separate worker alongside this process."""
import asyncio
import hmac
import re
import shutil
import time
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from sonara_vocal_remover.config import SUPPORTED_AUDIO_EXTENSIONS
from sonara_vocal_remover.jobs import catalog
from sonara_vocal_remover.jobs.settings import Settings
from sonara_vocal_remover.jobs.store import Store


def create_app(settings=None):
    settings = settings or Settings()
    store = Store(settings.root)
    app = FastAPI(title='Sonara Karaoke', version='0.2.0')
    app.state.store = store

    @app.middleware('http')
    async def authenticate(request, call_next):
        # Internal service token is injected by the same-origin web proxy, never the browser.
        if not settings.token or not hmac.compare_digest(request.headers.get('x-sonara-token', ''), settings.token):
            return JSONResponse({'error': {'code': 'unauthorized', 'message': 'دسترسی مجاز نیست.'}}, status_code=401)
        owner = request.headers.get('x-sonara-owner', '')
        if not re.fullmatch(r'[a-f0-9]{32}', owner):
            return JSONResponse({'error': {'code': 'unauthorized', 'message': 'نشست معتبر نیست.'}}, status_code=401)
        request.state.owner = owner
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse({'error': {'code': exc.detail, 'message': exc.detail}}, status_code=exc.status_code)

    def ready():
        return (store.alive() and bool(shutil.which('ffmpeg')) and
                shutil.disk_usage(settings.root).free >= settings.min_free_bytes)

    def owned(job_id, owner):
        job = store.get(job_id, owner)
        if not job:
            raise HTTPException(404, 'job_not_found')
        return job

    def serialize(job):
        state = job['state']
        if state == 'succeeded' and (job['remove'] or time.time() - job['finished'] >= settings.retention):
            state = 'deleted' if job['remove'] else 'expired'
        return {'job_id': job['id'], 'filename': job['filename'], 'state': state,
                'model_id': job['model']['definition']['id'], 'model_revision': job['model']['revision'],
                'created_at': job['created'], 'started_at': job['started'], 'finished_at': job['finished'],
                'error': job['error'], 'cancel_requested': bool(job['cancel']),
                'expires_at': job['finished'] + settings.retention if job['finished'] else None,
                'stems': {name: f"/api/jobs/{job['id']}/stems/{name}" for name in ('vocals', 'instrumental')} if state == 'succeeded' else {}}

    @app.get('/api/health/live')
    def live():
        return {'status': 'ok'}

    @app.get('/api/health/ready')
    def readiness():
        models = catalog.available(settings.cache)
        ok = ready() and any(m['id'] == settings.default_model for m in models)
        return JSONResponse({'ready': ok}, status_code=200 if ok else 503)

    @app.get('/api/models')
    def models():
        return {'models': catalog.available(settings.cache), 'default_model': settings.default_model,
                'worker_ready': ready(), 'max_bytes': settings.max_bytes, 'max_seconds': settings.max_seconds}

    @app.post('/api/jobs', status_code=202)
    async def create(request: Request, filename: str, model_id: str | None = None):
        if not ready():
            raise HTTPException(503, 'service_not_ready')
        if Path(filename).suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
            raise HTTPException(422, 'unsupported_format')
        if request.headers.get('content-type', '').split(';')[0] != 'application/octet-stream':
            raise HTTPException(415, 'expected_audio_stream')
        try:
            selected = catalog.snapshot(model_id or settings.default_model, settings.cache)
        except Exception:
            raise HTTPException(422, 'model_not_ready')
        job_id = uuid.uuid4().hex
        try:
            store.create(job_id, request.state.owner, Path(filename).name[:200], selected, settings.device, settings.max_pending)
        except ValueError:
            raise HTTPException(429, 'queue_full')
        folder = settings.root / job_id
        folder.mkdir()
        size = 0
        started = time.monotonic()
        try:
            with (folder / 'input').open('wb') as target:
                async with asyncio.timeout(600):
                    async for block in request.stream():
                        size += len(block)
                        if size > settings.max_bytes:
                            raise HTTPException(413, 'file_too_large')
                        if time.monotonic() - started > 600:
                            raise HTTPException(408, 'upload_timeout')
                        if shutil.disk_usage(settings.root).free < settings.min_free_bytes:
                            raise HTTPException(503, 'storage_full')
                        await run_in_threadpool(target.write, block)
            if size == 0:
                raise HTTPException(422, 'empty_file')
            store.enqueue(job_id)
            return serialize(store.get(job_id))
        except TimeoutError:
            store.finish(job_id, 'failed', 'upload_timeout')
            shutil.rmtree(folder, ignore_errors=True)
            raise HTTPException(408, 'upload_timeout')
        except BaseException:
            store.finish(job_id, 'failed', 'upload_failed')
            shutil.rmtree(folder, ignore_errors=True)
            raise

    @app.get('/api/jobs/{job_id}')
    def status(job_id: str, request: Request):
        return serialize(owned(job_id, request.state.owner))

    @app.post('/api/jobs/{job_id}/cancel', status_code=202)
    def cancel(job_id: str, request: Request):
        job = owned(job_id, request.state.owner)
        if job['state'] in ('uploading', 'queued', 'running'):
            store.request_cancel(job_id)
        return serialize(store.get(job_id))

    @app.delete('/api/jobs/{job_id}', status_code=202)
    def delete(job_id: str, request: Request):
        owned(job_id, request.state.owner)
        store.request_cancel(job_id, remove=True)
        return {'job_id': job_id, 'state': 'deleting'}

    def output(job_id, owner, name):
        job = owned(job_id, owner)
        if serialize(job)['state'] in ('expired', 'deleted'):
            raise HTTPException(410, 'file_expired')
        if job['state'] != 'succeeded':
            raise HTTPException(409, 'job_not_complete')
        path = settings.root / job_id / 'output' / name
        if not path.is_file():
            raise HTTPException(410, 'file_expired')
        return path

    @app.get('/api/jobs/{job_id}/stems/{name}')
    def stem(job_id: str, name: str, request: Request):
        if name not in ('vocals', 'instrumental'):
            raise HTTPException(404, 'stem_not_found')
        return FileResponse(output(job_id, request.state.owner, name + '.wav'), media_type='audio/wav')

    @app.get('/api/jobs/{job_id}/download')
    def download(job_id: str, request: Request):
        return FileResponse(output(job_id, request.state.owner, 'karaoke.zip'), filename='Sonara-karaoke.zip')

    @app.post('/api/separate')
    def legacy():
        raise HTTPException(410, 'use_async_jobs_api')

    return app

app = create_app()
