# Single-host private pilot

Run from the repository root on a Linux host with Docker Engine and the Compose v2 plugin. This package exposes only the web proxy on host loopback. Put it behind an existing HTTPS reverse proxy to use it from a phone. The internal API has no published port.

## Configure and build

```bash
python3 tools/init_deploy.py --origin https://karaoke.example.com
# Inspect/edit deploy/.env locally; it contains the private pilot password.
docker compose --env-file deploy/.env build
```

The initialization command creates a mode-0600 file and refuses to overwrite it. Keep credentials across restarts. Browser username: `sonara`. No credentials are included in the repository or image build context.

The default image uses CPU PyTorch. Model weights are downloaded at preparation time, not baked into the image. Keep enough disk for image builds, weights and outputs; the API refuses new uploads when less than 2 GiB remains. The worker build needs internet access to Python wheels and package sources.

## Prepare and start

Before starting the services, prepare the models using the worker image and its persistent cache volume:

```bash
docker compose --env-file deploy/.env run --rm --no-deps worker python -m sonara_vocal_remover.prepare_model bs_roformer_viperx
docker compose --env-file deploy/.env run --rm --no-deps worker python -m sonara_vocal_remover.prepare_model melband_kim
docker compose --env-file deploy/.env up -d
docker compose --env-file deploy/.env ps
```

Adapt `deploy/nginx.conf.example` into the HTTPS server block for your domain. Set `PUBLIC_ORIGIN` to precisely the same scheme/host/port used by the phone browser. Open that HTTPS address and sign in. Production session cookies do not work over ordinary HTTP. The loopback port is intended for the TLS reverse proxy, not direct phone access.

API readiness stays unhealthy until the default model has a preparation receipt and the worker has a fresh heartbeat. The web UI remains accessible to show service status. Both Python processes run as UID 10001; Docker-managed volumes keep uploads/outputs and model cache across container replacement. The API mounts the cache read-only, while only worker/preparation can update it. No host CUDA/GPU is used in the CPU configuration.

## RTX 4060 8 GB starting setup

For the supplied i7 13th-generation / 32 GB / RTX 4060 8 GB host, see [RTX4060.md](RTX4060.md). It includes an explicit CUDA initializer and a kernel/memory diagnostic.

## NVIDIA option

Install the NVIDIA driver and NVIDIA Container Toolkit on the target host. In `deploy/.env`, set `SONARA_DEVICE=cuda` and `TORCH_INDEX_URL` to the PyTorch CUDA wheel index compatible with that host. Use the override for **every** build, prepare and start command:

```bash
docker compose --env-file deploy/.env -f compose.yaml -f compose.gpu.yaml build worker
docker compose --env-file deploy/.env -f compose.yaml -f compose.gpu.yaml run --rm --no-deps worker python -m sonara_vocal_remover.jobs.gpu_check
docker compose --env-file deploy/.env -f compose.yaml -f compose.gpu.yaml run --rm --no-deps worker python -m sonara_vocal_remover.prepare_model bs_roformer_viperx
docker compose --env-file deploy/.env -f compose.yaml -f compose.gpu.yaml run --rm --no-deps worker python -m sonara_vocal_remover.prepare_model melband_kim
docker compose --env-file deploy/.env -f compose.yaml -f compose.gpu.yaml up -d --build
```

The adapter rejects a requested/actual device mismatch. CPU-to-GPU settings alone are not evidence of a speedup; run the measurement below on the actual server. The GPU configuration is supplied for operator validation and has not been executed here.

## Measure the actual phone path

Install `sonara-backend/requirements-light.txt` in a local Python environment with FFprobe available. Use a representative song that you can process, preferably several minutes long. Export the password without placing it on the command line:

```bash
read -rs -p 'Sonara password: ' SONARA_PASSWORD
export SONARA_PASSWORD
python tools/benchmark_karaoke.py /absolute/path/song.mp3 --url https://karaoke.example.com --models bs_roformer_viperx melband_kim --repeats 3 --output benchmark-reports/song-01.json
unset SONARA_PASSWORD
```

The script submits sequential jobs through the same password/session proxy as a phone. It records upload time, combined upload/queue time, server processing time, device, pinned model revision and RTF (processing seconds divided by audio seconds). An RTF below 1 means processing is faster than the song duration. It records first and subsequent runs separately without assuming the first run is cold. Processing includes decoding, model loading when needed, inference, output checks and ZIP creation. It does not measure output download time or playback quality.

Each benchmark job is deleted afterwards unless `--keep-results` is specified; unrelated jobs are unaffected. No automatic resubmission occurs if an upload response is lost. A failed run is recorded and produces a nonzero exit code. Reports exclude credentials, full local paths and the source filename. Choose a new output path for each run; earlier reports are never overwritten by a new invocation.

Listen to retained outputs from diverse songs before choosing a default. A shorter synthetic test cannot establish karaoke quality or song-length latency.

## Routine operations

```bash
docker compose --env-file deploy/.env logs --tail=100 api worker web
docker compose --env-file deploy/.env stop
docker compose --env-file deploy/.env up -d
```

`stop`/`up` keeps data. Avoid removing the volumes if you need existing jobs or weights. Stopping a worker interrupts the active job; it is marked failed on restart, while queued jobs survive. Worker cleanup removes expired audio, and the API denies expired downloads independently. SQLite metadata is retained.

For a new model version, create a new model ID and prepare it while keeping existing model assets in place. Do not re-prepare or modify assets that queued/running jobs still reference. To change CPU/CUDA dependencies, stop accepting new work, drain the queue, rebuild/re-prepare using the new environment, then restart.

## Validation boundary

Compose configuration checks, local Python/proxy tests and image builds are separate checks. Docker Engine is not available in the development workspace, so container startup, volume permissions on a real host, TLS routing and GPU execution still need operator validation. CI builds all three CPU images and checks their runtime imports or password gate. GPU image selection and actual container processing remain target-host gates.
