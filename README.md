# Sonara Vocal Remover

AI-powered vocal removal and music source separation engine for the Sonara platform.

Sonara Vocal Remover is a local-first audio separation backend designed to remove vocals from music tracks and produce separate **vocals** and **instrumental** stems.

The current backend implementation is built around **Demucs** and exposes the same processing pipeline through:

* Command Line Interface (CLI)
* Python API
* HTTP API (FastAPI)

---

## Features

### Audio separation

Given a supported audio file, Sonara Vocal Remover produces:

```text
vocals.wav
instrumental.wav
```

The current separation engine uses:

```text
Demucs 4.0.2
Model: htdemucs
```

The model and processing device can be overridden through the CLI or Python API.

### Supported input formats

The current validation layer supports:

* `.wav`
* `.mp3`
* `.flac`
* `.m4a`
* `.ogg`

### Input sources

The backend currently supports two input-source types:

1. Local audio files
2. Direct HTTP/HTTPS audio URLs

Platform pages such as YouTube, Spotify, and SoundCloud are **not** treated as direct audio sources.

For example, this is not a supported audio URL:

```text
https://www.youtube.com/watch?v=...
```

A URL must point to a directly downloadable audio resource.

---

# Project Structure

The repository contains the application frontend and the Python processing backend.

```text
SonaraVocalRemover/
│
├── sonara-vocal-remover/
│   └── Frontend / application layer
│
└── sonara-backend/
    │
    ├── api/
    │   └── main.py
    │
    ├── sonara_vocal_remover/
    │   ├── sources/
    │   │   ├── LocalFileSource
    │   │   └── UrlSource
    │   │
    │   ├── separation/
    │   │   └── Demucs separation engine
    │   │
    │   ├── cli.py
    │   ├── service.py
    │   ├── config.py
    │   ├── errors.py
    │   └── ...
    │
    ├── tests/
    ├── requirements.txt
    └── SERVICE.md
```

The important architectural principle is that **input acquisition is separated from source separation**.

```text
                  InputSource
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
   LocalFileSource            UrlSource
          │                       │
          └───────────┬───────────┘
                      ▼
                Audio Resource
                      │
                      ▼
               VocalRemovalService
                      │
                      ▼
              DemucsSeparationEngine
                      │
              ┌───────┴───────┐
              ▼               ▼
          vocals.wav     instrumental.wav
```

This separation makes it possible to add future input sources without modifying the separation engine.

---

# Requirements

## Software

The backend requires:

* Python 3.10+
* FFmpeg
* pip
* Virtual environment recommended

The current Python backend dependencies include:

```text
demucs==4.0.2
fastapi
uvicorn
python-multipart
requests
pytest
```

Demucs pulls in PyTorch and other machine-learning dependencies, so installation can require a significant amount of disk space and download time.

---

# Installation — Windows

Open PowerShell and enter the backend directory.

```powershell
cd "D:\Dropbox\MirancoProjects\SonaraVocalRemover\sonara-backend"
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
pip install -r requirements.txt
```

Verify FFmpeg:

```powershell
ffmpeg -version
```

If FFmpeg is correctly installed, the command should print its version information.

---

# Installation — Linux / macOS

Create the virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Verify FFmpeg:

```bash
ffmpeg -version
```

---

# Quick Start

The simplest way to remove vocals from a local audio file is:

```bash
python -m sonara_vocal_remover input/song.mp3
```

The default output directory is:

```text
./output
```

The resulting files are:

```text
output/
├── vocals.wav
└── instrumental.wav
```

---

# Windows — Complete MP3 Example

For example, if your input file is:

```text
C:\Users\Amir\Music\16. Daryache Noor.mp3
```

run:

```powershell
python -m sonara_vocal_remover `
    "C:\Users\Amir\Music\16. Daryache Noor.mp3" `
    --output "D:\Dropbox\MirancoProjects\SonaraVocalRemover\model-tests\Daryache-Noor" `
    --device cpu
```

After processing, the output directory should contain:

```text
D:\Dropbox\MirancoProjects\SonaraVocalRemover\model-tests\Daryache-Noor\
├── vocals.wav
└── instrumental.wav
```

The CLI prints the final paths when processing completes successfully.

---

# CLI

The CLI is implemented as a Python module:

```bash
python -m sonara_vocal_remover
```

Show help:

```bash
python -m sonara_vocal_remover --help
```

Basic usage:

```bash
python -m sonara_vocal_remover INPUT
```

With output directory:

```bash
python -m sonara_vocal_remover INPUT --output OUTPUT
```

With a specific device:

```bash
python -m sonara_vocal_remover INPUT --device cpu
```

With a specific model:

```bash
python -m sonara_vocal_remover INPUT --model htdemucs
```

## CLI options

| Option           | Description                                     | Default    |
| ---------------- | ----------------------------------------------- | ---------- |
| `input`          | Local audio path or direct HTTP/HTTPS audio URL | Required   |
| `--output`, `-o` | Output directory                                | `./output` |
| `--device`       | Processing device: `cpu` or `cuda`              | `cpu`      |
| `--model`        | Demucs model variant                            | `htdemucs` |

---

# CPU Processing

CPU processing is supported and is the default:

```bash
python -m sonara_vocal_remover input/song.mp3 --device cpu
```

CPU processing is expected to be considerably slower than a compatible GPU configuration.

Processing time depends on:

* CPU performance
* audio duration
* model
* available RAM
* Demucs processing behavior

No fixed processing-time estimate is currently claimed by the project.

---

# NVIDIA CUDA

If a compatible NVIDIA CUDA/PyTorch environment is installed, the backend can be instructed to use CUDA:

```bash
python -m sonara_vocal_remover input/song.mp3 --device cuda
```

The project currently exposes `cpu` and `cuda` as the supported CLI device values.

GPU compatibility depends on the installed PyTorch build and the NVIDIA driver/CUDA environment.

---

# AMD GPUs

AMD GPU acceleration is **not currently exposed through the project's CLI**.

The current CLI accepts:

```text
cpu
cuda
```

and does not provide a DirectML or ROCm device option.

Therefore, on systems without a compatible NVIDIA CUDA environment, use:

```bash
python -m sonara_vocal_remover input/song.mp3 --device cpu
```

AMD GPU acceleration should not be considered a current project feature until it is implemented and tested.

---

# Direct URL Input

The backend can process direct audio URLs:

```bash
python -m sonara_vocal_remover \
    "https://example.com/audio/song.mp3" \
    --output output/song
```

The URL source is processed through the same separation pipeline as a local file.

```text
URL
 │
 ▼
URL validation
 │
 ▼
Download
 │
 ▼
Temporary audio file
 │
 ▼
Demucs
 │
 ├── vocals.wav
 └── instrumental.wav
```

---

# URL Security

Remote input is subject to validation and security restrictions.

The current implementation enforces limits including:

* HTTP/HTTPS schemes only
* Maximum download size: 200 MB
* Connection timeout: 10 seconds
* Total download timeout: 60 seconds
* Maximum redirects: 3
* Protection against localhost/private/internal network access
* Supported audio-extension validation
* Platform URL blocking

The following platforms are explicitly outside the current direct-URL input scope:

```text
YouTube
Spotify
SoundCloud
```

For example:

```text
https://youtube.com/watch?v=...
```

is a web page URL, not a direct audio resource, and is therefore rejected by the URL input layer.

A future downloader/source adapter can support such platforms without coupling them to the Demucs separation engine.

---

# Python API

The same processing pipeline can be used directly from Python.

```python
from sonara_vocal_remover import (
    VocalRemovalService,
    LocalFileSource,
)

service = VocalRemovalService(
    model="htdemucs",
    device="cpu",
)

result = service.process(
    source=LocalFileSource("input/song.mp3"),
    output_dir="output/song",
)

print(result.vocals_path)
print(result.instrumental_path)
```

The service can also accept the convenience `input_path` argument:

```python
from sonara_vocal_remover import VocalRemovalService

service = VocalRemovalService(
    model="htdemucs",
    device="cpu",
)

result = service.process(
    input_path="input/song.mp3",
    output_dir="output/song",
)
```

For a direct audio URL:

```python
result = service.process(
    input_url="https://example.com/audio/song.mp3",
    output_dir="output/song",
)
```

The CLI and Python API use the same service and separation-engine code path.

---

# HTTP API

The backend also includes a FastAPI wrapper.

Start the API from the `sonara-backend` directory:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

The API exposes:

| Method | Endpoint                           | Purpose                                 |
| ------ | ---------------------------------- | --------------------------------------- |
| `GET`  | `/api/health`                      | Backend status and supported formats    |
| `POST` | `/api/validate-url`                | Validate a URL without downloading it   |
| `POST` | `/api/separate`                    | Separate an uploaded file or direct URL |
| `GET`  | `/files/{job_id}/vocals.wav`       | Download generated vocals               |
| `GET`  | `/files/{job_id}/instrumental.wav` | Download generated instrumental         |

A separation request can use either:

* uploaded audio file
* direct audio URL

Example response:

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

---

# Output

The current separation output consists of two WAV files:

```text
vocals.wav
instrumental.wav
```

The instrumental stem is intended for:

* karaoke
* backing tracks
* practice
* remixing
* music analysis

The vocals stem can be used for:

* vocal analysis
* remixing
* vocal practice
* further audio processing

The project currently exports WAV files only.

Exact output sample-rate, bit-depth, and channel behavior should be considered implementation-dependent until they are formally measured and documented.

---

# Models

The current default model is:

```text
htdemucs
```

The CLI allows the model to be overridden:

```bash
python -m sonara_vocal_remover input/song.mp3 --model htdemucs
```

The project architecture intentionally keeps the separation engine behind an abstraction so that additional models can be added later.

Potential future model support includes alternative Demucs variants and other source-separation architectures.

Model quality and performance should be evaluated through reproducible benchmarks before making quality claims.

---

# Testing

Run the backend tests from:

```text
sonara-backend/
```

with:

```bash
pytest tests/ -v
```

The current test suite focuses primarily on:

* local-file validation
* URL validation
* URL scheme restrictions
* platform URL blocking
* SSRF protection
* download limits
* timeout/redirect behavior
* application-level error handling

Real Demucs separation tests are intentionally not part of the normal test suite because they require model weights and are hardware-dependent.

---

# Error Handling

The backend translates low-level failures into application-level errors.

Possible error categories include:

* invalid local file
* unsupported audio format
* invalid URL
* unsupported URL scheme
* blocked URL
* private/internal network access
* HTTP failure
* download timeout
* download-size limit exceeded
* missing FFmpeg
* missing model
* invalid output path
* processing failure
* insufficient GPU resources

The CLI reports application errors in a concise form:

```text
Error: <message>
```

---

# Development Architecture

The core processing flow is:

```text
                 Input
                   │
          ┌────────┴────────┐
          │                 │
          ▼                 ▼
     Local File        Direct URL
          │                 │
          ▼                 ▼
 LocalFileSource       UrlSource
          │                 │
          └────────┬────────┘
                   ▼
             InputSource
                   │
                   ▼
        VocalRemovalService
                   │
                   ▼
       SeparationEngine
                   │
                   ▼
      DemucsSeparationEngine
                   │
             ┌─────┴─────┐
             ▼           ▼
          Vocals      Instrumental
             │           │
             └─────┬─────┘
                   ▼
             SeparationResult
```

The important design rule is:

> Input acquisition and source separation remain separate concerns.

For example, a future `YouTubeSource` should be implemented in the input-acquisition layer rather than adding YouTube-specific logic to `VocalRemovalService` or the Demucs engine.

---

# Current Status

## Implemented

* [x] Repository architecture
* [x] `InputSource` abstraction
* [x] Local file input
* [x] Direct URL input
* [x] URL validation
* [x] SSRF protection
* [x] URL scheme validation
* [x] Platform URL blocking
* [x] Download size limit
* [x] Download timeout
* [x] Redirect limit
* [x] Temporary-file handling
* [x] Demucs integration
* [x] Separation engine abstraction
* [x] Vocal extraction
* [x] Instrumental extraction
* [x] WAV output
* [x] CPU processing
* [x] CLI
* [x] Python API
* [x] FastAPI wrapper
* [x] Application-level error mapping
* [x] Input/security tests

## Experimental / Not Yet Fully Validated

* [ ] Exact Demucs checkpoint/version pin beyond the package version
* [ ] Comprehensive quality benchmarking
* [ ] CPU performance benchmarks
* [ ] GPU performance benchmarks
* [ ] Formal output sample-rate specification
* [ ] Formal output bit-depth specification
* [ ] Formal channel/stereo behavior specification
* [ ] Real-Demucs integration tests in CI

## Planned

* [ ] Model benchmarking framework
* [ ] Quality comparison between models
* [ ] Additional separation models
* [ ] Batch processing
* [ ] Progress reporting
* [ ] Improved GPU memory management
* [ ] Quality presets
* [ ] Processing queue
* [ ] Additional output formats
* [ ] REST API improvements
* [ ] Web interface integration
* [ ] Additional source adapters
* [ ] YouTube/source acquisition adapters
* [ ] Cloud/GPU workers

---

# Performance

No official benchmark numbers are currently published.

Separation performance depends heavily on:

* CPU/GPU hardware
* audio duration
* model
* available memory
* PyTorch configuration
* operating system
* disk speed

Benchmarks should be reported using reproducible conditions, including:

```text
Hardware
Model
Device
Audio duration
Processing time
Peak memory usage
```

This project intentionally avoids publishing unsupported performance estimates.

---

# Limitations

The current version has several important limitations:

1. The CLI currently supports `cpu` and `cuda`.
2. AMD GPU acceleration is not currently implemented as a project feature.
3. Output is currently WAV.
4. YouTube/Spotify/SoundCloud page URLs are not accepted as direct audio input.
5. Demucs processing can be computationally expensive.
6. Real separation performance depends strongly on hardware.
7. Exact output audio specifications have not yet been formally benchmarked.
8. Model-quality comparisons have not yet been established through a reproducible benchmark suite.

---

# Troubleshooting

## `python -m sonara_vocal_remover` is not found

Make sure you are inside the backend directory:

```text
sonara-backend/
```

For example:

```powershell
cd "D:\Dropbox\MirancoProjects\SonaraVocalRemover\sonara-backend"
```

Then activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Try:

```powershell
python -m sonara_vocal_remover --help
```

---

## `ffmpeg` is not recognized

Check:

```powershell
ffmpeg -version
```

If PowerShell cannot find it, install FFmpeg and add its `bin` directory to the system `PATH`.

---

## CUDA errors

If:

```bash
--device cuda
```

fails, verify that:

* the system has a compatible NVIDIA GPU
* the NVIDIA driver is installed
* the installed PyTorch build supports CUDA
* sufficient GPU memory is available

As a fallback, use:

```bash
--device cpu
```

---

## Processing is very slow

CPU inference can be significantly slower than GPU inference.

For long tracks, processing time can increase substantially.

This is expected behavior for a computationally intensive source-separation model.

---

# Contributing

Contributions are welcome.

Before making significant architectural changes, please open an issue to discuss the proposed change.

Areas that are particularly useful for contribution include:

* model benchmarking
* GPU support
* quality evaluation
* performance optimization
* batch processing
* test coverage
* API improvements
* additional input sources
* documentation

---

# License

No project license has currently been declared.

A license should be added before the project is distributed as an open-source package.
