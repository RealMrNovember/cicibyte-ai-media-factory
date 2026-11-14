# Plan 1 — Temel (Foundation) Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kendi sunucuna kurulabilen, güvenli varsayılanlı bir FastAPI + PostgreSQL iskeleti. Kimlik doğrulama, denetim kaydı, şifreli gizli bilgiler, AI sağlayıcı kayıt defteri, görev yönlendirme (sıralı yedek + 3 sn bekleme), veritabanı tabanlı iş kuyruğu ve worker, Docker Compose kurulumu.

**Architecture:** Tek Python paketi `mediafactory` iki giriş noktasıyla çalışır: `mf api` (FastAPI) ve `mf worker` (kuyruk işleyici). Tüm durum PostgreSQL'de; kuyruk `SELECT … FOR UPDATE SKIP LOCKED` ile alınır. Bu plan medya üretmez. Sonraki planlar (2: kaynaklar, 3: üretim hattı + medya, 4: panel, 5: YouTube) bu temelin üzerine aşama işleyicileri ve router'lar ekler.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x (sync, psycopg 3), Alembic, pydantic-settings, argon2-cffi, cryptography (Fernet), httpx, Typer (CLI), pytest + respx, Docker Compose, PostgreSQL 16.

**Spec:** `docs/superpowers/specs/2026-11-14-media-factory-design.md` (ana ürün şartnamesi: `CiciByte_AI_Media_Factory_Project_Spec.md`)

## Plan dizisi
1. **Temel** ← bu plan
2. Kaynaklar ve alım (adaptörler, dedup, hak kaydı, kaynak API'si)
3. Üretim hattı ve medya (classify, script + Script Doctor, Kokoro/Piper TTS, faster-whisper altyazı, arka plan kütüphanesi + Coverr/Mixkit, render, thumbnail, QC, Hazır Video Kataloğu, çok dilli üretim)
4. Panel (React + TS, tr/en, tüm sayfalar)
5. YouTube yayıncı (OAuth bağlama, şifreli token, private yükleme, idempotency) ve DL380 dağıtımı

## Global Constraints

- Python `>=3.12`. Paket adı `mediafactory`, CLI komutu `mf`.
- Lisans MIT, telif satırı: `Copyright (c) 2026 CiciByte Technology, Inc.`. purffle-shorts'tan uyarlanan her dosyanın başına: `# Adapted from purffle-shorts (MIT, Copyright (c) 2025 Purffle), commit 514fd2547227b98d951dfc1489fc8c7ce72f1b68`.
- Marka metni: "Powered by CiciByte Technology" → `https://cicibyte.com`. Bağış: `https://buymeacoffee.com/mikeross`.
- Commit mesajlarında **hiçbir Claude/Anthropic atfı veya `Co-Authored-By` satırı yok.**
- Runtime'da ücretli API zorunlu değil. `anthropic` paketi bağımlılık değildir.
- Ortam değişkenlerinin hepsi `MF_` önekli. `.env` git'e girmez; `.env.example` gerçek gizli bilgi içermez.
- `api` varsayılan bağlantı adresi `127.0.0.1:8080`.
- Docker image'ları sürümü sabitlenmiş etiketlerle (`latest` yok), root olmayan kullanıcıyla çalışır.
- Gizli bilgiler (API anahtarları, token'lar) veritabanında Fernet ile şifreli; loglara maskeleyiciden geçerek yazılır.
- Görev yönlendirme varsayılanları: tur sayısı `3`, turlar arası bekleme `3` sn. Yerel sağlayıcı zaman aşımı `600` sn, uzak `120` sn. Yerel LLM eşzamanlılığı `1`.
- İş sınıfı eşzamanlılık varsayılanları: `llm=1`, `render=1`, `tts=1`, `stt=1`, `io=4`.
- Durum makinesi değerleri (şartname §13): `discovered, normalized, classified, rights_review, script_draft, script_approved, voice_generated, subtitles_generated, visuals_ready, rendering, quality_check, needs_review, approved, scheduled, uploading, published, rejected, failed, retry_wait, archived`.

## Review Focus

1. **PostgreSQL kapalıyken başlatma:** `api` çökmemeli, `/api/health` 503 ve `{"db":"down"}` dönmeli. `worker` 5 sn aralıklarla yeniden bağlanmayı denemeli. → Görev 9 ve Görev 8 testleri.
2. **`MF_SECRET_KEY` eksik veya değişmiş:** Uygulama açıklayıcı bir hatayla başlamamalı (anahtar eksikse). Anahtar değiştiyse şifre çözme `SecretDecryptError` fırlatmalı, bozuk veri döndürmemeli. → Görev 2.
3. **İki worker aynı anda:** Aynı aşama iki kez alınmamalı. → Görev 8.
4. **Sağlayıcı JSON yerine HTML hata sayfası veya boş yanıt döndürüyor:** Yönlendirici bunu hata sayıp sıradakine geçmeli, istisna sızdırmamalı. → Görev 7.
5. **`mf create-admin` ikinci kez çalıştırılıyor:** Mevcut yöneticinin parolasını sessizce sıfırlamamalı; `--reset` olmadan hata vermeli. → Görev 4.

---

### Görev 1: Repo iskeleti ve GitHub reposu

**Files:**
- Create: `pyproject.toml`, `LICENSE`, `NOTICE`, `README.md`, `.gitignore`, `.env.example`, `backend/mediafactory/__init__.py`, `tests/test_smoke.py`
- Create (taşı): `docs/superpowers/specs/2026-11-14-media-factory-design.md`, `docs/superpowers/plans/2026-11-14-plan-1-foundation.md`, `docs/PROJECT_SPEC.md` (ana şartnamenin kopyası)

**Interfaces:**
- Produces: `mediafactory.__version__ = "0.1.0.dev0"`. Paket yolu `backend/` (`[tool.setuptools.packages.find] where = ["backend"]`). Komut `mf = "mediafactory.cli:app"` (CLI Görev 4'te yazılır; bu görevde `cli.py` boş bir Typer uygulaması olur).

- [ ] **Step 1:** Repo kökü `C:\Users\Captain\CicibyteProjects\cicibyte-ai-media-factory` olarak oluştur, `git init -b main`.
- [ ] **Step 2: Failing test yaz.** `tests/test_smoke.py`:
```python
import mediafactory
def test_version():
    assert mediafactory.__version__ == "0.1.0.dev0"
```
- [ ] **Step 3:** `pyproject.toml`. Bağımlılıklar: `fastapi`, `uvicorn[standard]`, `sqlalchemy>=2`, `psycopg[binary]>=3.1`, `alembic`, `pydantic-settings`, `argon2-cffi`, `cryptography`, `httpx`, `typer`. Dev: `pytest`, `respx`, `ruff`. Ruff ve pytest ayarlarında `testpaths=["tests"]` ve `pythonpath=["backend"]`. Sonra `__init__.py` yaz.
- [ ] **Step 4:** Çalıştır: `python -m venv .venv && .venv/Scripts/pip install -e ".[dev]" && .venv/Scripts/pytest -q`. Beklenen: `1 passed`.
- [ ] **Step 5:** `LICENSE` (MIT, Global Constraints'teki telif satırı). `NOTICE`: purffle-shorts MIT metni, telif satırı ve commit hash'i. `README.md`: ürün özeti, "Powered by CiciByte Technology" rozeti ve bağlantısı, Buy Me a Coffee rozeti, "kurulum yakında" bölümü. `.gitignore`: `.venv/`, `.env`, `data/`, `__pycache__/`, `node_modules/`. `.env.example`: Görev 2'deki değişkenler, boş değerlerle.
- [ ] **Step 6:** Spec, plan ve ana şartnameyi `docs/` altına kopyala.
- [ ] **Step 7: Commit:** `git add -A && git commit -m "chore: project skeleton, license and docs"`
- [ ] **Step 8:** `gh repo create RealMrNovember/cicibyte-ai-media-factory --public --source . --remote origin --push --description "Self-hosted, open-source AI YouTube media factory. Powered by CiciByte Technology."`. Beklenen: repo URL'si yazdırılır.

### Görev 2: Ayarlar, şifreleme ve maskeleme

**Files:**
- Create: `backend/mediafactory/core/config.py`, `core/crypto.py`, `core/redact.py`
- Test: `tests/core/test_config.py`, `tests/core/test_crypto.py`, `tests/core/test_redact.py`

**Interfaces:**
- Produces:
  - `Settings` (pydantic-settings, `env_prefix="MF_"`) alanları:
    - `database_url: str`
    - `secret_key: SecretStr`
    - `data_dir: Path = Path("/data")`
    - `bind_host: str = "127.0.0.1"`, `bind_port: int = 8080`
    - `allowed_hosts: list[str] = ["localhost","127.0.0.1"]`
    - `session_ttl_hours: int = 72`
  - `get_settings() -> Settings` (lru_cache)
  - `encrypt(plaintext: str) -> str` ve `decrypt(token: str) -> str`. Hata durumunda `SecretDecryptError`.
  - `redact(text: str) -> str`

- [ ] **Step 1: Failing testler:**
  - `test_missing_secret_key_raises`: `MF_SECRET_KEY` yoksa `Settings()` ValidationError fırlatır.
  - `test_secret_key_too_short_rejected`: 32 karakterden kısa anahtar reddedilir.
  - `test_roundtrip`: `decrypt(encrypt("sk-abc")) == "sk-abc"`.
  - `test_wrong_key_raises`: başka anahtarla `decrypt` → `SecretDecryptError`.
  - `test_redact_masks`: `redact("Authorization: Bearer sk-1234567890abcdef")` içinde `sk-1234567890abcdef` geçmez, `"Bearer ****"` geçer. `redact("https://x/?key=abc123&q=1")` → `key=****`. `api_key=…`, `token=…` ve `"password": "…"` biçimleri de maskelenir.
- [ ] **Step 2:** `pytest tests/core -q` → FAIL (modül yok).
- [ ] **Step 3:** Uygula. Fernet anahtarı, `secret_key`'den HKDF-SHA256 ile türetilir (`info=b"mediafactory-secrets"`). Böylece kullanıcı anahtar olarak düz metin verebilir.
- [ ] **Step 4:** `pytest tests/core -q` → PASS.
- [ ] **Step 5: Commit:** `feat(core): settings, secret encryption and log redaction`

### Görev 3: Veritabanı, modeller ve göçler

**Files:**
- Create:
  - `backend/mediafactory/db/base.py`, `db/session.py`
  - `db/models/{__init__,user,audit,settings,ai,jobs}.py`
  - `backend/mediafactory/db/migrations/` (Alembic `env.py`, `versions/0001_foundation.py`), `alembic.ini`
  - `deploy/docker-compose.test.yml`
  - `tests/conftest.py`
- Test: `tests/db/test_migrations.py`

**Interfaces:**
- Produces:
  - `get_engine()`, `SessionLocal`, `session_scope()` (context manager).
  - **Modeller** (sütunlar şartname §14 ve tasarım §12'ye göre):
    - `User(id, email unique, password_hash, role: "admin"|"editor", is_active, created_at, last_login_at)`
    - `AuditLog(id, at, actor_id nullable, action: str, target_type, target_id, details JSONB, ip)`
    - `SystemSetting(key pk, value JSONB, updated_at)`
    - `AIProvider(id, name unique, kind: "openai_compatible"|"ollama_native", base_url, api_key_enc nullable, locality: "local"|"remote", timeout_s int, max_concurrency int, enabled bool, created_at)`
    - `AITaskRoute(id, task: "script"|"classify"|"tts"|"stt"|"image" unique, steps JSONB [{provider_id, model}], rounds int=3, retry_delay_s float=3.0)`
    - `ProductionJob(id, status: str (durum makinesi), concept_id nullable, source_item_id nullable, language, content_group nullable, payload JSONB, created_at, updated_at)`
    - `JobStageRun(id, job_id fk, stage: str, job_class: "llm"|"tts"|"stt"|"render"|"io", state: "queued"|"running"|"succeeded"|"failed"|"retry_wait"|"cancelled", attempts int, max_attempts int=3, run_after timestamptz, started_at, finished_at, inputs JSONB, outputs JSONB, log text, error text, locked_by text)`. İndeks: `(state, job_class, run_after)`.
  - `conftest.py`: `TEST_DATABASE_URL` (varsayılan `postgresql+psycopg://mf:mf@127.0.0.1:55432/mf_test`). Oturum başında `alembic upgrade head`. Test başına transaction + rollback fixture'ı `db`.

- [ ] **Step 1:** `deploy/docker-compose.test.yml`: `postgres:16.6-alpine`, port `55432:5432`, kullanıcı/parola/db `mf/mf/mf_test`. `docker compose -f deploy/docker-compose.test.yml up -d`.
- [ ] **Step 2: Failing testler:**
  - `test_upgrade_creates_tables`: Yukarıdaki 7 tablo var.
  - `test_downgrade_base_is_clean`: `downgrade base` sonrası tablo kalmaz, ardından `upgrade head` tekrar çalışır.
- [ ] **Step 3:** `pytest tests/db -q` → FAIL.
- [ ] **Step 4:** Modelleri ve `0001_foundation` göçünü yaz. Göç modellerden elle yazılır; autogenerate çıktısı gözden geçirilerek kullanılır.
- [ ] **Step 5:** `pytest tests/db -q` → PASS.
- [ ] **Step 6: Commit:** `feat(db): foundation models and initial migration`

### Görev 4: Kimlik doğrulama, roller ve yönetici oluşturma

**Files:**
- Create: `backend/mediafactory/auth/{passwords,sessions,deps,service}.py`, `backend/mediafactory/api/routes/auth.py`, `backend/mediafactory/cli.py`
- Test: `tests/auth/test_auth.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `User`, `session_scope`, `get_settings`, `record_audit` (Görev 5; bu görevde çağrı noktası bırakılır, Görev 5'te bağlanır).
- Produces:
  - `hash_password(p) -> str`, `verify_password(p, h) -> bool` (Argon2id).
  - Oturum: imzalı çerez `mf_session`. Ayarlar: HttpOnly, `SameSite=Strict`, `Secure` (yalnızca HTTPS'te). Ömür: `session_ttl_hours`.
  - CSRF: `mf_csrf` çerezi + `X-CSRF-Token` başlığı, tüm değiştirici isteklerde zorunlu.
  - `require_user` ve `require_admin` FastAPI bağımlılıkları.
  - Uç noktalar:
    - `POST /api/auth/login {email,password}` → `200 {user}`
    - `POST /api/auth/logout`
    - `GET /api/auth/me`
  - Giriş hız sınırı: aynı IP ve e-posta için 15 dakikada 5 başarısız deneme → `429`.
  - CLI: `mf create-admin --email X [--reset]`. Rastgele 20 karakterlik bir parola üretir, yalnızca stdout'a yazar. Admin zaten varsa `--reset` olmadan çıkış kodu 1.

- [ ] **Step 1: Failing testler:**
  - `test_login_ok_sets_cookie`
  - `test_login_wrong_password_401`
  - `test_sixth_failed_login_429`
  - `test_post_without_csrf_403`
  - `test_editor_forbidden_on_admin_route_403` (test için `GET /api/admin/ping` rotası `require_admin` ile korunur)
  - `test_create_admin_twice_without_reset_fails` (Review Focus 5)
  - `test_create_admin_reset_changes_password`
- [ ] **Step 2:** `pytest tests/auth tests/test_cli.py -q` → FAIL.
- [ ] **Step 3:** Uygula.
- [ ] **Step 4:** Aynı komut → PASS.
- [ ] **Step 5: Commit:** `feat(auth): argon2 login, sessions, csrf, roles and admin bootstrap`

### Görev 5: Denetim kaydı

**Files:**
- Create: `backend/mediafactory/audit/service.py`, `backend/mediafactory/api/routes/audit.py`
- Modify: `auth/service.py` (giriş, çıkış ve başarısız girişi kaydet)
- Test: `tests/audit/test_audit.py`

**Interfaces:**
- Produces:
  - `record_audit(session, *, actor_id: int|None, action: str, target_type: str|None=None, target_id: str|None=None, details: dict|None=None, ip: str|None=None) -> None`. `details` kaydedilmeden önce her string değer `redact` edilir.
  - `GET /api/audit?limit=&before_id=` (admin) → sayfalı liste, yeniden eskiye.

- [ ] **Step 1: Failing testler:**
  - `test_login_is_audited` (`action == "auth.login"`)
  - `test_details_are_redacted` (`details={"api_key":"sk-secret123456"}` kayıtta görünmez)
  - `test_audit_list_admin_only`
- [ ] **Step 2:** FAIL. **Step 3:** Uygula. **Step 4:** PASS.
- [ ] **Step 5: Commit:** `feat(audit): audit log service and endpoint`

### Görev 6: AI sağlayıcı kayıt defteri ve OpenAI uyumlu istemci

**Files:**
- Create:
  - `backend/mediafactory/ai/client.py`: purffle `llm.py`'den uyarlanır, MIT başlığıyla.
  - `ai/jsonparse.py`: purffle `extract_json`'dan uyarlanır.
  - `ai/providers.py`
  - `api/routes/providers.py`
- Test: `tests/ai/test_client.py`, `tests/ai/test_jsonparse.py`, `tests/ai/test_providers_api.py`

**Interfaces:**
- Consumes: `AIProvider`, `encrypt`/`decrypt`, `record_audit`, `require_admin`.
- Produces:
  - `class ChatResult(text: str, model: str, provider_id: int, usage: dict)`.
  - `class ProviderError(Exception)` (alanlar: `retryable: bool`, `status: int|None`).
  - `chat(provider: AIProvider, model: str, messages: list[dict], *, json_schema: dict|None=None, max_tokens: int|None=None, temperature: float|None=None) -> ChatResult`
    - `locality=="local"` ise `stream=True` ile okur. Zaman aşımı `provider.timeout_s`.
    - `json_schema` verilmişse sırayla dener: `response_format={"type":"json_schema",...}`, ardından `{"type":"json_object"}`, ardından prompt'a "yalnızca JSON döndür" eki. 400/422 yanıtı bir sonraki biçime geçirir.
    - 2xx dışı yanıt, HTML gövde veya ayrıştırılamayan gövde → `ProviderError`. 429/5xx/zaman aşımı/bağlantı hatasında `retryable=True`.
  - `extract_json(text: str) -> dict|list`: Kod çitlerini (```) ve sondaki virgülleri temizler, ilk geçerli JSON nesnesini bulur. Bulamazsa `ValueError`.
  - REST (admin): `GET/POST /api/providers`, `PATCH/DELETE /api/providers/{id}`, `POST /api/providers/{id}/test`. Test uç noktası `GET {base_url}/models` çağırır ve `{ok, models:[...]}` döner. Yanıtlarda `api_key` hiçbir zaman dönmez, yalnızca `has_api_key: bool` döner.

- [ ] **Step 1: Failing testler** (respx ile):
  - `test_chat_plain_text`
  - `test_chat_streaming_local_concatenates_chunks`
  - `test_json_schema_falls_back_to_json_object_on_400`
  - `test_html_error_page_raises_provider_error` (Review Focus 4)
  - `test_timeout_is_retryable`
  - `test_extract_json_handles_fences_and_trailing_commas`
  - `test_api_key_never_returned`
  - `test_api_key_stored_encrypted` (veritabanındaki değer düz anahtar değildir)
  - `test_provider_create_is_audited`
- [ ] **Step 2:** FAIL. **Step 3:** Uygula. **Step 4:** PASS.
- [ ] **Step 5: Commit:** `feat(ai): provider registry and openai-compatible client`

### Görev 7: Görev yönlendirme (sıralı yedek + 3 sn bekleme)

**Files:**
- Create: `backend/mediafactory/ai/router.py`, `api/routes/task_routes.py`
- Test: `tests/ai/test_router.py`

**Interfaces:**
- Consumes: `chat`, `ProviderError`, `AITaskRoute`, `AIProvider`.
- Produces:
  - `run_task(session, task: str, messages: list[dict], *, json_schema: dict|None=None, max_tokens: int|None=None, sleep=time.sleep) -> ChatResult`
    - Rotadaki adımları sırayla dener. Bir adım başarısız olursa sıradakine geçer. Etkin olmayan sağlayıcılar atlanır.
    - Tüm adımlar başarısız olursa `sleep(route.retry_delay_s)` çağırır ve en fazla `route.rounds` tur tekrarlar.
    - Sonunda `TaskFailed(task, errors: list[str])` fırlatır.
    - Rota yoksa `TaskNotConfigured(task)`.
  - REST (admin): `GET /api/task-routes`, `PUT /api/task-routes/{task}` (`steps`, `rounds`, `retry_delay_s`).

- [ ] **Step 1: Failing testler:**
  - `test_first_step_success_no_fallback`
  - `test_falls_back_to_second_step`
  - `test_sleeps_3s_between_rounds_and_stops_after_3_rounds`: sahte `sleep` çağrıları `[3.0, 3.0]`, toplam deneme `3 × adım sayısı`.
  - `test_disabled_provider_skipped`
  - `test_unconfigured_task_raises`
- [ ] **Step 2:** FAIL. **Step 3:** Uygula. **Step 4:** PASS.
- [ ] **Step 5: Commit:** `feat(ai): task routing with ordered fallback and retry delay`

### Görev 8: Veritabanı kuyruğu ve worker

**Files:**
- Create: `backend/mediafactory/queue/{jobs,claim,worker,registry}.py`
- Modify: `cli.py` (`mf worker` komutu)
- Test: `tests/queue/test_claim.py`, `tests/queue/test_worker.py`

**Interfaces:**
- Consumes: `ProductionJob`, `JobStageRun`, `session_scope`.
- Produces:
  - `create_job(session, *, status="discovered", **fields) -> ProductionJob`
  - `enqueue_stage(session, job_id: int, stage: str, job_class: str, inputs: dict|None=None, max_attempts=3) -> JobStageRun`
  - `claim_next(session, *, worker_id: str, limits: dict[str,int]) -> JobStageRun|None`: `state='queued' AND run_after<=now()` koşulu, `ORDER BY run_after, id`, `FOR UPDATE SKIP LOCKED`. Sınıfın çalışan iş sayısı sınırdaysa o sınıfı atlar.
  - Stage registry: `@stage_handler(stage: str, job_class: str)` dekoratörü. Handler imzası `(ctx: StageContext) -> StageOutcome`.
    - `StageContext(session, job, run, log: Callable[[str],None], settings)`
    - `StageOutcome(next_status: str, outputs: dict, next_stage: tuple[str,str]|None)`
  - Worker döngüsü:
    - **Başarı:** `run` succeeded olur, `job.status = next_status`. `next_stage` varsa yeni bir run kuyruğa eklenir.
    - **İstisna:** `attempts < max_attempts` ise `retry_wait`, `run_after = now + 30s × 2^(attempts-1)`. Aksi halde run `failed`, `job.status = "failed"`.
  - `retry_failed(session, job_id)`: Yalnızca son başarısız aşamayı yeniden kuyruğa ekler; önceki başarılı aşamalar yeniden çalışmaz.
  - `cancel_job(session, job_id)`: Kuyruktaki run'ları `cancelled` yapar. Çalışan handler kontrol noktalarında `ctx.is_cancelled()` ile durur.
  - Veritabanı yoksa worker döngüsü 5 sn bekleyip yeniden dener ve çökmez.

- [ ] **Step 1: Failing testler:**
  - `test_two_workers_never_claim_same_run` (Review Focus 3): iki ayrı bağlantı + iş parçacığı, 20 run; her run tam bir kez alınır.
  - `test_class_limit_respected` (`render=1` iken ikinci render alınmaz)
  - `test_success_advances_status_and_enqueues_next`
  - `test_failure_goes_retry_wait_with_backoff`
  - `test_failure_after_max_attempts_marks_job_failed`
  - `test_retry_failed_reruns_only_failed_stage`
  - `test_cancel_marks_queued_cancelled`
  - `test_worker_survives_db_outage`: `claim_next` OperationalError fırlatınca döngü sahte `sleep(5)` çağırır ve devam eder.
- [ ] **Step 2:** FAIL. **Step 3:** Uygula. **Step 4:** PASS.
- [ ] **Step 5: Commit:** `feat(queue): postgres skip-locked queue, stage registry and worker`

### Görev 9: API uygulaması, sağlık kontrolü ve güvenlik başlıkları

**Files:**
- Create: `backend/mediafactory/api/app.py`
- Modify: `cli.py` (`mf api` komutu: uvicorn, `bind_host`/`bind_port`)
- Test: `tests/api/test_app.py`

**Interfaces:**
- Produces:
  - `create_app(settings: Settings|None=None) -> FastAPI`: Önceki görevlerdeki router'ları bağlar.
  - `GET /api/health` (kimlik doğrulama yok): `{"status":"ok","db":"up","version":…}`. Veritabanına ulaşılamazsa 503 ve `{"status":"degraded","db":"down"}`.
  - **Host başlığı kontrolü:** `allowed_hosts` dışında 400.
  - **Güvenlik başlıkları:** `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `X-Frame-Options: DENY`, panel için temel bir CSP.

- [ ] **Step 1: Failing testler:**
  - `test_health_ok`
  - `test_health_db_down_returns_503` (Review Focus 1; hatalı DB URL'siyle oluşturulan app)
  - `test_unknown_host_rejected`
  - `test_security_headers_present`
- [ ] **Step 2:** FAIL. **Step 3:** Uygula. **Step 4:** PASS. Ardından tüm paketi çalıştır: `pytest -q` → hepsi PASS.
- [ ] **Step 5: Commit:** `feat(api): app factory, health check and security headers`

### Görev 10: Docker Compose, kurulum ve yedekleme script'leri

**Files:**
- Create: `deploy/Dockerfile`, `deploy/docker-compose.yml`, `deploy/install.sh`, `deploy/backup.sh`, `deploy/restore.sh`, `docs/DEPLOYMENT.md` (ilk sürüm)
- Modify: `.env.example`, `README.md` (kurulum bölümü)

**Interfaces:**
- Produces: Compose servisleri:
  - `db`: `postgres:16.6-alpine`, kalıcı volume `mf_pg`.
  - `api`: Port `127.0.0.1:${MF_BIND_PORT:-8080}:8080`. Komut `mf api --host 0.0.0.0`, yalnızca container içinde.
  - `worker`: Komut `mf worker`.

  `api` ve `worker` aynı image'ı kullanır: `python:3.12.8-slim` tabanlı, `ffmpeg` kurulu, kullanıcı `mf` (uid 10001). Volume `mf_data:/data`.

  Başlangıçta `api`, `alembic upgrade head` çalıştırır. Healthcheck `/api/health`.

- [ ] **Step 1:** `install.sh` şunları yapar:
  - Docker ve Compose varlığını kontrol eder.
  - `.env` yoksa oluşturur: `MF_SECRET_KEY` (48 bayt base64) ve veritabanı parolası rastgele üretilir.
  - `docker compose up -d --build`.
  - Health beklenir.
  - `docker compose exec api mf create-admin --email "$ADMIN_EMAIL"` çalıştırılır; parola yalnızca terminale yazılır.
  - Script tekrar çalıştırılırsa mevcut `.env` dosyasına dokunmaz.
- [ ] **Step 2:** `backup.sh`: `pg_dump` ile `./backups/mf-YYYYmmdd-HHMM.sql.gz`, son 14 dosya saklanır. `restore.sh <dosya>`: onay sorusundan sonra geri yükler.
- [ ] **Step 3: Doğrulama:**
  - Temiz bir klasörde `bash deploy/install.sh` (Windows'ta Git Bash) → çıktıda `admin created`.
  - `curl -s http://127.0.0.1:8080/api/health` → `"db":"up"`.
  - `docker compose restart` sonrası health yeniden `up` ve admin hâlâ giriş yapabiliyor (kalıcılık).
  - `bash deploy/backup.sh` → bir `.sql.gz` dosyası oluşur. `restore.sh` ile geri yükleme sonrası kullanıcı tablosu aynı.
- [ ] **Step 4:** `docs/DEPLOYMENT.md`:
  - kurulum, güncelleme, yedekleme ve geri yükleme;
  - Tailscale veya ters proxy (Caddy örneği) ile erişim;
  - "panel doğrudan internete açılmaz" uyarısı.
- [ ] **Step 5: Commit + push:** `chore(deploy): docker compose, install, backup and restore scripts` → `git push`.

---

## Self-review notları
- **Kapsam:** Bu plan tasarımın §3 (kısıtlar), §5 (mimari, repo yapısı), §6 (sağlayıcı + görev yönlendirme), §8 (kuyruk ve iş sınıfları), §10 (güvenlik: kimlik doğrulama, roller, şifreleme, host kontrolü, root olmayan container), §11 (lisans, NOTICE, README markası), §12 (temel tablolar) ve §15'in temel testlerini karşılar.
- **Bilerek sonraki planlara bırakılanlar:**
  - SSRF engeli: Plan 2 (kaynak çekiciyle birlikte).
  - Kalan tablolar: Plan 2–5.
  - Panel alt bilgisi ve "Hakkında": Plan 4.
  - `OPERATIONS.md`, `SECURITY.md`, `SOURCE_RIGHTS.md`: ilgili planlarda.
