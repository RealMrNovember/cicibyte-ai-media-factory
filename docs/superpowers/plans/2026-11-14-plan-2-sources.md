# Plan 2 — Kaynaklar ve Alım (Sources & Ingest) Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Panelden tam yönetilen kaynaklar (Reddit RSS, resmî Reddit API, RSS/Atom, web sayfası, elle metin/dosya) ve bunların otomatik ve güvenli şekilde toplanıp tekilleştirilerek, hak kaydıyla "Gelen Kutusu"na düşmesi.

**Architecture:** Her adaptör aynı arayüzü uygular: `fetch(params, ctx) -> list[RawItem]`. Ağ çağrıları tek bir güvenli çekiciden (`SafeFetcher`) geçer. Bu çekici iç ağ adreslerini engeller (SSRF), yönlendirmeleri tek tek doğrular, boyut sınırı ve host başına hız sınırı uygular. `ingest.store_items` alınan öğeleri normalleştirir, kanonik URL ve içerik hash'iyle tekilleştirir, değişen içeriği "güncellendi" olarak işaretler ve `source_items` tablosuna yazar. Zamanlayıcı (`SourcePoller`) worker sürecinde ayrı bir thread olarak çalışır; zamanı gelen kaynakları `SKIP LOCKED` ile alır, hata durumunda üstel olarak geri çekilir. Bu plan iş (`production_jobs`) oluşturmaz; öğeleri işe çevirmek Plan 3'ün işidir.

**Tech Stack:** Plan 1'deki yığın + `defusedxml` (güvenli XML), `pypdf` ve `python-docx` (elle yüklenen PDF/DOCX), stdlib `urllib.robotparser`, `ipaddress`, `socket`.

**Spec:** `docs/superpowers/specs/2026-11-14-media-factory-design.md` §7 ve §16a (Reddit: RSS ana yol, resmî API kimlik bilgisi Ayarlar'dan), `docs/PROJECT_SPEC.md` §5.

## Global Constraints

- Plan 1'in Global Constraints'i aynen geçerli: MIT, `MF_` önekli ortam değişkenleri, commit'lerde Claude/Anthropic atfı yok, purffle'dan uyarlanan dosyalarda MIT başlığı.
- **Hak durumu değerleri** (şartname §5): `unknown`, `user_owned`, `licensed`, `permission_granted`, `public_domain`, `restricted`. **Varsayılan `unknown`.**
- **Adaptör anahtarları:** `reddit_rss`, `reddit`, `rss`, `web`, `manual`. Wattpad adaptörü **yok**; Wattpad içeriği yalnızca `manual` ile girer.
- **Kullanıcı ajanı:** `CiciByteMediaFactory/<sürüm> (+https://cicibyte.com)`.
- **SSRF:** Kaynak URL'leri ve tüm yönlendirme adımları için loopback, özel, link-local, CGNAT, multicast ve ayrılmış IPv4/IPv6 adresleri yasak (127/8, 10/8, 172.16/12, 192.168/16, 169.254/16, 100.64/10, 0/8, ::1, fc00::/7, fe80::/10). `MF_FETCH_ALLOWLIST` (host listesi) ile istisna tanınabilir.
- **Çekme sınırları:** Yanıt en fazla 5 MB. Zaman aşımı 20 sn. En fazla 5 yönlendirme. Aynı host'a iki istek arasında en az 2 sn.
- **Toplama sıklığı:** Kaynak başına dakika cinsinden, varsayılan 60, en az 10. Hata durumunda bir sonraki deneme `min(sıklık × 2^ardışık_hata, 24 saat)` sonra.
- **Roller:** Kaynak ve öğe yönetimi `editor` ve `admin` için açık. Kaynak kimlik bilgileri (Reddit API) yalnızca `admin`.
- **Kaynak silme yumuşaktır:** `deleted_at` doldurulur. Öğeler ve hak kayıtları kalır.

## Review Focus

1. **Bir RSS beslemesi XML bombası veya DTD ile dış varlık içeriyor:** Ayrıştırıcı reddetmeli; kaynak hata durumuna geçer, worker çökmez. → Görev 3.
2. **Herkese açık bir URL, `http://127.0.0.1:8080` veya `169.254.169.254`'e yönlendiriyor:** Yönlendirme adımında engellenmeli. → Görev 2.
3. **Aynı Reddit gönderisi farklı URL biçimleriyle geliyor** (`old.reddit.com`, sonda `/`, `?utm_source=`): Tek öğe olarak kalmalı. → Görev 5.
4. **Reddit 429 döndürüyor veya besleme boş geliyor:** Kaynak `last_error` alır ve geri çekilir; diğer kaynaklar etkilenmez. → Görev 8.
5. **Elle yüklenen dosya şifreli PDF, bozuk DOCX veya 10 MB'tan büyük:** 422 ile anlaşılır bir hata dönmeli, 500 dönmemeli. → Görev 7.

---

### Görev 1: Kaynak tabloları ve göç

**Files:**
- Create: `backend/mediafactory/db/models/sources.py`, `db/migrations/versions/0003_sources.py`
- Modify: `db/models/__init__.py`, `tests/db/test_migrations.py` (tablo listesi)

**Interfaces:**
- Produces:
  - Sabitler `RIGHTS_STATUSES`, `ADAPTERS`, `ITEM_STATUSES = ("discovered","updated","queued","used","rejected","archived")`.
  - `SourceConnector`
    - `id`, `name` (unique), `adapter`, `params: JSONB`
    - `credentials_enc: Text|None` (kaynağa özel gizli bilgi)
    - `enabled`, `poll_interval_min=60`
    - `next_run_at`, `last_run_at`, `last_success_at`, `last_error`
    - `consecutive_failures=0`, `items_total=0`
    - `default_rights="unknown"`, `default_language: str|None`
    - `created_at`, `deleted_at|None`
  - `SourceItem`
    - `id`, `source_id` (FK, `ondelete SET NULL`), `source_type`
    - `external_id`, `canonical_url` (unique, nullable), `title`, `author`
    - `published_at`, `fetched_at`
    - `raw_text`, `normalized_text`, `language`
    - `content_hash` (unique), `revision=1`
    - `rights_status="unknown"`, `attribution_required=False`
    - `processing_status="discovered"`, `error_message`
    - `meta: JSONB`
  - `SourceRightsRecord`: `id`, `item_id` (FK CASCADE), `from_status`, `to_status`, `note`, `actor_id`, `at`.
  - Göç `0003` (down_revision `0002`) ve CHECK kısıtları (hak durumu, adaptör, öğe durumu).

- [ ] **Step 1:** `test_upgrade_creates_tables` içindeki tablo kümesine `source_connectors`, `source_items`, `source_rights_records` ekle. Çalıştır, FAIL gör.
- [ ] **Step 2:** Modelleri ve `0003` göçünü yaz (autogenerate + gözden geçirme).
- [ ] **Step 3:** `pytest tests/db -q` → PASS. Commit: `feat(db): source connector, item and rights tables`

### Görev 2: Güvenli çekici (SSRF, boyut, hız, robots.txt)

**Files:**
- Create: `backend/mediafactory/core/net.py`
- Modify: `core/config.py` (`fetch_allowlist: list[str] = []`)
- Test: `tests/core/test_net.py`

**Interfaces:**
- Produces:
  - `class FetchError(Exception)` (`status: int|None`, `retryable: bool`)
  - `class BlockedAddress(FetchError)`
  - `class SafeFetcher(*, allowlist: list[str] = (), min_interval_s=2.0, max_bytes=5_000_000, timeout_s=20, max_redirects=5, resolver=socket.getaddrinfo, sleep=time.sleep, clock=time.monotonic, transport: httpx.BaseTransport|None=None)`. Testlerde transport `httpx.MockTransport` ile, resolver da sahte bir fonksiyonla değiştirilir.
    - `.get(url, *, headers=None) -> FetchedResponse(url, status, headers, content: bytes, text: str)`. Her adımda (yönlendirmeler dahil) host çözülür ve **her** IP kontrol edilir; tek bir yasak IP bile engeller.
    - Gövde akış olarak okunur; `max_bytes` aşılırsa `FetchError("response too large")`.
    - 429 ve 5xx → `retryable=True`.
    - `.robots_allowed(url) -> bool`: host başına önbellek. robots.txt yoksa (404) izin var. Çekme hatası olursa izin yok.
  - `is_public_ip(ip: str) -> bool`

- [ ] **Step 1: Failing testler:**
  - `test_blocks_loopback_literal` (`http://127.0.0.1/`)
  - `test_blocks_hostname_resolving_to_private` (sahte resolver `10.0.0.5`)
  - `test_blocks_redirect_to_metadata_ip` (MockTransport 302 → `http://169.254.169.254/`) (Review Focus 2)
  - `test_blocks_ipv6_ula_and_mapped` (`fd00::1`, `::ffff:127.0.0.1`)
  - `test_allowlist_permits_private_host`
  - `test_rejects_oversized_body` (6 MB akış)
  - `test_rate_limits_same_host` (sahte saat/uyku: aynı host'a ikinci istekte `sleep(≈2.0)`)
  - `test_robots_disallow_respected`
  - `test_non_http_scheme_rejected` (`file:///etc/passwd`, `ftp://`)
- [ ] **Step 2:** FAIL. **Step 3:** Uygula (`httpx.Client(follow_redirects=False)` + elle yönlendirme döngüsü). **Step 4:** PASS.
- [ ] **Step 5:** Commit: `feat(core): ssrf-safe fetcher with size, rate and robots limits`

### Görev 3: Normalleştirme, kanonik URL ve güvenli besleme ayrıştırma

**Files:**
- Create:
  - `backend/mediafactory/sources/text.py`: `strip_html` ve `extract_article`, purffle'dan uyarlanır (MIT başlığı).
  - `sources/urls.py`
  - `sources/feeds.py`
- Test: `tests/sources/test_text.py`, `test_urls.py`, `test_feeds.py`

**Interfaces:**
- Produces:
  - `strip_html(s) -> str`
  - `normalize_text(s) -> str`: HTML temizlenir, NFC uygulanır, boşluklar sadeleştirilir, sondaki "submitted by /u/…" Reddit imzası kaldırılır.
  - `content_hash(normalized: str) -> str`: `normalized.casefold()` değerinin SHA-256 hex'i.
  - `extract_article(html) -> tuple[str, str]`
  - `canonical_url(url) -> str`:
    - Şema ve host küçük harfe çevrilir; `www.` kaldırılır.
    - Fragment, `utm_*`, `fbclid`, `gclid`, `ref`, `share_id` parametreleri silinir.
    - Kalan sorgu parametreleri sıralanır.
    - Sondaki `/` kaldırılır.
    - Reddit: `old.`/`new.`/`np.` → `reddit.com`; `/r/<sub>/comments/<id>/...` → `https://reddit.com/r/<sub>/comments/<id>`.
  - `parse_feed(content: bytes) -> list[FeedEntry(id, link, title, author, published_at, content_html, summary_html)]`:
    - RSS 2.0 ve Atom desteklenir; `defusedxml.ElementTree` kullanılır.
    - DTD veya varlık (entity) içeren girdi → `FeedError`.

- [ ] **Step 1: Failing testler:**
  - `test_strip_html_and_entities`
  - `test_normalize_removes_reddit_signature`
  - `test_hash_ignores_case_and_whitespace`
  - `test_canonical_url_strips_tracking`
  - `test_canonical_reddit_variants_equal`: `https://old.reddit.com/r/nosleep/comments/abc/title/?utm_source=x` ile `https://www.reddit.com/r/nosleep/comments/abc` aynı sonucu verir.
  - `test_parse_rss_items`, `test_parse_atom_entries`
  - `test_billion_laughs_rejected` (Review Focus 1)
  - `test_external_entity_rejected`
  - `test_extract_article_skips_nav`
- [ ] **Step 2:** FAIL. **Step 3:** Uygula. **Step 4:** PASS.
- [ ] **Step 5:** Commit: `feat(sources): text normalization, canonical urls and safe feed parsing`

### Görev 4: Adaptör arayüzü ve RSS/Reddit RSS/web adaptörleri

**Files:**
- Create: `backend/mediafactory/sources/adapters/{__init__,base,rss,reddit_rss,web}.py`
- Test: `tests/sources/test_adapters.py` (kayıtlı örnek beslemeler `tests/sources/fixtures/*.xml`)

**Interfaces:**
- Consumes: `SafeFetcher`, `parse_feed`, `normalize_text`, `extract_article`, `canonical_url`.
- Produces:
  - `RawItem(external_id: str, url: str|None, title: str, text: str, author: str|None=None, published_at: datetime|None=None, language: str|None=None, meta: dict = {})`
  - `class AdapterError(Exception)` (`retryable: bool`)
  - `class Adapter(Protocol)`:
    - `key: str`
    - `validate(params: dict) -> dict`: Normalleştirilmiş parametreleri döndürür; geçersizse `ValueError`.
    - `fetch(params: dict, ctx: FetchContext) -> list[RawItem]`
  - `FetchContext(fetcher: SafeFetcher, credentials: dict|None)`
  - `get_adapter(key) -> Adapter`, `ADAPTER_REGISTRY`
  - Adaptör parametreleri:
    - `rss`: `{url, max_items=25}`
    - `reddit_rss`: `{subreddit (^[A-Za-z0-9_]{2,21}$), sort: hot|new|top|rising="top", time: hour|day|week|month|year|all="day", min_chars=400, max_items=25, include_nsfw=False}`
      - URL biçimi `https://www.reddit.com/r/<sub>/<sort>/.rss?t=<time>`.
      - NSFW, giriş metnindeki `[NSFW]`/`nsfw` etiketinden anlaşılır. RSS puan vermez; minimum puan yalnızca `reddit` (API) adaptöründe vardır.
    - `web`: `{url}`. Önce robots.txt kontrolü; izin yoksa `AdapterError(retryable=False, "robots.txt disallows")`. Metin 200 karakterden kısaysa hata.

- [ ] **Step 1: Failing testler:**
  - `test_rss_adapter_returns_items`
  - `test_reddit_rss_builds_url_and_filters_short_and_nsfw`
  - `test_reddit_rss_strips_signature`
  - `test_reddit_rss_invalid_subreddit_rejected`
  - `test_web_adapter_respects_robots`
  - `test_web_adapter_short_page_error`
  - `test_429_is_retryable_adapter_error`
- [ ] **Step 2:** FAIL. **Step 3:** Uygula. **Step 4:** PASS.
- [ ] **Step 5:** Commit: `feat(sources): adapter interface with rss, reddit rss and web adapters`

### Görev 5: Alım (ingest): tekilleştirme, güncelleme algılama, hak varsayılanı

**Files:**
- Create: `backend/mediafactory/sources/ingest.py`
- Test: `tests/sources/test_ingest.py`

**Interfaces:**
- Consumes: `SourceConnector`, `SourceItem`, `RawItem`, `canonical_url`, `normalize_text`, `content_hash`.
- Produces:
  - `IngestResult(new: int, updated: int, duplicates: int, skipped: int)`
  - `store_items(session, connector: SourceConnector|None, items: list[RawItem], *, source_type: str, rights_status: str|None=None) -> IngestResult`
    - Normalleştirilmiş metin 50 karakterden kısaysa öğe atlanır (`skipped`).
    - Aynı kanonik URL'ye sahip bir öğe var ve hash aynıysa → `duplicates`.
    - Aynı URL, farklı hash → metin güncellenir, `revision += 1`, `processing_status = "updated"`, `meta.updated_at` doldurulur → `updated`.
    - URL yok ama aynı hash varsa → `duplicates` (farklı URL ama aynı içerik için de).
    - Hak durumu sırasıyla: parametre → `connector.default_rights` → `"unknown"`.
    - Yeni öğe için `SourceRightsRecord(from_status=None, to_status=<ilk>, note="ingest")` yazılır.

- [ ] **Step 1: Failing testler:**
  - `test_new_items_stored_with_unknown_rights`
  - `test_same_url_same_text_is_duplicate`
  - `test_reddit_url_variants_deduplicated` (Review Focus 3)
  - `test_same_text_different_url_is_duplicate`
  - `test_changed_text_marks_updated_and_bumps_revision`
  - `test_too_short_skipped`
  - `test_initial_rights_record_written`
- [ ] **Step 2:** FAIL. **Step 3:** Uygula. **Step 4:** PASS.
- [ ] **Step 5:** Commit: `feat(sources): ingest with dedup, update detection and rights default`

### Görev 6: Resmî Reddit API adaptörü ve kimlik bilgisi ayarı

**Files:**
- Create: `backend/mediafactory/sources/adapters/reddit.py`, `api/routes/source_credentials.py`
- Test: `tests/sources/test_reddit_api.py`, `tests/sources/test_credentials_api.py`

**Interfaces:**
- Consumes: `SafeFetcher`, `encrypt`/`decrypt`, `SystemSetting`, `record_audit`, `require_admin`.
- Produces:
  - Kimlik bilgileri `system_settings` içinde `key="credentials.reddit"` olarak, değeri `{"client_id": str, "client_secret_enc": str}` biçiminde tutulur.
  - `get_reddit_credentials(session) -> dict|None`
  - REST (admin):
    - `GET /api/source-credentials` → `{"reddit": {"configured": bool, "client_id": "…"|null}}`. Sır asla dönmez.
    - `PUT /api/source-credentials/reddit {client_id, client_secret}` → audit kaydı (maskelenmiş).
    - `DELETE /api/source-credentials/reddit`
  - `reddit` adaptörü: `{subreddit, sort, time, min_score=0, min_chars=400, max_items=25, include_nsfw=False}`.
    - Uygulama-adına OAuth: `POST https://www.reddit.com/api/v1/access_token` (`grant_type=client_credentials`, Basic auth). Token süresi dolana kadar bellekte önbelleklenir.
    - Liste: `https://oauth.reddit.com/r/<sub>/<sort>?t=&limit=`. `selftext`, `score`, `over_18`, `permalink`, `author`, `created_utc` alanları kullanılır.
    - Kimlik bilgisi yoksa `AdapterError(retryable=False, "Reddit API credentials are not configured (Settings → Source credentials)")`.

- [ ] **Step 1: Failing testler:**
  - `test_not_configured_error`
  - `test_token_then_listing_filters_score_nsfw_length`
  - `test_token_cached_until_expiry`
  - `test_401_not_retryable`
  - `test_credentials_put_get_never_returns_secret`
  - `test_credentials_admin_only`
  - `test_credentials_audited_masked`
- [ ] **Step 2:** FAIL. **Step 3:** Uygula. **Step 4:** PASS.
- [ ] **Step 5:** Commit: `feat(sources): official reddit api adapter and admin credentials`

### Görev 7: Elle içerik ekleme (metin, URL, dosya)

**Files:**
- Create: `backend/mediafactory/sources/manual.py`, `api/routes/items.py` (bu görevde yalnızca manuel uç noktalar)
- Test: `tests/sources/test_manual.py`

**Interfaces:**
- Consumes: `store_items`, `get_adapter("web")`, `extract_article`, `record_audit`, `require_user`.
- Produces:
  - `POST /api/items/manual` iki biçimde çağrılabilir:
    - JSON: `{title?, text?, url?, rights_status, language?, attribution_required?, note?}`. `text` ve `url`'den biri zorunlu. `url` verilmişse `web` adaptörüyle (SSRF ve robots kurallarıyla) çekilir; Reddit gönderi URL'leri gönderinin `.rss`'inden okunur.
    - Multipart: `file` (`.txt`, `.md`, `.pdf`, `.docx`; en fazla 10 MB) + form alanları.
    - Yanıt `201 {item}`. Mükerrerse `200 {item, duplicate: true}`.
  - `extract_file_text(filename: str, data: bytes) -> str`. Desteklenmeyen tür, şifreli PDF, bozuk dosya ya da boyut aşımı → `ManualInputError` → HTTP 422.
  - `source_type="manual"`; hak durumu yükleyenin seçtiği değer olur ve `SourceRightsRecord.actor_id` = yükleyen kullanıcı.

- [ ] **Step 1: Failing testler:**
  - `test_manual_text_created_with_chosen_rights`
  - `test_manual_requires_text_or_url_422`
  - `test_manual_url_uses_safe_fetcher` (özel IP → 422)
  - `test_manual_reddit_post_url_reads_rss`
  - `test_upload_txt_md_docx_pdf` (küçük örnek dosyalar fixtures'ta)
  - `test_encrypted_pdf_422`, `test_corrupt_docx_422`, `test_oversized_upload_422` (Review Focus 5)
  - `test_duplicate_manual_returns_existing`
- [ ] **Step 2:** FAIL. **Step 3:** Uygula. **Step 4:** PASS.
- [ ] **Step 5:** Commit: `feat(sources): manual text, url and file intake`

### Görev 8: Kaynak toplama zamanlayıcısı (worker thread)

**Files:**
- Create: `backend/mediafactory/sources/poller.py`
- Modify: `cli.py` (`mf worker` poller thread'ini de başlatır)
- Test: `tests/sources/test_poller.py`

**Interfaces:**
- Consumes: `SourceConnector`, `get_adapter`, `store_items`, `SafeFetcher`, `decrypt`.
- Produces:
  - `run_source(session, connector, *, fetcher) -> IngestResult`. Başarıda: `last_success_at`, `items_total += new`, `consecutive_failures = 0`, `last_error = None`. Hatada: `last_error` (redact edilmiş), `consecutive_failures += 1`.
  - `schedule_next(connector, *, failed: bool)`: `next_run_at = now + poll_interval_min`. Hata varsa `min(interval × 2^failures, 24 sa)`.
  - `poll_due(factory, *, fetcher, limit=5) -> int`:
    - `enabled AND deleted_at IS NULL AND (next_run_at IS NULL OR next_run_at <= now())` olan kaynakları `FOR UPDATE SKIP LOCKED` ile alır.
    - Önce `next_run_at`'i ileri alıp commit eder; aynı kaynak iki worker'da çalışmaz.
    - Her kaynağı kendi oturumunda çalıştırır. Bir kaynağın istisnası diğerlerini etkilemez.
  - `class SourcePoller(threading.Thread)`: `factory`, `interval_s=30`, `stop_event` alır. Veritabanı yoksa 5 sn bekler.

- [ ] **Step 1: Failing testler:**
  - `test_due_source_runs_and_schedules_next`
  - `test_disabled_and_deleted_sources_skipped`
  - `test_failure_backs_off_exponentially_capped_24h`
  - `test_one_failing_source_does_not_block_others` (Review Focus 4)
  - `test_two_pollers_do_not_run_same_source`
  - `test_reddit_429_sets_last_error_and_retries_later`
- [ ] **Step 2:** FAIL. **Step 3:** Uygula. **Step 4:** PASS.
- [ ] **Step 5:** Commit: `feat(sources): background source poller with backoff`

### Görev 9: Kaynak ve Gelen Kutusu REST API'si

**Files:**
- Create: `backend/mediafactory/api/routes/sources.py`
- Modify: `api/routes/items.py`, `api/app.py`
- Test: `tests/api/test_sources_api.py`, `tests/api/test_items_api.py`

**Interfaces:**
- Consumes: `SourceConnector`, `SourceItem`, `SourceRightsRecord`, `get_adapter(...).validate`, `run_source`, `record_audit`, `require_user`.
- Produces (giriş yapmış kullanıcı; değiştirici isteklerde CSRF):
  - `GET /api/sources` → liste: durum, son çalışma, son hata, toplam öğe, sonraki çalışma. Silinmişler varsayılan olarak gizli (`?include_deleted=true` ile görünür).
  - `POST /api/sources {name, adapter, params, poll_interval_min?, enabled?, default_rights?, default_language?}` → `validate` ile doğrulanır → 201. Ad tekrarlanırsa 409.
  - `PATCH /api/sources/{id}`: kısmi güncelleme. `params` değişirse yeniden doğrulanır.
  - `DELETE /api/sources/{id}` → yumuşak silme, 204.
  - `POST /api/sources/{id}/run` → `run_source` hemen çalışır, `IngestResult` döner. Kaynak devre dışıysa 409.
  - `GET /api/items?status=&rights=&source_id=&q=&limit=&before_id=` → Gelen Kutusu: yeniden eskiye, metin kısaltılmış.
  - `GET /api/items/{id}` → tam metin ve hak geçmişi.
  - `PATCH /api/items/{id} {processing_status?: "rejected"|"archived"|"discovered"}`
  - `POST /api/items/{id}/rights {rights_status, note?, attribution_required?}` → `SourceRightsRecord` + audit.
  - Her yazma işlemi audit'e girer: `source.create/update/delete/run`, `item.rights`, `item.status`.

- [ ] **Step 1: Failing testler:**
  - `test_create_source_validates_params_422`
  - `test_create_list_update_delete_soft`
  - `test_run_now_returns_ingest_result` (respx'li RSS)
  - `test_items_inbox_filters_and_pagination`
  - `test_rights_change_records_history_and_audit`
  - `test_editor_can_manage_sources`
  - `test_unauthenticated_401`
  - `test_delete_keeps_items`
- [ ] **Step 2:** FAIL. **Step 3:** Uygula. **Step 4:** PASS.
- [ ] **Step 5:** Commit: `feat(api): sources and inbox endpoints`

### Görev 10: Belgeler ve uçtan uca doğrulama

**Files:**
- Create: `docs/SOURCE_RIGHTS.md`
- Modify: `README.md` (Kaynaklar bölümü), `docs/DEPLOYMENT.md` (`MF_FETCH_ALLOWLIST`, Reddit API kimlik bilgisi)

`docs/SOURCE_RIGHTS.md` içeriği:
- hak durumları ve anlamları;
- varsayılanın `unknown` olduğu;
- `inspired` / `adaptation` modlarının kuralları;
- Reddit içeriğinin yazarlarına ait olduğu;
- Wattpad'den scraping yapılmadığı;
- web adaptörünün robots.txt ve hız sınırına uyduğu;
- klip ve müzik lisans kaydının (Plan 3) zorunlu olduğu.

- [ ] **Step 1:** Belgeleri yaz.
- [ ] **Step 2: Uçtan uca doğrulama** (Docker, laptop):
  - `install.sh` → API ile bir `reddit_rss` kaynağı ekle (`r/nosleep`, `top`, `week`) → `POST /run` → `GET /api/items` gerçek öğeler döner, hak durumu `unknown`.
  - İkinci `run` → `new=0`, `duplicates>0`.
  - `127.0.0.1` URL'li bir web kaynağı 422 alır.
  - Kurulum sonra kaldırılır.
- [ ] **Step 3:** Tüm paket: `pytest -q` → hepsi PASS. `ruff check` temiz. Commit + push (dal).

---

## Self-review notları
- **Kapsam:** Tasarım §7'nin bütün maddeleri karşılanıyor:
  - adaptörler (Wattpad hariç; Wattpad yalnızca manuel yolla);
  - kaynak yönetimi ve yumuşak silme;
  - alım kuralları: kanonik URL, hash, güncelleme algılama, hız sınırı, geri çekilme, hata kaydı;
  - hak politikası: varsayılan `unknown`, hak geçmişi;
  - SSRF (tasarım §10).
- **Bilerek Plan 3'e bırakılanlar:**
  - Kaynak–konsept ataması ve otomatik iş üretimi.
  - Sınıflandırma ve dil algılama (normalize aşaması).
  - Özgünlük (n-gram) kontrolü.
  - `categories` tablosu.
