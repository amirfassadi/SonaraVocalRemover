# Sonara Vocal Remover

AI-powered vocal removal and music source separation engine for the Sonara platform.

Sonara Vocal Remover is a standalone audio-processing component designed to extract vocals from music and produce a high-quality instrumental version of a song.

> **Status:** 🚧 Early development (MVP in progress). See [Roadmap](#roadmap) for current progress — nothing below is production-ready yet.

The MVP focuses on one core capability:

> Remove vocals from a music track while preserving the original instrumental content and stereo quality as much as possible.

The project is designed as a reusable processing engine that can later be integrated into web applications, APIs, desktop applications, and other Sonara services.

---

## Table of Contents

- [MVP Scope](#mvp-scope)
- [Installation](#installation)
- [Usage](#usage)
- [Python API](#python-api)
- [Input Architecture](#input-architecture)
- [Security Considerations](#security-considerations-for-url-input)
- [Output Format](#output-format)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [License](#license)

---

## MVP Scope

The first release intentionally keeps the product focused.

### Input

The MVP accepts audio from two sources:

- Local audio files
- Direct audio URLs

Examples:

```
# Local file
./input/song.wav

# Direct URL
https://example.com/audio/song.wav
```

A URL must point to a directly downloadable audio resource.

The MVP does **not** treat arbitrary web pages as audio sources. Services such as YouTube, Spotify, SoundCloud pages, or other platform URLs are outside the initial scope unless a dedicated downloader integration is added later.

**Supported local/remote input formats (MVP, target):** `.wav`, `.mp3`, `.flac`, `.m4a`, `.ogg`

> This list reflects formats FFmpeg can decode reliably and that are worth testing against for MVP — not "anything FFmpeg supports." It should be finalized (and locked down in validation code) before implementation, not expanded ad hoc afterward.

**Not automatically supported:**

```
https://youtube.com/...
https://youtu.be/...
https://open.spotify.com/...
https://soundcloud.com/...
```

These URLs generally point to web pages or streaming services rather than directly downloadable audio files. Support for such platforms can be introduced later through dedicated source/download adapters.

### Processing

AI-based music source separation using [Demucs](https://github.com/facebookresearch/demucs) as the initial separation engine.

**Target model variant:** `htdemucs` (Hybrid Transformer Demucs), pinned to a specific released version once implementation starts.

> The exact model variant matters: quality, inference speed, and VRAM usage all vary meaningfully between Demucs variants (e.g. `htdemucs` vs `htdemucs_ft` vs `mdx_extra`). `htdemucs` is the current target as a balance of quality and speed, but this should be confirmed and pinned to an exact version/checkpoint before the MVP is considered feature-complete — "Demucs" alone is not a sufficient specification for a project whose stated goal is separation quality.

### Output

Two audio stems:

- `vocals.wav`
- `instrumental.wav`

### MVP Interfaces

- Command Line Interface (CLI)
- Python API for internal integration

### Processing Targets

- CPU
- NVIDIA CUDA GPU

The MVP is local-first. No cloud service or external API is required to perform the separation itself.

---

## Installation

> ⚠️ Package is not yet published. These are the intended installation steps once the MVP lands.

### Requirements

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) installed and available on `PATH`
- Sufficient disk space for model weights, temporary files, and generated audio (exact figure to be published once the model version is pinned)
- Optional: NVIDIA GPU with CUDA 11.8+ and compatible drivers, for GPU acceleration

### Steps

```bash
# Clone the repository
git clone https://github.com/<your-org>/sonara-vocal-remover.git
cd sonara-vocal-remover

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# (Optional) install in editable mode for development
pip install -e .
```

Verify FFmpeg is available:

```bash
ffmpeg -version
```

---

## Usage

> The commands below describe the **intended MVP interface** (the target CLI surface once implementation lands) and are **not functional yet** — see [Roadmap](#roadmap) for current status.

### Local File

```bash
python -m sonara_vocal_remover input/song.wav
```

Output:

```
output/
├── vocals.wav
└── instrumental.wav
```

With an explicit output directory:

```bash
python -m sonara_vocal_remover \
    input/song.wav \
    --output output/song/
```

### Direct URL

```bash
python -m sonara_vocal_remover \
    "https://example.com/audio/song.mp3"
```

With an explicit output directory:

```bash
python -m sonara_vocal_remover \
    "https://example.com/audio/song.mp3" \
    --output output/song/
```

The application will:

1. Validate the URL
2. Download the audio
3. Store it in a temporary workspace
4. Run the same processing pipeline used for local files
5. Export the resulting stems
6. Clean up temporary files

```
URL
 │
 ▼
Download
 │
 ▼
Temporary Audio File
 │
 ▼
Audio Processing
 │
 ├── vocals.wav
 └── instrumental.wav
```

### GPU Processing

```bash
python -m sonara_vocal_remover \
    input/song.wav \
    --device cuda
```

Works the same way with a URL input:

```bash
python -m sonara_vocal_remover \
    "https://example.com/audio/song.mp3" \
    --device cuda
```

### CPU Processing

```bash
python -m sonara_vocal_remover \
    input/song.wav \
    --device cpu
```

### CLI Options (planned)

| Flag | Description | Default |
|---|---|---|
| `--output`, `-o` | Output directory for stems | `./output` |
| `--device` | `cpu` or `cuda` | auto-detected |
| `--model` | Separation model to use | `htdemucs` |

> `--format` is intentionally omitted for now — the MVP only exports WAV. An output-format option will be added once an encoder abstraction (MP3/FLAC export) exists.

### Benchmarks

No performance numbers are published yet. Processing time depends heavily on hardware, model, chunking strategy, and track length — publishing estimates before real measurements would be misleading. A `Benchmarks` section with reproducible numbers (hardware spec, track length, wall-clock time) will be added once the MVP pipeline is implemented and measured.

---

## Python API

> The following describes the **intended Python API** for the MVP and is **not functional yet** — see [Roadmap](#roadmap) for current status.

The processing engine can also be used directly from Python.

The **canonical API** takes an explicit `InputSource`, matching the [Input Architecture](#input-architecture) exactly:

```python
from sonara_vocal_remover import VocalRemovalService, LocalFileSource, UrlSource

service = VocalRemovalService(
    model="htdemucs",
    device="cuda",
)

# Local file
result = service.process(
    source=LocalFileSource("input/song.wav"),
    output_dir="output/song",
)

# Direct URL
result = service.process(
    source=UrlSource("https://example.com/audio/song.wav"),
    output_dir="output/song",
)

print(result.vocals_path)
print(result.instrumental_path)
```

The CLI builds the appropriate `InputSource` internally (a local path becomes a `LocalFileSource`, a URL becomes a `UrlSource`) and calls this same `process(source, output_dir)` method — the CLI and the Python API share one code path, not two.

### Convenience shortcuts

For simple scripts, `input_path` / `input_url` keyword arguments are also accepted as thin wrappers that construct the corresponding `InputSource` internally:

```python
# Equivalent to source=LocalFileSource("input/song.wav")
result = service.process(input_path="input/song.wav", output_dir="output/song")

# Equivalent to source=UrlSource("https://example.com/audio/song.wav")
result = service.process(input_url="https://example.com/audio/song.wav", output_dir="output/song")
```

These shortcuts exist purely for convenience and are implemented as a thin layer on top of the `source=` API — they do not introduce a second, separate code path. Adding a future source (`YouTubeSource`, `CloudStorageSource`, `UploadedFileSource`) only requires implementing the `InputSource` interface; no changes to `VocalRemovalService.process()` or the separation engine are needed.

---

## Input Architecture

Input acquisition is separated from audio processing, so the separation engine never needs to know where the audio came from.

```
                    InputSource
                        │
          ┌─────────────┴─────────────┐
          │                           │
          ▼                           ▼
     LocalFileSource             UrlSource
          │                           │
          ▼                           ▼
     File Loader                URL Downloader
          │                           │
          └─────────────┬─────────────┘
                        ▼
              Canonical Audio
              Representation
                        │
                        ▼
                Source Separation
                        │
                        ▼
            vocals.wav / instrumental.wav
```

Each source implements the same input abstraction, so future input sources can be added without modifying the separation engine.

Potential future sources include:

- Local File
- Direct URL
- YouTube
- Cloud Storage
- Sonara API
- Uploaded File

### Scope Boundary: Vocal Remover ≠ Downloader

Adding new input sources (e.g. a future `YouTubeSource`) must **not** turn the separation engine into a general-purpose downloader. Source acquisition and audio separation are and will remain two distinct layers:

```
                    Sonara Vocal Remover
                            │
                     Input Acquisition
                            │
              ┌─────────────┴─────────────┐
              │                           │
         Local File                  Direct URL
              │                           │
              └─────────────┬─────────────┘
                            ▼
                       Audio Resource
                            │
                            ▼
                    Audio Preprocessing
                            │
                            ▼
                     Separation Engine
                            │
                         Demucs
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
              Vocals              Instrumental
```

A future `YouTubeSource` (or any other source) plugs into the **Input Acquisition** layer only — it must never be implemented inside `VocalRemovalService`, `DemucsService`, or any part of the separation engine itself:

```
YouTubeSource
     ↓
Source Acquisition Layer
     ↓
Audio Resource
     ↓
Vocal Remover
```

---

## Security Considerations for URL Input

URL processing introduces additional security considerations. The downloader must not blindly trust arbitrary URLs.

> **Status:** none of this is implemented yet. The requirements below are binding design constraints for the URL downloader, not a description of current behavior. This section will be updated to describe actual enforced behavior once the downloader ships, with tests referenced alongside each guarantee.

The URL downloader **must enforce** protection against:

- Unsupported protocols
- Localhost access
- Private network access (RFC 1918 ranges, link-local addresses)
- Internal service access (SSRF protection)
- Excessively large files
- Excessive redirects
- Download timeouts
- Malicious or corrupted files
- Disk exhaustion

### Required Limits (MVP target — not yet implemented)

| Control | Target default | Configurable |
|---|---|---|
| Allowed URL schemes | `http`, `https` only | No |
| Max download size | 200 MB | Yes, via `--max-size` |
| Connection timeout | 10 seconds | Yes |
| Total download timeout | 60 seconds | Yes |
| Max redirects | 3 | Yes |
| Private/internal network access | Blocked | No |

> These are conservative starting targets for implementation, not confirmed shipped behavior. Any deviation from them once implemented should be documented here and covered by tests before this note is removed.

---

## Output Format

- **Container:** WAV (confirmed for MVP)
- **Sample rate, bit depth, and mono/stereo handling:** **not yet finalized.** These depend on the real behavior of the Demucs pipeline and will be determined during implementation, not decided in advance in this document.

> This section will be filled in with exact, verified specifications (sample rate, bit depth, channel handling) once the separation pipeline is implemented and its actual output has been inspected — not before.

---

## Error Handling

The application is designed to provide clear errors for common input and processing failures, including:

- Invalid local file
- Invalid URL
- Unsupported URL scheme
- URL download failure
- HTTP error
- Download timeout
- File too large
- Unsupported audio format
- Corrupted audio
- Missing FFmpeg
- Missing model
- Insufficient GPU memory
- Invalid output path
- Processing failure

Low-level downloader and model exceptions will be translated into meaningful application-level errors rather than raw stack traces.

---

## Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run the full test suite
pytest

# Run with coverage
pytest --cov=sonara_vocal_remover
```

Test suite includes (planned):

- Unit tests for input sources (local file, URL)
- Unit tests for the security/downloader limits
- Integration tests for the full separation pipeline (CPU)
- CLI argument parsing tests

---

## Roadmap

### MVP

- [x] Repository architecture
- [ ] Local file input
- [ ] Direct URL input
- [ ] Secure URL downloader
- [ ] Temporary-file management
- [ ] Demucs integration
- [ ] Separation engine interface
- [ ] Vocal extraction
- [ ] Instrumental extraction
- [ ] WAV export
- [ ] CPU processing
- [ ] CUDA processing
- [ ] CLI
- [ ] Python API
- [ ] Unit tests
- [ ] Integration tests

### Post-MVP

- [ ] Model benchmarking framework
- [ ] Additional separation models
- [ ] Quality comparison tools
- [ ] Batch processing
- [ ] Progress reporting
- [ ] Better GPU memory management
- [ ] Additional audio formats
- [ ] Quality presets
- [ ] Processing queue
- [ ] REST API
- [ ] Web interface
- [ ] YouTube/source adapters
- [ ] Cloud/GPU workers

---

## Contributing

Contributions are welcome once the MVP core lands. Please open an issue to discuss significant changes before submitting a pull request.

## License

*(Specify a license — e.g. MIT, Apache-2.0 — before publishing publicly. No license currently declared.)*