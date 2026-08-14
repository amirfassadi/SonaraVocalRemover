# SonaraVocalRemover — MVP-1 Backend Hardening & Reliable Vocal Separation

## Goal

Review and fix the existing `SonaraVocalRemover` repository so it becomes a
stable MVP for vocal separation:

```text
Local Audio File / URL
      ↓
InputSource
      ↓
AudioResource
      ↓
VocalRemovalService
      ↓
DemucsEngine
      ↓
vocals.wav / instrumental.wav
```

The same pipeline must also be usable through FastAPI.

### Ground rule — read this first

**Do not change the existing architecture without a concrete reason.**

Keep the current abstractions (`InputSource`, `AudioResource`,
`SeparationEngine`, `VocalRemovalService`, `SeparationResult`) exactly as
they are. This is a **hardening pass**, not a rewrite. Fix only the
specific bugs and gaps listed in this document — nothing else.

### Scope lock — files you are allowed to touch

Only modify files inside `sonara-backend/`. Specifically, you are expected
to touch:

```text
sonara-backend/sonara_vocal_remover/sources/local_file.py
sonara-backend/sonara_vocal_remover/sources/url.py
sonara-backend/sonara_vocal_remover/separation/demucs_engine.py
sonara-backend/sonara_vocal_remover/errors.py
sonara-backend/sonara_vocal_remover/config.py
sonara-backend/api/main.py
sonara-backend/requirements.txt
sonara-backend/tests/  (new test files only, don't rewrite existing tests unless they're wrong)
sonara-backend/SERVICE.md
sonara-backend/README-SETUP.md  (only if something there is factually wrong)
README.md  (root, only the sections explicitly listed in Phase 12)
```

### Do NOT touch these, under any circumstance

```text
sonara-vocal-remover/**        (the frontend — read-only for this task, see Phase 11)
AI_STUDIO_PROMPT.md
package-lock.json (root)
Dockerfile                     (unless Phase 4's exact pin changes what's copied — it shouldn't)
sonara_vocal_remover/service.py       (already correct — do not modify unless a phase below explicitly says so)
sonara_vocal_remover/sources/base.py  (interface — do not modify)
sonara_vocal_remover/audio_resource.py (do not modify — Phase 2's fix lives in local_file.py, not here)
```

If you believe a file outside the allowed list genuinely needs a change to
satisfy a phase below, **stop and explain why before making the change** —
don't do it silently.

---

## Phase 1 — Initial review (prerequisite, no code changes yet)

1. Review the whole repository (backend and frontend, read-only).
2. Review dependencies (`requirements.txt`, `requirements-light.txt`, `package.json`).
3. Read the existing tests (`tests/test_local_file_source.py`,
   `tests/test_url_source.py`) to know what's already covered — don't
   duplicate this coverage.
4. Compare `README.md` against the actual implementation. Where they
   disagree, the code is the source of truth.
5. Output a summary categorized as `Critical` / `Important` / `Minor`
   before touching any code.

---

## Phase 2 — Fix temporary upload cleanup (Critical)

**Confirmed bug:** in `sonara_vocal_remover/sources/local_file.py`,
`LocalFileSource.acquire()` always returns
`AudioResource(..., is_temporary=False)` — this is hardcoded, not a
parameter. In `api/main.py`, an uploaded file is written to a temp
directory and then passed to the pipeline through this same
`LocalFileSource`, so `AudioResource.cleanup()` never deletes it. Uploaded
files leak on disk indefinitely.

### Required behavior

The uploaded file must be deleted after processing finishes, whether it
succeeds or fails.

### Required fix (do not redesign the abstraction)

Add an optional constructor parameter to `LocalFileSource`:

```python
def __init__(self, path: str, is_temporary: bool = False):
```

Pass it through to the `AudioResource` it returns. In `api/main.py`, when
constructing `LocalFileSource` for an uploaded file, pass
`is_temporary=True`. Do not touch `VocalRemovalService.process()` — its
existing `finally: audio.cleanup()` already handles this correctly once
`is_temporary` is set properly.

### Tests required

- Uploaded temp file no longer exists on disk after a successful
  `/api/separate` call (or after `VocalRemovalService.process()` in a unit
  test using a fake engine — see Phase 7).
- Cleanup still happens if the separation engine raises an exception.
- A `LocalFileSource` constructed the normal way (CLI path, no
  `is_temporary` argument) still defaults to `is_temporary=False` and is
  **not** deleted — don't break this existing behavior.

---

## Phase 3 — Handle relative redirects correctly (Important — not an active security hole)

**Current state:** in `sonara_vocal_remover/sources/url.py`, when a
server's `Location` header is a relative URL (e.g. `/audio/song.mp3`),
the code assigns it directly to `current_url` without
`urllib.parse.urljoin`. Because `urlparse("/audio/song.mp3").scheme` is
empty, `_validate_url` correctly rejects it with
`UnsupportedUrlSchemeError` — **this is fail-safe, not an SSRF bypass.**
The real problem is that legitimate relative redirects (which real audio
CDNs commonly use) incorrectly fail.

### Required behavior

Use `urllib.parse.urljoin(current_url, location)` to resolve the redirect
target relative to the current URL, then run the resolved URL through the
exact same `_validate_url` checks as before (scheme, hostname, private-IP,
platform-host — no exceptions skipped).

### Tests required

- Absolute redirect still works (existing behavior, don't break it).
- Relative redirect now resolves and succeeds when the target is public.
- Relative redirect that resolves to localhost/private IP is still
  blocked.
- **Cross-host redirect**: `https://example.com/file` redirects to a
  *different* public host (e.g. `https://cdn.example.org/file`) — must
  re-run full validation against the new host and succeed if it's public.
- **Cross-host redirect to a private target**: a public URL redirects to
  `http://127.0.0.1/...` (or any private/internal address) — must be
  blocked by `BlockedUrlError`, even though the first hop was fully
  public and passed validation.
- Multi-hop redirect chain.
- Redirect limit exceeded still raises `TooManyRedirectsError`.

---

## Phase 4 — Pin the Demucs version (Important)

**Confirmed:** `requirements.txt` currently has `demucs>=4.0.1` (open-ended).

### Required work

1. First check whether Demucs is already installed in the current
   environment (`pip show demucs`) or whether there's any existing
   lock/installation metadata that indicates a version already
   tested against this codebase. **Do not arbitrarily pick a version**
   (e.g. don't just grab the latest release from PyPI because it's the
   first one you see) — the goal is to pin whatever version this
   project has actually been built and tested against. If no such
   evidence exists in the environment you're working in, install the
   latest `4.x` release, run the full test suite plus a manual
   separation on a short fixture to confirm it actually works, and pin
   that exact version — state clearly in your report that this version
   was newly chosen rather than recovered from an existing environment.
2. Change `requirements.txt` to `demucs==X.Y.Z` (exact version).
3. Verify `pip install -r requirements.txt` succeeds cleanly in a fresh
   venv.
4. Other unpinned dependencies (`requests`, `fastapi`, `uvicorn`,
   `python-multipart`, `pytest`) are **out of scope** for this phase —
   just note them as a finding in the final report, don't pin them unless
   explicitly asked.

---

## Phase 5 — Real timeout for the Demucs subprocess (Critical)

**Confirmed bug:** in `sonara_vocal_remover/separation/demucs_engine.py`,
`subprocess.run(cmd, capture_output=True, text=True, timeout=None)` — if
Demucs hangs, this never terminates. There is also currently no
timeout-specific exception for processing (only `DownloadTimeoutError`,
which is about the URL download, not processing).

### Required behavior

1. Add a new exception in `errors.py`: `class ProcessingTimeoutError(SonaraError)`.
2. Add a configurable timeout for Demucs (e.g. in `config.py`, a
   reasonable default constant for the MVP; pass it through to
   `DemucsSeparationEngine.__init__`).
3. Ensure the Demucs child process is **reliably terminated** when the
   timeout occurs — including any grandchild processes Demucs/torch may
   spawn (e.g. data-loading worker processes), not just the immediate
   subprocess. `subprocess.run(..., timeout=<value>)` alone only kills the
   direct child on timeout, which may leave orphaned worker processes
   behind. If `subprocess.run()` doesn't give you enough control for this
   (e.g. you need `os.killpg` on a process group, or `Popen` +
   `terminate()`/`kill()` with a grace period), switch the *internal*
   implementation to `subprocess.Popen()` — but do not change the public
   `SeparationEngine.separate()` interface or its return type. Catch the
   timeout condition and raise `ProcessingTimeoutError`.
4. Confirm (don't need to change) that `VocalRemovalService.process()`'s
   existing `finally: audio.cleanup()` still cleans up temp files when
   this new exception is raised.
5. Keep this concept separate from `DownloadTimeoutError` — do not merge
   or rename either.
6. In `api/main.py`, add `ProcessingTimeoutError` to `_ERROR_STATUS`
   (suggested: `504`, consistent with the existing `DownloadTimeoutError`
   mapping). Do not change any existing mappings in that dict.

### Tests required

Using a `FakeSeparationEngine` (see Phase 7) that simulates a hang or
raises a `subprocess.TimeoutExpired`-equivalent condition, confirm
`ProcessingTimeoutError` is raised correctly and cleanup still runs.

---

## Phase 6 — Complete error → HTTP status mapping (Minor–Important)

Verify these errors map to the correct HTTP status in `api/main.py`'s
`_ERROR_STATUS` dict. Only **add** the new `ProcessingTimeoutError` entry
— do not change any of the existing mappings below:

```text
InvalidLocalFileError        → 400  (existing, keep as-is)
InvalidUrlError               → 400  (existing, keep as-is)
UnsupportedUrlSchemeError      → 400  (existing, keep as-is)
BlockedUrlError                 → 400  (existing, keep as-is)
UnsupportedAudioFormatError      → 400  (existing, keep as-is)
InvalidOutputPathError            → 400  (existing, keep as-is)
DownloadTimeoutError                → 504  (existing, keep as-is)
ProcessingTimeoutError (NEW)         → 504  (add this)
FileTooLargeError                     → 413  (existing, keep as-is)
TooManyRedirectsError                  → 502  (existing, keep as-is)
MissingFFmpegError                      → 503  (existing, keep as-is)
MissingModelError                        → 503  (existing, keep as-is)
InsufficientGPUMemoryError                → 503  (existing, keep as-is)
ProcessingFailureError                     → 500  (existing, keep as-is)
```

---

## Phase 7 — Unit tests for `VocalRemovalService` with a fake engine (Critical)

There are currently **no** tests for `VocalRemovalService`. Create a
`FakeSeparationEngine(SeparationEngine)` (put it in
`tests/` or a small `tests/fakes.py` helper — your choice, but don't put
test-only code in the production package) that does not run real Demucs
and just produces fake output paths / simulates failures. Inject it via
the existing constructor parameter:
`VocalRemovalService(engine=FakeSeparationEngine())` — this dependency
injection point already exists in `service.py`, do not modify
`service.py` itself.

### Tests required

1. `LocalFileSource` → `VocalRemovalService` → `FakeEngine` →
   `SeparationResult` is returned correctly.
2. If `FakeEngine.separate()` raises an exception, `cleanup()` is still
   called.
3. If `FakeEngine` simulates a timeout (raises `ProcessingTimeoutError`
   from Phase 5), cleanup is still guaranteed.

---

## Phase 8 — Integration test for the real DemucsEngine (Important, kept separate from unit tests)

Add an integration test that runs real Demucs on a short audio fixture
and verifies `vocals.wav` / `instrumental.wav` exist, are readable, and
are at the correct path. Mark it separately from the fast unit tests
(e.g. `@pytest.mark.integration`) since it's heavy and won't run in every
CI environment. Document how to run it separately (e.g.
`pytest -m integration`) in `SERVICE.md`.

**Fixture requirements:** the audio fixture must be committed to the
repo at `tests/fixtures/short_test_audio.wav` (or similar), and it must
be **short and small** — a few seconds of audio, not a full track. Do not
commit a large audio file to the repository. If you need to generate one
programmatically (e.g. a short sine-wave tone) instead of sourcing a real
short clip, that's fine — the point is keeping the repo lightweight.

---

## Phase 9 — FastAPI tests (Important)

There are currently no tests for `api/main.py`. Using FastAPI's
`TestClient`, cover at minimum:

- `GET /api/health` → 200
- `POST /api/validate-url` with an invalid/blocked URL → correct status and message
- `POST /api/separate` with neither `file` nor `url` → 400
- `POST /api/separate` with both `file` and `url` → 400
- `POST /api/separate` success path (inject `FakeSeparationEngine` instead
  of real Demucs so the test stays fast — you may need a small,
  test-only way to override the engine used by the endpoint; keep this
  override minimal and don't restructure `api/main.py` beyond what's
  needed for testability)
- Confirm that after a successful `/api/separate` call, the temp uploaded
  file from Phase 2 is gone

---

## Phase 10 — Quick CLI check (Minor)

Just confirm `cli.py` still goes through `VocalRemovalService.process()`
(separation logic must not be duplicated in the CLI) and that
`--model` / `--device` / `--output` actually match the current
implementation. No architecture changes unless you find a genuine
mismatch — if you do, stop and describe it before changing anything.

---

## Phase 11 — Frontend check only, no rewrite (Minor)

Do not modify any file under `sonara-vocal-remover/`. Just verify (read-only):

- `src/lib/audioEngine.ts` is only used for client-side playback/audio
  handling, not as a separation engine.
- The actual flow is: `React → POST /api/separate → receive result → play
  vocals/instrumental`.
- If the frontend is incompatible with the API after this task's changes,
  report it — do not fix it as part of this task.

---

## Phase 12 — Update documentation (Important)

After the code changes above are done, update `README.md` and
`sonara-backend/SERVICE.md` to match the real implementation: installation,
running the backend/frontend, CLI usage, API usage, supported formats, the
now-pinned Demucs version, CPU/CUDA behavior, output files, and known
limitations (e.g. output job files under `/tmp/sonara_jobs` are **not**
auto-cleaned yet — this is intentionally out of scope for this milestone,
just document it as a known limitation). Do not claim any feature exists
that isn't actually implemented.

---

## Phase 13 — Repository hygiene (Minor)

Check `.gitignore`, `requirements.txt`, `Dockerfile`, and pytest config
(add an `integration` marker registration in `pytest.ini` or
`pyproject.toml` if one doesn't exist yet, so `pytest -m integration`
works cleanly without a warning). Confirm no secrets/API keys are
committed and no temp output or venv directories are tracked by git.

---

## MVP-1 acceptance criteria

- [ ] Local file via CLI → vocals.wav / instrumental.wav (already works — just confirm, don't change)
- [ ] Valid URL (including relative redirects) → secure download → same output
- [ ] Upload via `/api/separate` → processed → uploaded temp file is deleted afterward
- [ ] On success, failure, and timeout, temp files are cleaned up
- [ ] SSRF protection and redirect validation (including relative) are active and tested
- [ ] `demucs` is pinned to an exact version
- [ ] `ProcessingTimeoutError` is implemented and tested
- [ ] Unit tests for `VocalRemovalService` using a fake engine
- [ ] Integration test (separate from unit tests) for real Demucs
- [ ] FastAPI tests for health / validate-url / separate
- [ ] `README.md` / `SERVICE.md` match the actual code

---

## Explicitly out of scope for this milestone (do not add any of these)

```text
❌ YouTube downloader or any new InputSource
❌ Cloud storage
❌ Batch processing
❌ Job queue / Celery / Redis
❌ RoFormer / MDX / any additional separation model or model selection UI
❌ Authentication / user accounts / database
❌ New frontend framework or frontend rewrite
❌ Auto-cleanup / retention policy for OUTPUT job files under /tmp/sonara_jobs
   (this is different from Phase 2, which is only about the temp *upload*
   file — leave output retention for the next milestone)
❌ Any dependency pin/upgrade beyond Demucs (Phase 4) unless you flag it
   as a finding first
```

---

## How to work

**Do not run all phases in one shot.** Work in these checkpoints and stop
for confirmation after each one before continuing to the next:

```text
Checkpoint A: Phase 1 only        → report findings, then stop
Checkpoint B: Phases 2–5          → implement, run tests, then stop
Checkpoint C: Phases 6–9          → implement, run tests, then stop
Checkpoint D: Phases 10–13        → implement, then stop
```

Within each checkpoint:

1. Before any code change, output the Phase 1 summary (checkpoint A only).
2. List exactly which files you're about to change and why, mapped to the
   phase that justifies it.
3. Apply changes phase by phase within the checkpoint. Run the relevant
   tests after each phase before moving to the next phase.
4. If a test fails, find the root cause and fix it before continuing —
   don't move to the next phase with a known failing test.
5. At the end of each checkpoint, review the `git diff` for that
   checkpoint yourself — if anything in it isn't explained by a phase in
   this document, revert it.
6. Summarize what changed in this checkpoint and wait before proceeding
   to the next one. This keeps changes reviewable in small batches
   instead of one large, hard-to-audit diff — if something goes wrong in
   Phase 5 (subprocess/timeout handling), it should be caught before
   another 20 files change on top of it.

### Core principle

**Do not rewrite the architecture. Improve the existing architecture.**
If you find yourself wanting to touch a file in the "Do NOT touch" list
above to make something easier, that's a signal to stop and ask, not a
signal to proceed.

### Final report format

```text
1. Files changed (list, each mapped to the phase that required it)
2. Problems fixed (labeled Critical/Important/Minor)
3. Tests added
4. Tests passed (paste the pytest summary)
5. Remaining known issues (e.g. output job retention, unpinned secondary deps)
6. Recommended next milestone
```
