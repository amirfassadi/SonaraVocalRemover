# Validation record — 2026-10-16

## Automated checks

- Backend unit/API/FFmpeg suite: 52 passed, 2 skipped (optional model integrations). Optional model tests require prepared assets.
- Opt-in real-model integration test also passed: 1 passed in 56.15 s (three jobs: repeated ViperX, then Kim).
- TypeScript check and Vite/server production build passed.
- A proxy integration check covers password gating, signed session isolation, spoofed owner headers, cross-origin writes and byte forwarding.

## Actual inference smoke run

Ran FastAPI and the Linux worker together, uploaded a two-second synthetic stereo signal via HTTP, polled each job, downloaded both stems and inspected their WAV headers. No fake separator was used.

Environment: Python 3.12.14, audio-separator 0.47.0, PyTorch 2.14.1+cpu, torchaudio 2.11.0+cpu, FFmpeg 6.1.1, CPU only, OMP/MKL threads 2. `pip check` found no broken requirements.

| Run | Model | Worker processing elapsed |
| --- | --- | --- |
| First load | BS-RoFormer ViperX | 25.19 s |
| Next job, cached model | BS-RoFormer ViperX | 22.94 s |
| Switch model | MelBand RoFormer Kim | 8.85 s |

Each result contained vocals and instrumental, stereo PCM16 at 44.1 kHz, exactly 88,200 frames. These are plumbing observations on one synthetic input, not a quality comparison, reliable benchmark or extrapolation to song-length input. Download/preparation time is excluded. No GPU performance claim is made.

The opt-in `tests/test_real_jobs.py` preserves the equivalent scenario for repeatable operator validation. Model assets and generated audio are not committed.

## Limitations

Browser screenshot automation could not start because the available Chromium download returned an invalid archive. Real phone/browser visual and audio checks remain outstanding. The production build passing does not establish mobile acceptance.

No deployment, real-song listening evaluation, GPU run, production load test, or full MVP acceptance has been performed. See KARAOKE_MVP.md for remaining acceptance items.

## Server packaging follow-up

- Added non-root API/worker/web images, CPU Compose and an NVIDIA override, shared persistent volumes, private credential initialization, health checks and HTTPS proxy guidance.
- CPU and merged GPU configurations passed Docker Compose v2.39.4 `config --quiet` locally. This checks configuration, not runtime GPU availability.
- Fresh light Python environment: 56 passed, 2 optional model integrations skipped; TypeScript, production build and proxy integration passed.
- Added benchmark tests for timing/RTF calculation and cleanup, plus tests for private configuration creation and read-only worker health.
- CI now builds all three CPU images, checks runtime imports/password gating and validates both Compose configurations. Local Docker Engine is unavailable; actual image-build results are recorded in GitHub Actions.
- The target server, HTTPS routing, GPU processing and full-song benchmark remain untested.
