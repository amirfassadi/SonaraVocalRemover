"""
FastAPI service exposing VocalRemovalService over HTTP.

This is the "Python Separation Service" the web frontend (built separately,
e.g. via the AI Studio prompt) calls. It does not reimplement any
separation logic — it's a thin HTTP wrapper around
sonara_vocal_remover.service.VocalRemovalService, so the CLI, the Python
API, and this HTTP API all share the exact same code path.

Run with:
    uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from sonara_vocal_remover.config import DEFAULT_DEVICE, DEFAULT_MODEL, SUPPORTED_AUDIO_EXTENSIONS
from sonara_vocal_remover.errors import (
    BlockedUrlError,
    DownloadTimeoutError,
    FileTooLargeError,
    InsufficientGPUMemoryError,
    InvalidLocalFileError,
    InvalidOutputPathError,
    InvalidUrlError,
    MissingFFmpegError,
    MissingModelError,
    ProcessingFailureError,
    ProcessingTimeoutError,
    SonaraError,
    TooManyRedirectsError,
    UnsupportedAudioFormatError,
    UnsupportedUrlSchemeError,
    UrlDownloadError,
)
from sonara_vocal_remover.service import VocalRemovalService
from sonara_vocal_remover.sources import LocalFileSource, UrlSource
from sonara_vocal_remover.sources.url import _validate_url  # reused for /validate-url

OUTPUT_ROOT = Path(tempfile.gettempdir()) / "sonara_jobs"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Sonara Vocal Remover API", version="0.1.0-mvp")
app.mount("/files", StaticFiles(directory=str(OUTPUT_ROOT)), name="files")

# Maps each application error to an HTTP status code. Client errors (bad
# input, blocked URL, unsupported format) -> 400. Server-side/environment
# errors (missing ffmpeg, OOM, processing failure) -> 500/503.
_ERROR_STATUS = {
    InvalidLocalFileError: 400,
    InvalidUrlError: 400,
    UnsupportedUrlSchemeError: 400,
    BlockedUrlError: 400,
    UnsupportedAudioFormatError: 400,
    InvalidOutputPathError: 400,
    UrlDownloadError: 502,
    DownloadTimeoutError: 504,
    ProcessingTimeoutError: 504,
    FileTooLargeError: 413,
    TooManyRedirectsError: 502,
    MissingFFmpegError: 503,
    MissingModelError: 503,
    InsufficientGPUMemoryError: 503,
    ProcessingFailureError: 500,
}


def _error_response(exc: SonaraError) -> JSONResponse:
    status = 500
    for exc_type, code in _ERROR_STATUS.items():
        if isinstance(exc, exc_type):
            status = code
            break
    return JSONResponse(
        status_code=status,
        content={"error": {"type": type(exc).__name__, "message": str(exc)}},
    )


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": "0.1.0-mvp",
        "engine": f"Demucs ({DEFAULT_MODEL})",
        "supported_formats": sorted(SUPPORTED_AUDIO_EXTENSIONS),
    }


@app.post("/api/validate-url")
def validate_url(payload: dict):
    url = payload.get("url")
    if not url or not isinstance(url, str):
        return JSONResponse(status_code=400, content={"valid": False, "message": "URL is required"})
    try:
        _validate_url(url)
    except SonaraError as exc:
        return JSONResponse(status_code=400, content={"valid": False, "message": str(exc)})

    parsed = urlparse(url)
    ext = Path(parsed.path).suffix.lower()
    return {
        "valid": True,
        "hasValidExt": ext in SUPPORTED_AUDIO_EXTENSIONS,
        "hostname": parsed.hostname,
        "protocol": parsed.scheme,
    }


@app.post("/api/separate")
async def separate(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    model: str = Form(DEFAULT_MODEL),
    device: str = Form(DEFAULT_DEVICE),
):
    if not file and not url:
        raise HTTPException(status_code=400, detail="Provide either 'file' or 'url'")
    if file and url:
        raise HTTPException(status_code=400, detail="Provide only one of 'file' or 'url', not both")

    job_id = str(uuid.uuid4())
    job_dir = OUTPUT_ROOT / job_id

    try:
        if url:
            source = UrlSource(url)
        else:
            ext = Path(file.filename or "").suffix.lower()
            if ext not in SUPPORTED_AUDIO_EXTENSIONS:
                supported = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
                raise UnsupportedAudioFormatError(
                    f"Unsupported extension '{ext}'. Supported: {supported}"
                )
            tmp_dir = Path(tempfile.mkdtemp(prefix="sonara_upload_"))
            tmp_path = tmp_dir / f"upload{ext}"
            with open(tmp_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            source = LocalFileSource(str(tmp_path), is_temporary=True)

        service = VocalRemovalService(model=model, device=device)
        result = service.process(source=source, output_dir=str(job_dir))

    except SonaraError as exc:
        return _error_response(exc)

    return {
        "job_id": job_id,
        "vocals_url": f"/files/{job_id}/vocals.wav",
        "instrumental_url": f"/files/{job_id}/instrumental.wav",
        "model": result.model,
        "device": result.device,
        "source_origin": result.source_origin,
    }
