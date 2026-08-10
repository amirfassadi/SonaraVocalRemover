# Google AI Studio Prompt — Sonara Vocal Remover Web App

Copy everything below the line into Google AI Studio as your build prompt.

---

Build a web application called **Sonara Vocal Remover**: a tool that lets a user upload a local audio file or paste a direct audio URL, and get back two downloadable stems — `vocals.wav` and `instrumental.wav`.

## Critical architecture constraint — read first

**Do NOT implement audio separation in the browser or in the Node/Express server.** There is no real vocal-separation logic you can run in JavaScript/TypeScript for this app. All real separation happens in an existing, separate **Python backend service** (FastAPI) that I already built and will run alongside this app. Your job is the frontend + a thin Express layer that talks to that backend over HTTP. Do not fabricate, simulate, or approximate separation with any in-browser audio trick (e.g. no mid/side channel subtraction, no synthesized "demo" separation). If the backend is unreachable, show a real error state — never fall back to fake output.

## Backend API contract (already implemented, do not reimplement)

Base URL is configurable via an environment variable `SEPARATION_API_URL` (default `http://localhost:8000`).

- `GET {SEPARATION_API_URL}/api/health`
  → `{ status, version, engine, supported_formats: string[] }`

- `POST {SEPARATION_API_URL}/api/validate-url`
  Body: `{ "url": string }`
  → `{ valid: boolean, message?: string, hasValidExt?: boolean, hostname?: string, protocol?: string }`
  Use this to validate a pasted URL **before** submitting it for separation, so the user gets fast feedback (e.g. "this looks like a YouTube page, not a direct audio file" or "this points to a private network address and is blocked").

- `POST {SEPARATION_API_URL}/api/separate`
  `multipart/form-data` with **either** a `file` field (the uploaded audio) **or** a `url` field (a validated direct audio URL) — never both. Optional fields: `model` (default `htdemucs`), `device` (default `cpu`).
  → `{ job_id, vocals_url, instrumental_url, model, device, source_origin }`
  `vocals_url` / `instrumental_url` are relative paths (e.g. `/files/{job_id}/vocals.wav`) served by the same backend — resolve them against `SEPARATION_API_URL` to get playable/downloadable URLs.
  On failure, returns a non-2xx status with `{ error: { type: string, message: string } }`. Map `type` to a user-friendly message (see Error Handling below); always show `message` as a fallback.

Do not add any other backend endpoints related to separation. Do not add a Gemini/LLM "audio analysis" feature unless I explicitly ask for it later — keep the app scoped to separation only for this MVP.

## Supported input

- **Local file upload**: `.wav`, `.mp3`, `.flac`, `.m4a`, `.ogg` — validate the extension client-side before upload as a UX nicety, but treat the backend's response as authoritative (client-side checks are not security).
- **Direct URL**: must resolve via `/api/validate-url` before the user can submit it. If the URL looks like a YouTube/Spotify/SoundCloud page, show a clear inline message explaining these platform URLs aren't supported in the MVP — direct audio file links only (e.g. ending in `.mp3`, `.wav`, `.flac`).

## Required UI flow

1. **Input step** — tabs or toggle between "Upload file" and "Paste URL".
   - File upload: drag-and-drop + click-to-browse, show filename/size, reject unsupported extensions before upload with a clear inline error.
   - URL input: text field with a "Validate" step (calls `/api/validate-url`) before "Separate" becomes clickable. Show validation state inline (checking / valid / blocked / invalid) — don't just silently accept.
2. **Processing step** — after submitting to `/api/separate`, show a clear "processing" state (this call is slow — real separation can take anywhere from seconds to a few minutes depending on hardware and track length; do not imply a fixed duration or fake progress percentage). A simple indeterminate spinner/animation with an honest label like "Separating vocals — this can take a while" is correct. Do not fabricate a progress bar with fake percentages advancing over time.
3. **Result step** — once `/api/separate` resolves, show:
   - An audio player for `vocals.wav` and one for `instrumental.wav` (use the native `<audio>` element or a simple custom player — either is fine).
   - Download buttons for both stems, linking directly to the resolved `vocals_url`/`instrumental_url`.
   - The `model`/`device` actually used, from the response (don't assume — display what the backend reports).
4. **Error step** — if `/api/separate` or `/api/validate-url` fails, or the backend is unreachable (network error / non-JSON response), show a clear, specific error message and a way to try again. Never silently show empty/placeholder stems.

## Error handling (map backend error `type` → user-facing message)

| Backend `error.type` | Suggested user-facing message |
|---|---|
| `InvalidLocalFileError` | "That file couldn't be read. Try a different file." |
| `UnsupportedAudioFormatError` | "That file format isn't supported yet. Supported: WAV, MP3, FLAC, M4A, OGG." |
| `InvalidUrlError` | "That doesn't look like a valid URL." |
| `UnsupportedUrlSchemeError` | "Only http:// and https:// URLs are supported." |
| `BlockedUrlError` | "That URL can't be used (blocked for security reasons, or it's a platform page rather than a direct audio file)." |
| `UrlDownloadError` / `TooManyRedirectsError` | "Couldn't download audio from that URL. Double-check the link." |
| `DownloadTimeoutError` | "The download took too long and timed out. Try a smaller file or a faster host." |
| `FileTooLargeError` | "That file is too large (limit: 200MB)." |
| `MissingFFmpegError` / `MissingModelError` / `InsufficientGPUMemoryError` / `ProcessingFailureError` | "Something went wrong on our end while processing. Please try again in a moment." |
| Network error reaching the backend at all | "Can't reach the separation service right now. Please try again shortly." |

Always fall back to displaying `error.message` alongside the friendly text above, not instead of it.

## Non-functional requirements

- **`SEPARATION_API_URL` must be an environment variable**, not hardcoded, so it can point at `localhost:8000` in dev and a real deployed backend in production.
- **No fake/simulated separation anywhere in the codebase.** If you're tempted to add a "demo mode" with synthesized audio or a client-side DSP shortcut so the UI has something to show without the backend running, don't — instead, show the disconnected/error state described above when the backend isn't reachable.
- Package name should be `sonara-vocal-remover`, not a generic template name.
- Keep the UI clean and modern (dark theme is fine) but the priority is that every state (idle, validating, uploading, processing, success, error) is real and wired to the actual API — not visual polish over fake functionality.
- Write basic loading/disabled states on all buttons during in-flight requests to prevent double-submission.

## Out of scope for this build (do not implement)

- YouTube/Spotify/SoundCloud downloading or any platform adapter.
- Any AI-generated commentary/analysis of the separated audio.
- User accounts, history, or persistence beyond the current session.
- Batch processing of multiple files at once.

---

*(End of prompt.)*
