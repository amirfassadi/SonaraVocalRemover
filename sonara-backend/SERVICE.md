# Sonara Vocal Remover — Python Backend

Real implementation of the architecture described in the project README:
`InputSource` (`LocalFileSource`, `UrlSource`) → `SeparationEngine`
(`DemucsSeparationEngine`) → `SeparationResult`, exposed three ways that
all share the exact same code path:

1. **CLI** — `python -m sonara_vocal_remover ...`
2. **Python API** — `from sonara_vocal_remover import VocalRemovalService`
3. **HTTP API** (`api/main.py`) — for the web frontend to call

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # includes demucs (pulls in torch — heavy)
```

FFmpeg must also be installed and on `PATH`.

> If you only want to run the tests for the input/security logic (no real
> separation), you can skip `demucs`/`torch` — only `requests`, `fastapi`,
> `pytest` are needed for that.

## Run the CLI

```bash
python -m sonara_vocal_remover input/song.wav --output output/song
python -m sonara_vocal_remover "https://example.com/song.mp3" --device cuda
```

## Run the HTTP API (for the web frontend)

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Endpoints:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Status, version, supported formats |
| `POST` | `/api/validate-url` | `{"url": "..."}` → validation result, without downloading |
| `POST` | `/api/separate` | multipart form: `file` **or** `url`, plus optional `model`/`device` → job result with stem URLs |
| `GET` | `/files/{job_id}/vocals.wav` | Static download of a completed stem |

`/api/separate` response shape:

```json
{
  "job_id": "…",
  "vocals_url": "/files/…/vocals.wav",
  "instrumental_url": "/files/…/instrumental.wav",
  "model": "htdemucs",
  "device": "cpu",
  "source_origin": "local_file"
}
```

Errors come back as:

```json
{ "error": { "type": "BlockedUrlError", "message": "..." } }
```

with an appropriate HTTP status code (see `_ERROR_STATUS` in `api/main.py`).

## Tests

```bash
pytest tests/ -v
```

Current coverage focuses on the security-critical `UrlSource` validation
(SSRF protection, scheme checks, platform-URL blocking) and `LocalFileSource`
validation — the parts of the system that don't require the heavy
Demucs/torch install to test. Separation-engine tests (real Demucs runs)
are intentionally not included yet; they need model weights downloaded and
are slow/hardware-dependent — add them once a CI environment with
appropriate resources is available.

## What's real vs. what's still a target

- ✅ **Real**: `InputSource`/`LocalFileSource`/`UrlSource`, SSRF protection,
  scheme/format validation, size/timeout/redirect enforcement, the CLI,
  the Python API, the FastAPI wrapper, error mapping.
- ✅ **Real** (given `demucs` installed): `DemucsSeparationEngine` — this
  actually shells out to Demucs and produces real `vocals.wav` /
  `instrumental.wav`, not a fake DSP trick.
- 🎯 **Still target, not pinned**: exact `htdemucs` checkpoint/version,
  exact output sample rate/bit depth behavior (inherits whatever Demucs
  produces — not yet verified against the README's "preserve source
  quality" goal).
