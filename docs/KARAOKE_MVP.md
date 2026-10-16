# Mobile karaoke milestone

## Scope and architecture

Phone browser → same-origin Node streaming proxy → FastAPI/SQLite queue → separate Linux inference worker → private WAV/ZIP downloads.

The browser sends file bytes once, then polls status. No inference runs inside the upload request. Closing the page after the job ID is received does not stop processing. The last ID is stored locally; ownership lives in a signed HttpOnly cookie. Clearing cookies loses access to earlier jobs. A lost upload response is not automatically recovered: resumable uploads and idempotent submission remain follow-up work.

One worker per data directory is enforced by an OS lock. A long-lived subprocess keeps the model loaded for subsequent jobs. Changing model replaces the cached engine. Cancellation and timeout kill the subprocess group and release its memory. The next job reloads the model. Interrupted active jobs fail explicitly on restart; queued jobs remain queued. SQLite is for one host, not distributed/NFS deployment.

## Local setup

Use Linux, Python 3.12+, Node 22+, FFmpeg and a C/C++ build toolchain (for diffq). The commands below run from the repository root unless indicated.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
CC=gcc CXX=g++ pip install -r sonara-backend/requirements-worker.txt
```

For NVIDIA deployment install a matching CUDA PyTorch/torchaudio wheel set instead and set `SONARA_DEVICE=cuda`. Device mismatch fails explicitly; there is no silent fallback to CPU. This branch has not been benchmarked on a GPU.

Set the same absolute data/cache paths in API and worker environments. Keep model cache operator-writable only. Do not change model assets while jobs are queued; use a new model ID for a new release.

```bash
export SONARA_DATA_DIR="$PWD/sonara-data"
export SONARA_MODEL_CACHE="$PWD/model_cache"
export SONARA_DEVICE=cpu
export SONARA_DEFAULT_MODEL=bs_roformer_viperx
export SONARA_API_TOKEN="$(openssl rand -hex 32)"
export SONARA_SESSION_SECRET="$(openssl rand -hex 32)"
export SONARA_PASSWORD="$(openssl rand -hex 16)"
```

Save the generated credentials privately and reuse them across shells/restarts. Browser login username is `sonara`. Node and Python must share `SONARA_API_TOKEN`. Never commit credentials or put them in Vite client variables.

Prepare models once (downloads weights and records hashes; not an audio-quality approval):

```bash
cd sonara-backend
python -m sonara_vocal_remover.prepare_model bs_roformer_viperx
python -m sonara_vocal_remover.prepare_model melband_kim
```

Run these two processes in separate shells from `sonara-backend`, with the same environment:

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000
python -m sonara_vocal_remover.jobs.worker
```

The API can use `requirements-light.txt` in a separate environment; the worker must have `requirements-worker.txt`. Both share the database, job directories and prepared model cache. Keep the internal API bound to loopback or a private network.

From `sonara-vocal-remover`, with credentials exported:

```bash
npm ci
npm run dev
```

Open http://127.0.0.1:3000. For phone access deploy behind HTTPS, set `PUBLIC_ORIGIN` to the exact public origin, run `npm run build` then `NODE_ENV=production npm start`. Production cookies require HTTPS. Configure the reverse proxy for streaming (request buffering off), 200 MiB uploads and at least a ten-minute upload timeout. Do not expose this private pilot without the password. Account management, brute-force rate limits and public multi-tenant operation are outside this milestone.

## Models and adding one

Definitions live in `sonara-backend/Models/<id>/model.yaml`; `SONARA_MODELS_DIR` can override the registry directory.

1. Copy an existing RoFormer definition to a new ID. Set name, architecture, `backend.model_filename` and runtime parameters compatible with the installed audio-separator version.
2. Prepare it with `python -m sonara_vocal_remover.prepare_model <id>`.
3. Inspect the receipt, upstream checkpoint provenance/license and actual audio output. Benchmark representative songs before selecting it as the default.
4. Set `SONARA_DEFAULT_MODEL=<id>` and restart the API; available models also appear in the advanced selector. No frontend or HTTP handler changes are required.

A new architecture already supported by audio-separator follows the same path if it produces both required stems. A genuinely new runtime needs a `SeparationEngine` adapter and registration in `separation/factory.py`; operator preparation and worker support must also be extended before it can be exposed through the job catalog. The current async catalog intentionally accepts only the audio-separator backend. Legacy Demucs remains available through the CLI/Python service.

The receipt pins the model definition, artifact hashes and audio-separator version. Admission checks receipt metadata and artifact sizes; the worker verifies hashes and package version before loading a new engine and checks again after loading. Each job stores its snapshot, so changing the default does not redirect queued jobs to another model. Editing or removing assets needed by queued jobs makes those jobs fail rather than silently substitute a model.

Candidates:

| ID | Checkpoint | Status |
| --- | --- | --- |
| `bs_roformer_viperx` | `model_bs_roformer_ep_317_sdr_12.9755.ckpt` | Default candidate, requires local preparation |
| `melband_kim` | `vocals_mel_band_roformer.ckpt` | Alternate candidate, requires local preparation |

References: [audio-separator](https://github.com/nomadkaraoke/python-audio-separator), [upstream separation training tools](https://github.com/ZFTurbo/Music-Source-Separation-Training).

## API (through the web proxy)

| Method/path | Behavior |
| --- | --- |
| `GET /api/models` | Prepared models, default, worker readiness, limits |
| `POST /api/jobs?filename=song.mp3&model_id=...` | Raw bytes, `Content-Type: application/octet-stream`; 202 with job ID after upload |
| `GET /api/jobs/{id}` | State, timestamps, model revision, errors and stem URLs |
| `POST /api/jobs/{id}/cancel` | Request cancellation, 202 |
| `DELETE /api/jobs/{id}` | Request deletion, 202; successful outputs become inaccessible immediately |
| `GET /api/jobs/{id}/stems/instrumental` | Private WAV, supports byte ranges |
| `GET /api/jobs/{id}/stems/vocals` | Private WAV |
| `GET /api/jobs/{id}/download` | ZIP containing both stems |
| `GET /api/health/live` / `ready` | Process liveness / worker, storage, FFmpeg and default-model availability |

States: `uploading`, `queued`, `running`, `succeeded`, `failed`, `cancelled`, `expired`, `deleted`. Internal API additionally requires `x-sonara-token` and a validated 32-hex `x-sonara-owner`, injected by Node. Readiness is not a guarantee against a later hardware or inference failure.

Common responses: 401 unauthorized, 404 wrong owner/missing job, 410 expired/deleted file, 413 oversized input, 422 unsupported/empty input or unprepared model, 429 queue full, 503 worker/storage unavailable. Invalid audio and duration violations detected during decoding fail the asynchronous job. Original uploads are removed after processing; output expires after 24 hours. Cleanup runs with the worker, while API expiry enforcement applies even if the worker is offline. SQLite job metadata is retained; metadata pruning is future work.

Breaking change: the old synchronous `POST /api/separate` returns 410, and public `/files` is removed. HTTP URL ingestion is not included in this mobile upload milestone; the existing CLI URL source remains available.

## Validation and remaining acceptance

```bash
python -m pytest -q sonara-backend/tests
cd sonara-vocal-remover
npm run lint
npm run build
```

Automated tests cover durable queue admission/claiming, owner isolation, cancellation cleanup, bounds, expiry, byte ranges, real FFmpeg conversion, model snapshotting and artifact tampering. They do not measure perceptual separation quality.

Before calling the MVP complete:

- Benchmark cold and warm processing on the actual server/GPU, using full-length songs and concurrent uploads. Choose quality/speed defaults from measurements; 600 seconds is a provisional timeout (`SONARA_JOB_TIMEOUT`).
- Listen to at least ten diverse songs, including Persian vocals, backing vocals and reverberation. Confirm both candidate models and checkpoint licensing for intended deployment.
- Verify real iOS Safari/Android uploads, backgrounding, playback, seeking and downloads.
- Validate gain/clipping behavior: the upstream separator can adjust individual stem levels. Strict shared gain, finite-float checks and reconstruction-error gates are not implemented.
- Synchronized two-stem mixing, URL ingestion, resumable/idempotent uploads and distributed workers remain outside this first slice.

Do not infer whole-song speed or karaoke quality from a synthetic smoke test.
