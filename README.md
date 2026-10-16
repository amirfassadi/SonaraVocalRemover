# Sonara Vocal Remover

Private mobile karaoke prototype: upload a song from a phone browser, process it on the server, then play or download the instrumental and vocals.

The web path now uses persistent asynchronous jobs rather than holding an HTTP request open during inference. A Linux worker keeps one model loaded between jobs. BS-RoFormer ViperX and MelBand RoFormer Kim are configurable candidates through `audio-separator`; model quality and target GPU latency still require acceptance testing.

- Persian RTL mobile UI, streaming uploads, real upload progress and job recovery after refresh.
- SQLite queue: one active job and three waiting/uploading jobs per host.
- WAV/MP3/FLAC/M4A/OGG, up to 200 MiB and ten minutes.
- Private password entry, signed browser ownership, authenticated audio streaming with Range support.
- Cancel, delete, processing timeout and 24-hour output retention.
- Model definitions, preparation receipts, artifact hashes and per-job model snapshots.

**Start here:** [setup, API and model switching](docs/KARAOKE_MVP.md).

This is an implementation milestone, not a production speed or audio-quality certification. [Earlier CLI/Demucs documentation](docs/LEGACY_README.md) is historical; its HTTP deployment examples are superseded. The previous `copilot task/SONARA_MVP1_TASK_EN.md` describes an earlier backend-only task, not this mobile milestone.
