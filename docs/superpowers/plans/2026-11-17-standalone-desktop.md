# Standalone Desktop App + Easy Setup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The Windows desktop app runs the whole Media Factory engine locally (embedded PostgreSQL + API + worker), and a first-run Easy Setup connects the user's own AI server or a paid AI service.

**Architecture:** A new `desktop_engine.py` owns the engine: data folder, secret key, `pgserver` PostgreSQL, `mf migrate`, and two child processes (`--engine api`, `--engine worker`) of the same frozen exe. `desktop.py` gains a `mode` (`local` | `remote`): in local mode the existing local proxy forwards `/api` to the engine. AI setup lives server-side (`ai/presets.py`, `ai/discovery.py`, `api/routes/ai_setup.py`) with a panel wizard (`web/setup.js`).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy/Alembic, PostgreSQL via `pgserver`, pywebview, PyInstaller, Inno Setup, vanilla JS panel.

**Spec:** `docs/superpowers/specs/2026-11-17-ai-setup-wizard-design.md`

## Global Constraints

- No Claude/Anthropic attribution in commits, PRs or files.
- Backend tests run on CT 175 via `bash "../remote_test.sh" [paths]` (exits non-zero on failure). Never start Docker locally. Windows-only checks (engine spike, packaged smoke) run in the local `.venv`.
- No Tailscale or `mediafactory` host assumption anywhere in user-facing defaults or text (Tailscale may appear only as one example of a remote address).
- API keys are stored only encrypted (`AIProvider.api_key_enc`), never logged or returned.
- Existing installs with `server_url` in `config.json` must stay in `remote` mode and behave exactly as today.
- Engine data folder (Windows): `%LOCALAPPDATA%\CiciByteMediaFactory\data`. Engine binds only `127.0.0.1`.
- Arbitrary-address AI checks (`check`, `try` with a custom base_url) are allowed only when the API runs in local mode (`MF_LOCAL_MODE=1`).
- Release v0.5.0: Windows gets local mode; macOS/Linux builds stay remote-only and show local mode as "coming soon".
- Every release also updates the showroom download site (release checklist).

## Review Focus

1. Engine shutdown on every path (window close, updater restart, crash on next start): no orphan postgres/api/worker processes, no corrupted pg data dir.
2. Second app launch while the first is running: must focus the first window, never start a second engine on the same data dir.
3. A cloud service accepting the request but ignoring `response_format` (Anthropic compat): script/classify output must still parse via prompt-mode JSON.
4. Remote-mode server reachable on a LAN: `/api/ai-setup/check` and `/try` must refuse arbitrary URLs.
5. First run without internet: setup must let the user skip model downloads and still finish the AI step.

---

### Task 1: Spike — pgserver on Windows

**Files:**
- Create: `scripts/spike_pgserver.py` (kept as a manual diagnostic)

- [ ] Step 1: In the local `.venv`, `pip install pgserver`. Write `scripts/spike_pgserver.py` that starts pgserver in a temp dir, prints the connection URI, runs `SELECT version()` with psycopg, runs `mf migrate` against it (env `MF_DATABASE_URL`, `MF_SECRET_KEY`), then stops it.
- [ ] Step 2: Run it. Expected: version printed, migrations reach head, process exits, no `postgres.exe` left (`Get-Process postgres` empty).
- [ ] Step 3: Freeze-check: confirm pgserver's binaries are package data (locate `pginstall` folder) so PyInstaller can `--collect-all pgserver`.
- [ ] Step 4: Ledger a Ruling: pgserver works / fallback to bundling official PostgreSQL Windows zip binaries (`initdb`, `pg_ctl`) behind the same `EngineDB` interface (Task 3). Commit the script.

### Task 2: Engine-ready backend (paths, stop file, local mode flag)

**Files:**
- Modify: `backend/mediafactory/core/config.py` (add `local_mode: bool = False`)
- Modify: `backend/mediafactory/queue/worker.py`, `backend/mediafactory/cli.py` (stop file)
- Test: `tests/test_engine_backend.py`

**Interfaces:**
- Produces: `cli.stop_requested(data_dir: Path) -> bool` (true when `data_dir/engine.stop` exists); `mf worker` stops when SIGTERM **or** stop file; `Settings.local_mode`.

- [ ] Step 1: Tests: `test_worker_stops_when_stop_file_appears` (create file → `should_stop` true); `test_local_mode_setting_reads_env` (`MF_LOCAL_MODE=1` → `get_settings().local_mode is True`).
- [ ] Step 2: Run remotely, expect FAIL. Step 3: implement. Step 4: run, expect PASS. Step 5: commit.

### Task 3: Engine manager (`desktop_engine.py`)

**Files:**
- Create: `backend/mediafactory/desktop_engine.py`
- Test: `tests/test_desktop_engine.py` (pure logic; processes faked)

**Interfaces:**
- Produces:
  - `engine_dir(home: Path) -> Path` → `home / "data"`.
  - `secret_key(dir: Path) -> str` — created once in `engine.key` (urlsafe 48 bytes), reused.
  - `class SingleInstance(home: Path)`: `acquire() -> bool`; on False, `focus_existing() -> bool` (POST `http://127.0.0.1:<port>/__focus` read from `instance.json`); `release()`.
  - `class EngineDB(dir: Path)`: `start() -> str` (database URL), `stop()`.
  - `class Engine(home: Path, exe: list[str])`: `start(progress: Callable[[str], None]) -> int` (API port; runs migrate, spawns `exe + ["--engine","api","--port",p]` and `exe + ["--engine","worker"]` with env `MF_DATABASE_URL, MF_SECRET_KEY, MF_DATA_DIR, MF_LOCAL_MODE=1, MF_ALLOWED_HOSTS=["127.0.0.1","localhost"]`, PATH prefixed with bundled ffmpeg dir), `healthy() -> bool`, `watch()` (restart a dead child once, then mark `failed`), `stop(timeout_s=20)` (touch `engine.stop`, wait worker, terminate api, `EngineDB.stop()`, remove stop file), `cleanup_stale()` (kill PIDs from `engine.pids` left by a crash).
  - `state: Literal["starting","running","failed","stopped"]`, `last_error: str | None`, logs in `data/logs/{api,worker}.log` (RotatingFileHandler-style: 5 × 5 MB, implemented by child processes via `MF_LOG_FILE`).

- [ ] Step 1: Tests with fake `Popen`/`EngineDB`: key created once and reused; second `SingleInstance.acquire()` returns False while first holds; `stop()` writes stop file then kills after timeout; `cleanup_stale()` kills listed PIDs; `watch()` restarts once then sets `failed`.
- [ ] Step 2: FAIL → Step 3: implement → Step 4: PASS → Step 5: commit.

### Task 4: Desktop integration (modes, proxy target, entry points, updater)

**Files:**
- Modify: `backend/mediafactory/desktop.py`, `backend/mediafactory/desktop_update.py`, `packaging/desktop_entry.py`, `backend/mediafactory/cli.py` (`api` accepts `--log-file`)
- Test: `tests/test_desktop.py` (extend)

**Interfaces:**
- Consumes: Task 3 `Engine`, `SingleInstance`.
- Produces: `Config.mode -> "local"|"remote"` (`remote` if `server_url` saved or `MF_SERVER_URL` set; else `local`; `local` forced to `remote` with a note on non-Windows in v0.5.0); `Config.target_url` (engine URL in local mode, `server_url` in remote); `DEFAULT_SERVER` removed; desktop handler routes `/__engine` (state JSON), `/__focus`, `/__mode` (POST switch + restart); `desktop_entry.py` dispatches `--engine api|worker` to `cli` before importing webview; updater calls `engine.stop()` before `os._exit`.

- [ ] Step 1: Tests: old config with `server_url` → `mode == "remote"`; empty config on win32 → `local`; empty config on linux → `remote` with no default URL (offline card asks for address); `--engine worker` argv runs the worker entry (monkeypatched) without importing webview.
- [ ] Step 2–4: FAIL → implement → PASS. Step 5: commit.

### Task 5: Provider options + client per-service tweaks

**Files:**
- Create: `backend/mediafactory/db/migrations/versions/0009_provider_options.py` (add `ai_providers.options` JSONB, default `{}`)
- Modify: `backend/mediafactory/db/models/ai.py`, `backend/mediafactory/ai/client.py`, `backend/mediafactory/api/routes/providers.py`, `backend/mediafactory/portability.py` (export/import options)
- Test: `tests/test_provider_options.py`

**Interfaces:**
- Produces: `AIProvider.options: dict` keys `json_mode: "auto"|"prompt"`, `headers: dict[str,str]`, `check: "models"|"chat"`; `client.chat` with `json_mode="prompt"` sends no `response_format` and adds the JSON instruction on the first attempt; extra headers merged (never overriding Authorization); `client.check_key(provider, model) -> list[str]` (models list, or `[model]` after a 1-token chat when `check == "chat"`).

- [ ] Step 1: Tests (respx): prompt-mode request body has no `response_format` and system message starts with `JSON_INSTRUCTION`; header merge; `check_key` chat path sends `max_tokens: 1`.
- [ ] Step 2–4. Step 5: commit.

### Task 6: Presets + discovery + `/api/ai-setup`

**Files:**
- Create: `backend/mediafactory/ai/presets.py`, `backend/mediafactory/ai/discovery.py`, `backend/mediafactory/api/routes/ai_setup.py`
- Modify: `backend/mediafactory/api/app.py`
- Test: `tests/test_ai_setup.py`

**Interfaces:**
- Produces:
  - `presets.PRESETS: list[dict]` with `id, name, base_url, key_url, models (recommended, first = default), options` for openai, anthropic (`json_mode: prompt`, `check: chat`), gemini, openrouter, groq, deepseek, mistral, xai.
  - `discovery.TOOLS` (spec §3.4 table) and `discovery.scan(host="127.0.0.1", *, http=None) -> list[{tool, base_url, models}]` (400 ms per probe, parallel, Ollama told apart via `/api/version`).
  - Routes: `GET /api/ai-setup` → `{local_mode, presets, configured: bool}`; `GET /api/ai-setup/scan`; `POST /api/ai-setup/check {base_url?|preset?, api_key?}` → `{ok, models, error}`; `POST /api/ai-setup/apply {base_url|preset, api_key?, name?, script_model, classify_model, mode: "primary"|"only"}` → provider + routes (primary = prepend, keep old steps; only = replace); `POST /api/ai-setup/try` → `{ok, seconds, sample: {tr, en}, error}` via `run_task(..., "script")` short prompt; `POST /api/ai-setup/done` sets `SystemSetting "setup" = {"done": true, "at": ...}`.
  - Custom `base_url` in `check/apply` → 403 unless `settings.local_mode`; presets always allowed.
  - Error messages mapped to plain text (401/403 → "the key is not valid", 404 model → "model not found", timeout → "too slow — choose a smaller model").

- [ ] Step 1: Tests: presets list shape; scan finds a respx-mocked Ollama on 11434 and LM Studio on 1234; custom URL refused when not local mode, allowed with `MF_LOCAL_MODE=1`; apply primary keeps existing steps after the new one; apply only replaces; try returns sample with mocked `run_task`; done flag set; api key never in any response.
- [ ] Step 2–4. Step 5: commit.

### Task 7: Model pre-download endpoint

**Files:**
- Modify: `backend/mediafactory/api/routes/ai_setup.py` (or new `routes/setup_assets.py`), reuse `pipeline/tts.py` voice download and `pipeline/align.py` model load
- Test: `tests/test_setup_assets.py`

**Interfaces:**
- Produces: `POST /api/setup/assets` starts a background thread downloading default Piper voices (TR + EN defaults from voices catalog) and the whisper model used by `align.py`; `GET /api/setup/assets` → `{state: idle|running|done|failed, done: n, total: n, current, error}`. Idempotent; already-present files count as done.

- [ ] Step 1: Tests with download functions monkeypatched: progress goes 0→total; second POST while running doesn't start another; failure reported.
- [ ] Step 2–4. Step 5: commit.

### Task 8: Panel — Easy Setup wizard and mode-aware UI

**Files:**
- Create: `backend/mediafactory/web/setup.js`
- Modify: `backend/mediafactory/web/index.html`, `backend/mediafactory/web/app.js`

**Interfaces:**
- Consumes: Task 6/7 routes, desktop `/__engine` and `/__mode`.
- Produces: route `#setup` (6 steps per spec §3.3: welcome+language, preparation, AI tabs [this computer / my server / AI service], models, try, done); opened automatically when `GET /api/ai-setup` says not configured and `local_mode`; Settings card "🤖 Easy Setup" to rerun; Settings → Advanced: mode switch (local disabled with "coming soon" off Windows); offline card only in remote mode and without Tailscale text; server-update and server-address cards hidden in local mode; Overview shows engine state + data folder.

- [ ] Step 1: `node --check` on changed JS.
- [ ] Step 2: Run the API locally against the Task 1 pgserver spike DB (`MF_LOCAL_MODE=1`) via `.claude/launch.json` entry `mf-local` and drive the wizard in the browser pane: scan (none found → download links), AI service tab with a fake key → readable error, my-server tab with an unreachable URL → readable error. Screenshot each step.
- [ ] Step 3: Commit.

### Task 9: install.sh publish scope

**Files:**
- Modify: `deploy/install.sh`, `docs/DEPLOYMENT.md`

- [ ] Step 1: When `.env` is new and stdin is a TTY, ask: 1) this machine only (default, `127.0.0.1`), 2) local network (`0.0.0.0`), 3) Tailscale address (offered only if `tailscale ip -4` works). Non-interactive: keep `MF_PUBLISH_ADDR` env or default `127.0.0.1` (no more automatic Tailscale).
- [ ] Step 2: `bash -n deploy/install.sh`; dry run on CT 175 in a temp copy with `MF_PUBLISH_ADDR=0.0.0.0` non-interactive → `.env` has `0.0.0.0`. Commit.

### Task 10: Windows packaging with the engine

**Files:**
- Modify: `packaging/build_windows.ps1`, `packaging/installer.iss`
- Create: `packaging/fetch_ffmpeg.ps1` (downloads a pinned LGPL win64 build from a fixed URL, verifies SHA256, extracts `ffmpeg.exe`/`ffprobe.exe` + license into `packaging/ffmpeg/`)

- [ ] Step 1: PyInstaller: `--collect-all pgserver --collect-all faster_whisper --collect-all ctranslate2 --collect-all piper --collect-all onnxruntime --hidden-import mediafactory.pipeline.handlers`, add `packaging/ffmpeg` as `ffmpeg/`; console-less child processes (`CREATE_NO_WINDOW`).
- [ ] Step 2: Smoke: `MF_DESKTOP_SMOKE=60` with a fresh `LOCALAPPDATA` → engine reaches `running`, `/api/health` 200, then exit leaves no `postgres`/child processes. Expected: exit 0, `Get-Process postgres` empty.
- [ ] Step 3: Commit.

### Task 11: Windows end-to-end production

- [ ] Step 1: With the packaged app (fresh data dir), run Easy Setup against an OpenAI-compatible endpoint the owner already has (9router via its network address, entered under "my server"), download assets, make one 30 s TR video from the Studio.
- [ ] Step 2: Fix any Windows-only breakage found (paths, fonts, ffmpeg filters, Piper, whisper) each with a regression test where the code is cross-platform; ledger Rulings for anything disabled on Windows with the on-screen reason.
- [ ] Step 3: Full remote suite green; commit.

### Task 12: Docs and release v0.5.0 (Windows)

- [ ] Step 1: README install section: download the app first; server install becomes "Advanced". ROADMAP plan 16 entry; DEPLOYMENT notes.
- [ ] Step 2: Bump version to 0.5.0; build Windows installer; GitHub release with the Windows asset (macOS/Linux workflow still builds remote-only assets for the tag).
- [ ] Step 3: Update the download site (backup `index.html`/`script.js` first; dynamic GitHub lookup already picks the newest assets — verify the Windows link shows 0.5.0).
- [ ] Step 4: Deploy server (`/api/system/update`) so remote-mode users get the new panel.
