# CiciByte AI Media Factory — Tasarım Belgesi

**Tarih:** 14 Kasım 2026
**Durum:** Onaylandı (14 Kasım 2026). Kullanıcı tasarımcının kararlarını onayladı; ikinci tur değişiklikleri (§16a) işlendi.
**Ana kaynak:** `CiciByte_AI_Media_Factory_Project_Spec.md` (ürün şartnamesi). Bu belge, o şartnamenin nasıl inşa edileceğini ve şartnameden bilerek ayrılan noktaları anlatır.
**Referans kod:** `purffle-shorts` v3.1.0, commit `514fd2547227b98d951dfc1489fc8c7ce72f1b68`, MIT lisanslı.

---

## 1. Ne yapıyoruz ve neden

CiciByte AI Media Factory, herkesin **kendi sunucusuna kurabileceği**, ücretsiz ve açık kaynak bir YouTube içerik fabrikası. Kullanıcı:

- kaynaklarını (Reddit, RSS, web sayfaları, kendi dosyaları ve metinleri) panelden ekler, çıkarır, açıp kapatır;
- kendi AI'sını bağlar (yerel Ollama veya llama.cpp, OpenAI uyumlu herhangi bir uç nokta, 9router gibi bir yönlendirici, bulut API'leri);
- birden fazla YouTube kanalı ve her kanal için birden fazla konsept tanımlar;
- toplanan içeriğin özgün senaryoya, sese, altyazıya ve videoya dönüşmesini panelden izler; onayladıklarını YouTube'a yükler.

CiciByte bu ürünü kendi kanalları için DL380 sunucusunda (9router + yerel LLM) kullanacak. Aynı zamanda ürün CiciByte'ın tanıtımını yapacak (§11).

**Neden sıfırdan, neden purffle-shorts değil:** purffle-shorts tek kanal ve `.env` dosyası üzerine kurulu, yalnızca Shorts üretiyor (en fazla 170 sn), yüklemeleri varsayılan olarak herkese açık yapıyor ve stüdyosunda parola isteğe bağlı. Bunları dönüştürmek yeniden yazmaktan pahalı. Ama içindeki sağlam parçaları (§9) uyarlayarak alacağız.

## 2. Hedefler, hedef olmayanlar, anti-hedefler

### Hedefler
- Tek komutla, güvenli varsayılanlarla kendi sunucuna kurulum (Docker Compose).
- Kaynakların panelden tam yönetimi: ekleme, çıkarma, düzenleme, açma/kapama, toplama sıklığı, filtreler, hata durumu.
- AI sağlayıcılarının panelden yönetimi ve **görev bazlı yönlendirme**: senaryo, sınıflandırma, ses (TTS), yazıya dökme (STT) ve görsel için ayrı sıralı sağlayıcı listeleri; sıra sonuna kadar denenir, ardından 3 sn bekleyip yeniden başlanır (§6).
- Çok kanal, çok konsept: kanal başına ayrı OAuth bağlantısı, yayın takvimi, günlük limit.
- Aşamalı, kaldığı yerden devam edebilen üretim hattı (şartname §13 durum makinesi).
- İnsan onayı olmadan dışarıya hiçbir şey yayınlanmaz. Yüklemeler varsayılan olarak `private`.
- Kaynak ve hak kaydı: her öğe için kaynak, tarih, içerik hash'i ve hak durumu.
- Panel Türkçe ve İngilizce.

### Hedef olmayanlar (v1)
- Çok kiracılı SaaS: hesap açma, faturalama, kiracılar arası veri ayrımı.
- AI ile text-to-video üretimi.
- YouTube dışındaki platformlara paylaşım (TikTok, Instagram vb.).
- Ses klonlama.
- Yerleşik telemetri.

### Anti-hedefler (çalışsa bile başarısızlık sayılır)
- Düşük değerli, tekrar eden, seri üretilmiş içerik basan bir "spam makinesi"ne dönüşmek.
- Kullanıcı onayı olmadan herkese açık yayın yapmak.
- Platform kurallarını aşan scraping (Reddit, Wattpad, web).
- Başkasının hikâyesini birebir okuyup kendi içeriğiymiş gibi yayınlamak.
- Kurulumu karmaşık hale getirip yalnızca yazarının çalıştırabileceği bir şey olmak.

## 3. Kısıtlar

- **Lisans:** MIT. purffle-shorts'tan uyarlanan her dosyada orijinal MIT telif satırı korunur; kökeni `NOTICE` dosyasında listelenir.
- **Runtime'da ücretli API zorunlu değil.** Varsayılan yol tamamen yerel çalışabilmeli. Bulut sağlayıcıları isteğe bağlı.
- **Donanım hedefi:** CPU yeterli olmalı (DL380: 16 thread, GPU yok). GPU varsa algılanıp kullanılabilir ama gerekmez.
- **Python 3.12**, Docker Engine + Compose v2.
- **Commit/PR mesajlarında Claude/Anthropic atfı yok** (kullanıcının kalıcı kuralı).

## 4. Yaklaşımlar

| Yaklaşım | Artı | Eksi | Karar |
|---|---|---|---|
| **A. Python tek uygulama:** FastAPI + PostgreSQL + veritabanı tabanlı kuyruk + React paneli | purffle'dan kod alınabilir; medya ekosistemi (faster-whisper, Piper, Kokoro) Python'da; tek dil | Panel için ayrı bir frontend derlemesi gerekir | **Seçildi** |
| B. Next.js/TypeScript + Python medya worker'ları | Panel ve API tek dilde | İki dil, iki bağımlılık ağacı, aradaki köprü; purffle'dan kod almak zorlaşır | Elendi |
| C. purffle-shorts'u fork'layıp dönüştürmek | En hızlı ilk demo | Tek kanal ve `.env` temeli; dönüştürme maliyeti yeniden yazmaktan büyük | Kullanıcı eledi |

**Şartnameden bilinçli sapma:** Şartname kuyruk için Redis öneriyor. İş durumu zaten PostgreSQL'de tutulduğu için kuyruk da orada (`SELECT … FOR UPDATE SKIP LOCKED`). Bu, kurulumdan bir servisi çıkarır ve "gereksiz teknoloji ekleme" kuralına uyar. İleride gerekirse Redis eklenebilir.

## 5. Mimari

```
                 ┌──────────────── Docker Compose ────────────────┐
 Tarayıcı ──▶ api (FastAPI, React panelini de sunar) ──┐            │
                 │                                      ▼            │
                 │                               postgres (veri + kuyruk)
                 │                                      ▲            │
                 └── worker (aşama işleyicileri, zamanlayıcı) ───────┘
                          │        │          │           │
                     AI sağlayıcıları   ffmpeg   yerel TTS/STT   YouTube API
                     (Ollama, OpenAI uyumlu,      (Piper, Kokoro,
                      9router, bulut)              faster-whisper)
```

- **`api`:** REST API, oturum ve yetkilendirme, panelin statik dosyaları, sunucu tarafından olay akışı (canlı log, SSE).
- **`worker`:** Kuyruktan iş alır, aşamaları çalıştırır. Kaynak toplama ve yayın takvimi için zamanlayıcıyı da barındırır. Aynı Python paketi, farklı giriş noktası.
- **`postgres`:** Tüm veri ve kuyruk.
- **Medya depolama:** Yerel disk, `DATA_DIR` altında (`/data/media/<kanal>/<iş>/…`). Model dosyaları `/data/models`, yedekler `/data/backups`.

### Repo yapısı

```
cicibyte-ai-media-factory/
├── backend/mediafactory/        # Python paketi
│   ├── api/                     # FastAPI router'ları
│   ├── core/                    # ayarlar, güvenlik, şifreleme, i18n
│   ├── db/                      # SQLAlchemy modelleri, Alembic göçleri
│   ├── queue/                   # veritabanı kuyruğu, worker, zamanlayıcı
│   ├── sources/                 # kaynak adaptörleri
│   ├── ai/                      # sağlayıcı kayıt defteri + görev yönlendirme
│   ├── pipeline/                # aşamalar: normalize → … → upload
│   ├── media/                   # tts, stt/hizalama, görseller, render, qc
│   └── publish/                 # YouTube
├── frontend/                    # React + TypeScript + Vite, tr/en
├── deploy/                      # docker-compose.yml, Dockerfile'lar, install.sh, update.sh, backup.sh
├── docs/                        # README.tr, DEPLOYMENT, OPERATIONS, SECURITY, SOURCE_RIGHTS
├── tests/
├── LICENSE (MIT) · NOTICE · README.md
```

## 6. AI sağlayıcıları ve görev yönlendirme

Panelde **Sağlayıcılar** sayfası:

- **Sağlayıcı tipleri (v1):**
  - `openai_compatible`: OpenAI uyumlu her uç nokta (Ollama'nın `/v1`'i, llama.cpp, 9router, LM Studio, OpenRouter, Groq, OpenAI…). Taban adres, API anahtarı ve model listesi tutulur.
  - `ollama_native`: model indirme ve listeleme için isteğe bağlı.
  - TTS ve STT sağlayıcıları (§8).
- Her sağlayıcı için "Bağlantıyı test et" düğmesi. Yerel mi uzak mı (`local` / `remote`) etiketi zorunlu.
- **Görev yönlendirme:** `script`, `classify`, `tts`, `stt`, `image` görevlerinin her biri için sıralı bir model listesi. Biri hata verirse sıradaki denenir. Liste bitince **3 sn** beklenir ve baştan, en fazla N tur denenir (N ayarlanabilir, varsayılan 3).
- **CiciByte kurulumu:** tek bir `openai_compatible` sağlayıcı = 9router (`http://ai-router:20128/v1`); görevler `mf-senaryo` ve `mf-siniflandir` combo'larına yönlenir. 9router zaten "önce ücretsiz bulut, en son yerel" sırasını uyguluyor.
- **İstek kuralları:**
  - Yerel ve yavaş modeller için akış (stream) ile okuma. Zaman aşımı sağlayıcı başına ayarlanabilir; varsayılan yerelde 600 sn, uzakta 120 sn.
  - Yapılandırılmış çıktı: önce JSON Schema, desteklenmezse JSON modu, o da yoksa prompt + ayrıştırma. purffle'ın `extract_json` mantığı uyarlanır.
  - Eşzamanlılık sağlayıcı başına sınırlı; yerel LLM'de 1.
- API anahtarları veritabanında şifreli saklanır (§10).

## 7. Kaynaklar, alım ve hak kaydı

### Adaptörler (v1)
| Adaptör | Yöntem | Not |
|---|---|---|
| `reddit` | **Resmî Reddit API** (OAuth "script app" kimliği). Subreddit, sıralama (`top`/`hot`/`new`), zaman aralığı, minimum puan, minimum uzunluk, NSFW filtresi. | Kimlik bilgisi yoksa panelde açıkça "kimlik bilgisi eksik" gösterilir. |
| `reddit_rss` | Herkese açık `.rss` beslemesi, salt-okunur. | Yedek yol: yalnızca başlık ve kısa metin verebilir; uyarıyla işaretlenir. |
| `rss` | RSS/Atom URL'leri | |
| `web` | Tek sayfa çekme | `robots.txt` kontrolü, hız sınırı, kullanıcı ajanı tanımı. |
| `manual` | Metin, URL, `.txt` / `.md` / `.docx` / `.pdf` yükleme | Hak durumu yükleyen tarafından seçilir. |
| `wattpad` | **Yok.** Yalnızca `manual` üzerinden, kullanıcı hak sahibiyse. | Scraping yapılmaz. |
| `media_library` | Kullanıcının kendi video, görsel ve müzik klasörü | Lisans notu zorunlu. |

### Kaynak yönetimi (panel)
- Her kaynak için: ad, adaptör, parametreler, konsept atamaları, toplama sıklığı, açık/kapalı, son çalışma, son hata, toplanan öğe sayısı.
- Ekle / düzenle / sil / şimdi topla / devre dışı bırak.
- Silme: kaynak silinir. Ondan gelen öğeler ve üretilmiş videolar kalır ama kaynağı "silinmiş" olarak işaretlenir. Hak kaydının izi kaybolmaz.

### Alım kuralları
- URL kanonikleştirme. İçerik hash'i (normalize edilmiş metnin SHA-256'sı). Aynı URL veya aynı hash ikinci kez eklenmez. Kaynak güncellenmişse algılanır.
- Kaynak başına hız sınırı, üstel geri çekilme, hata kaydı.
- Her öğe şartnamenin §5 alanlarını taşır. `rights_status` varsayılan olarak `unknown`.

### Hak politikası
- `unknown` veya `restricted` haktaki öğe **otomatik yayın kuyruğuna giremez**. Editoryal onayda kullanıcı hak durumunu değiştirebilir; değişiklik denetim kaydına yazılır.
- **Senaryo modları:**
  - `inspired` (varsayılan): Kaynaktan yalnızca fikir, tema ve atmosfer alınır; LLM özgün bir hikâye yazar. Kaynak metinden uzun pasaj kopyalanmaz.
  - `adaptation`: Kaynağın uyarlanması. Yalnızca hak durumu `user_owned`, `licensed`, `permission_granted` veya `public_domain` ise seçilebilir.
- Özgünlük kontrolü: üretilen senaryo ile kaynak metin arasında n-gram örtüşme oranı. Eşik aşılırsa iş `needs_review` durumuna düşer.
- Kaynak, atıf ve hak bilgisi video kaydıyla birlikte saklanır; `SOURCE_RIGHTS.md` politikayı anlatır.

## 8. Üretim hattı

### Durum makinesi
Şartname §13'teki durumlar aynen kullanılır. Her aşama bir `job_stage_runs` kaydıdır ve şunları tutar:
- başlangıç ve bitiş zamanı,
- girdi ve çıktı dosya referansları,
- log,
- deneme sayısı,
- hata.

Bir aşama başarısız olursa yalnızca o aşama yeniden çalışır. İşler panelden iptal edilebilir ve yeniden denenebilir.

### Aşamalar
1. **normalize:** Temizleme, dil algılama, uzunluk kontrolü.
2. **classify:** `classify` görevi, JSON çıktı. Alanlar şartname §6'daki gibi. Düşük güven veya hassasiyet bayrağı → manuel inceleme.
3. **rights_review:** Hak durumu `unknown` ise kullanıcı onayı beklenir. Konsept ayarıyla `inspired` modunda otomatik geçiş açılabilir; varsayılan kapalı.
4. **script:** `script` görevi.
   - Shorts yapısı: hook (ilk cümle), gelişme, doruk noktası, kapanış ve CTA.
   - Hedef süreye göre kelime hedefi.
   - Başlık, açıklama, etiketler ve thumbnail özeti.
   - **Script Doctor** öz-değerlendirme döngüsü: purffle'dan uyarlanır, dil bağımsız hale getirilir.
   - Her sürüm `script_versions`'a yazılır; kullanıcı düzenleyebilir. Senaryo `draft` olarak başlar, onaysız TTS'e geçmez.
5. **voice:** TTS sağlayıcıları:
   - **Kokoro:** yerel, Apache-2.0, İngilizce için varsayılan.
   - **Piper:** yerel, Türkçe sesleri var; v0.2.
   - **Edge TTS:** uzak; `remote` olarak etiketlenir.
   - **OpenAI uyumlu `/audio/speech`:** uzak veya yerel.

   Çıktı WAV. Ayrıca telaffuz sözlüğü, hız ve duraklama ayarı.
6. **subtitles:** faster-whisper (`small`, int8, CPU) ile kelime düzeyinde hizalama. Çıktı SRT + VTT. Büyük harf dönüşümü **dile duyarlı** (Türkçe "i → İ"). Güvenli alan kontrolü yapılır.
7. **visuals:** Sahne bazında arama sorgusu. Kaynak sırası:
   1. kullanıcının medya kütüphanesi,
   2. isteğe bağlı Pexels/Pixabay (anahtar varsa),
   3. gradyan/doku yedeği.

   Aynı klibin yakın zamanda tekrar kullanılması engellenir.
8. **render:** ffmpeg, argüman listesiyle (kabuk yok).
   - Format: 9:16 (v0.1), 16:9 (v0.2).
   - Kodlayıcı: `libx264`. NVENC veya VAAPI algılanırsa kullanılır, başarısız olursa `libx264`'e düşülür.
   - Konsept başına render preset'i.
   - Müzik yalnızca lisans kaydı olan dosyalardan seçilir.
9. **quality_check:** Şartname §10'daki kontroller: dosya açılıyor mu, süre/çözünürlük, ses seviyesi ve clipping, altyazı taşması, siyah kare, thumbnail, boş metadata, hak durumu, mükerrer içerik, AI içerik beyanı, Made for Kids. Başarısız olan iş `needs_review` durumuna düşer.
10. **approval → scheduled → uploading → published:** §9.

### İş kuyruğu ve kaynak yönetimi
- Aşamalar iş sınıflarına ayrılır: `llm`, `tts`, `stt`, `render`, `io`.
- Her sınıfın eşzamanlılık sınırı ayarlanabilir. Varsayılan: `llm=1`, `render=1`, `tts=1`, `stt=1`, `io=4`.
- `llm` ile `render` aynı anda en fazla 1+1 çalışır (şartname §16).

## 9. YouTube yayıncı

- Resmî YouTube Data API v3 ve OAuth 2.0. Kullanıcı kendi Google Cloud projesini ve OAuth istemcisini oluşturur; `DEPLOYMENT.md` adım adım anlatır.
- **Başsız (headless) sunucu için OAuth akışı:** Panelde "Kanal bağla" düğmesi Google onay sayfasını açar. Geri dönüş adresi panelin kendisidir (`/oauth/callback`). Panele Tailscale veya ters proxy üzerinden erişildiği için çalışır. Alternatif olarak "kodu yapıştır" yöntemi de sunulur.
- Kanal başına ayrı bağlantı. Refresh token **şifreli** saklanır.
- Yükleme: parçalı (resumable), 8 MB chunk, yeniden deneme, kota hatasının algılanması. purffle'ın `youtube.py` yapısı uyarlanır.
- **Görünürlük:**
  - Varsayılan `private`.
  - `public` veya `scheduled` (`publishAt`), kanal ayarında bunun **açıkça etkinleştirilmesini** ve her video için onayı gerektirir.
  - Günlük yükleme sınırı kanal başına; varsayılan 2.
- **Idempotency:**
  - Yüklemeden önce `publishing_jobs` kaydına benzersiz bir anahtar ve `uploading` durumu yazılır.
  - Yeniden denemede önce kanalın son yüklemeleri bu anahtara göre aranır. Anahtar video açıklamasına gizli bir etiket olarak değil, `videos.list` ile başlık ve yükleme zamanı eşleşmesiyle aranır. Böylece çökme sonrası ikinci yükleme önlenir.
- **Diğer alanlar:** thumbnail, playlist, kategori, dil, altyazı dosyası yükleme, `containsSyntheticMedia` beyanı, `selfDeclaredMadeForKids` (kanal kuralından gelir, tahmin edilmez).

## 10. Güvenlik

- **İlk kurulum:** Yönetici hesabı ilk açılışta oluşturulur. Varsayılan parola yoktur; `install.sh` rastgele bir başlangıç parolası üretip yalnızca terminale yazar.
- **Kimlik doğrulama:**
  - Parolalar Argon2id ile saklanır.
  - Oturumlar HttpOnly, SameSite=Strict çerezlerle tutulur.
  - CSRF koruması var.
  - Başarısız girişlerde hız sınırı uygulanır.
- **Roller:** `admin` (her şey) ve `editor` (içerik, onay, üretim; sağlayıcı, kanal bağlantısı ve kullanıcı yönetimi yok).
- **Gizli bilgiler:** API anahtarları ve OAuth token'ları, `.env` içindeki `MF_SECRET_KEY` ile Fernet (AES) üzerinden şifrelenir. Loglara yazılmadan önce maskeleyiciden geçer. `.env` git'e girmez.
- **Ağ:**
  - `api` varsayılan olarak `127.0.0.1:8080`'e bağlanır. Dışarıya açmak için ters proxy (Caddy örneği) veya Tailscale önerilir.
  - Host başlığı kontrolü yapılır.
- **SSRF koruması:** Kaynak URL'lerinde özel ağ adreslerine (127/8, 10/8, 192.168/16, 169.254/16, ::1, fc00::/7) istek yasak. Ayarlarda açık izin listesiyle aşılabilir; bu, yerel AI sağlayıcıları için gerekir.
- **Container:** Container'lar root olmayan kullanıcıyla çalışır. Image sürümleri sabitlenir (`latest` yok).
- **Dış ağ çağrıları:** Güncelleme kontrolü ve font indirme gibi çağrılar ayardan kapatılabilir. Fontlar image'a gömülüdür; render sırasında internetten font indirilmez.

## 11. Marka, bağış ve tanıtım

- **Panel alt bilgisi ve "Hakkında" sayfası:** "Powered by **CiciByte Technology**" → `https://cicibyte.com`, ve "Destek ol / Support" → `https://buymeacoffee.com/mikeross`. Şirket tanıtım metni ve iletişim bilgileri cicibyte.com'daki bilgilerden alınır.
- **README:** "Powered by CiciByte Technology" rozeti ve bağlantısı, Buy Me a Coffee rozeti.
- **Video açıklaması satırı:** "Made with CiciByte AI Media Factory — Powered by CiciByte Technology (cicibyte.com)". Bu bir **ayar**: varsayılan kapalı, CiciByte'ın kendi kanallarında açık.
- **Showroom sitesi:** Ayrı bir proje (§14).
- **Şirket bilgileri** (cicibyte.com'dan, 14 Kasım 2026):
  - Ad: **CiciByte Technology, Inc.**
  - Slogan: "From Idea to Future. Your Corporate Digital Brain."
  - Logo: `https://cicibyte.com/images/cicibyte-logo.png`. Repoya kopyalanır; panel internetten çekmez.
  - Görsel tarz: "Quiet Luxury". Panel ve showroom sade, koyu tonlu ve ölçülü olur.
  - Instagram: `@cicibyte.corporation`.
- **LICENSE telif satırı:** `Copyright (c) 2026 CiciByte Technology, Inc.`, ayrıca purffle-shorts'un MIT satırı `NOTICE` dosyasında.
- Ürün, cicibyte.com'daki **Cicibyte Hub → AI & Data** listesine eklenmeye aday. Bu, kullanıcının kendi sitesinde yapacağı bir iş.

## 12. Veri modeli

Şartname §14'teki tablolar kullanılır:
- `users`, `channels`, `channel_oauth_connections`, `concept_profiles`, `source_connectors`, `source_items`, `source_rights_records`, `categories`
- `content_ideas`, `scripts`, `script_versions`
- `production_jobs`, `job_stage_runs`
- `media_assets`, `subtitles`, `rendered_videos`, `thumbnails`
- `publishing_jobs`, `published_videos`, `analytics_snapshots`
- `prompt_templates`, `audit_logs`, `system_settings`

Bunlara iki tablo eklenir:
- **`ai_providers`:** tip, taban adres, şifreli anahtar, `local` / `remote` etiketi, zaman aşımı, eşzamanlılık.
- **`ai_task_routes`:** görev → sıralı sağlayıcı/model listesi, tur sayısı, bekleme süresi.

Kuyruk `production_jobs` ve `job_stage_runs` üzerinden çalışır. Göçler Alembic ile yapılır, ilişkiler yabancı anahtarlarla tanımlanır.

## 13. Sürüm planı

### v0.1: "İlk gerçek video"
**Hedef:** Reddit'ten alınan bir korku hikâyesinden, `inspired` modunda **İngilizce Shorts** üretmek ve tek bir kanala **private** yüklemek.

Kapsam:
- Kurulum: Docker Compose, `install.sh`, yönetici hesabı, sağlık kontrolleri, yedekleme script'i.
- Sağlayıcılar: `openai_compatible` + görev yönlendirme. CiciByte'ta 9router ile çalışır.
- Kaynaklar: `reddit` (resmî API) + `reddit_rss` yedeği + `rss` + `manual`. Panelden tam yönetim.
- Hat: normalize → classify → rights_review → script (+ Script Doctor) → voice (Kokoro EN, Piper TR) → subtitles (faster-whisper, dile duyarlı) → visuals (`background_loop`: oyun arka planı kütüphanesi, §16a) → render 9:16 → thumbnail → quality_check → onay → private upload.
- Kaynak: `reddit_rss` ana yol; resmî `reddit` adaptörü kimlik bilgisi Ayarlar'dan eklenince çalışır.
- Panel sayfaları: Genel Bakış, Kanallar, Konseptler, Kaynaklar, Gelen Kutusu, Editoryal Kuyruk, Üretim Kuyruğu (canlı log), Video Kütüphanesi, Sağlayıcılar, Ayarlar, Denetim Kaydı. Türkçe ve İngilizce.
- Veri modeli **baştan çok kanallı.** v0.1 testinde 2 kanal ve 3 konsept oluşturulabildiği doğrulanır (şartname §19).

**v0.1'e eklenenler (§16a):** Hazır Video Kataloğu ve otomatik üretim (varsayılan açık), Coverr API ve Mixkit tek dosya içe aktarma, çok dilli üretim (EN + TR; Piper Türkçe ses ve dile duyarlı altyazı).

### v0.2: Uzun video
- 16:9 uzun video yapısı (bölümler; LLM bağlam sınırı için parçalı üretim).
- `web` adaptörü, kaynak doğrulama notları.

### v0.3: Takvim ve analitik
- Yayın takvimi sayfası, `publishAt`, kanal bazlı limitler.
- YouTube Analytics anlık görüntüleri, konsept bazlı raporlar.
- Benzerlik ve özgünlük denetiminin güçlendirilmesi.

### Dağıtım
- CiciByte kurulumu: DL380'de yeni bir LXC `medya` container'ı (Docker; `vmbr0` + `vmbr1`).
- Panele Tailscale üzerinden erişilir.

## 14. Ayrı projeler (bu belgenin kapsamı dışında)

- **Showroom ve indirme sitesi:**
  - `cicibytetechnology` sunucusunda (aaPanel/nginx) bir `cicibyte.com` subdomain'i olacak; ad sonra seçilecek.
  - İçerik: ürün tanıtımı, ekran görüntüleri, GitHub'dan indirme ve kurulum talimatı, CiciByte tanıtımı, Buy Me a Coffee.
  - DNS kaydı Cloudflare'de kullanıcı tarafından eklenir.
  - Kendi tasarım belgesiyle, v0.1 ekran görüntüleri hazır olduğunda yapılacak.
- **Git reposu:** `RealMrNovember/cicibyte-ai-media-factory`, herkese açık. Bu tasarım onaylanınca oluşturulur; belge ve kod oraya taşınır.

## 15. Test stratejisi

- **pytest:**
  - Sahte LLM, sahte TTS ve sessiz ses ile çevrimdışı uçtan uca hat testi (purffle'ın `test_e2e` yaklaşımı).
  - Adaptör testleri kayıtlı HTTP yanıtlarıyla.
  - Kuyruk ve durum makinesi testleri: yeniden deneme, kaldığı yerden devam, iptal.
- **Güvenlik testleri:** kimlik doğrulama, CSRF, roller, SSRF engeli, gizli bilgilerin maskelenmesi.
- **YouTube:** İstemci sahte bir sunucuya karşı test edilir. Gerçek private yükleme, v0.1 kabulünde CiciByte test kanalıyla elle yapılır.
- **Panel:** Bileşen testleri (Vitest) ve kritik akışlar için Playwright duman testi.
- **Kabul:** Şartname §19'daki maddeler, v0.1 kapsamına girenler.

## 16. purffle-shorts'tan uyarlanacak parçalar

| Parça | Kaynak dosya | Değişiklik |
|---|---|---|
| OpenAI uyumlu istemci, JSON çıkarma, yedeğe geçme | `llm.py` | Görev yönlendirme, akış, sağlayıcı başına zaman aşımı |
| Senaryo şeması ve Script Doctor | `script.py` | Dil bağımsız lint, `inspired` / `adaptation` modları, uzun video için genişletme |
| Kelime zamanlama, sessizlik algılama | `timing.py`, `tts.py` | VTT, dile duyarlı büyük harf |
| Altyazı ve overlay çizimi | `overlays.py` | Gömülü fontlar, internetten indirme yok |
| ffmpeg render, kodlayıcı yedeği | `render.py`, `ffmpeg.py` | NVENC/VAAPI algılama, preset'ler |
| Stok medya ve tekrar engeli | `media.py` | Kütüphane öncelikli |
| YouTube parçalı yükleme | `youtube.py` | Şifreli token, kanal başına bağlantı, idempotency, varsayılan private |
| Sentezlenmiş efekt sesleri | `sfx.py` | Değişmeden |

## 16a. Kullanıcı kararları (builder kontrolünden sonra, 14 Kasım 2026)

- **İşlerin başlaması: "Hazır Video Kataloğu" modeli** (kullanıcı kararı, 14 Kasım 2026, ikinci tur):
  - Konsept başına **otomatik üretim varsayılan AÇIK.**
  - Worker, sınıflandırmayı geçen ve konseptin filtrelerine uyan öğeleri kendisi seçip üretime alır.
  - Hedef: konsept başına `ready_buffer` adet (varsayılan 10) **yayına hazır video** stokta tutmak.
  - Stok dolunca üretim durur; video yayınlandıkça ya da reddedildikçe yeniden başlar.
  - Günlük üretim sınırı (varsayılan 6) CPU bütçesini korur.
  - Gelen Kutusu'ndan elle "Üret" demek her zaman mümkündür.
- **Katalog:** Video Kütüphanesi'nde "Hazır" sekmesi, katalog gibi kartlarla gösterilir: önizleme, thumbnail, başlık, dil, süre, kaynak, hak notu. Kullanıcı karttan **"Yayına al"** der.
  - Bu tıklama **son insan onayıdır** (`approved`); ardından takvime ya da private yüklemeye gider.
  - "Reddet" ya da "Yeniden üret" de seçilebilir.
- **Hak kapısı:**
  - `inspired` modunda üretilen içerik özgün kabul edildiği için, `unknown` haktaki öğeler için `rights_review` bu modda **otomatik geçer** (konsept ayarı, varsayılan açık). Kaynak ve hak notu video kaydında görünür.
  - `adaptation` modunda hak kapısı her zaman insan onayı ister.
  - Hiçbir video katalogdan insan seçmeden yayınlanmaz. Şartnamedeki "hak durumu belirsiz kaynak otomatik yayına girmez" kuralı böylece korunur: üretim otomatik, yayın değil.
- **Senaryo onayı:** Konsept ayarıdır, varsayılan **kapalı** (katalog modeliyle uyumlu). Script Doctor'ı geçen senaryo doğrudan TTS'e gider. Kullanıcı istediği konseptte açabilir.
- **Çok dilli üretim:**
  - Konseptte birden fazla dil seçilebilir (`languages: ["en","tr"]`).
  - Seçilen her dil için aynı kaynak öğeden **ayrı bir video** üretilir. Senaryo her dilde ayrı yazılır (çeviri değil, o dilin doğal anlatımı), ses, altyazı, render ve thumbnail da dil başına ayrıdır.
  - Arka plan klibi ve görsel düzen aynı kalabilir.
  - Videolar bir `content_group` altında bağlanır; katalogda birlikte gösterilir.
  - Her dil videosu kendi kanalına ya da aynı kanala yüklenebilir. Hangi dilin hangi kanala gideceği konseptte tanımlanır.
  - Bunun için **Türkçe (Piper TTS + dile duyarlı altyazı) v0.1'e alınır.** v0.2'deki "Türkçe" maddesi uzun video ile sınırlanır.
- **Görseller — oyun arka planı (Minecraft parkur tarzı):**
  - v0.1'in ana görsel modu `background_loop`. Konsepte atanan bir **arka plan klip kütüphanesinden** rastgele bir klip ve rastgele bir başlangıç noktası seçilir, 9:16'ya kırpılır, video boyunca sürer. Üzerine altyazı, isteğe bağlı başlık kartı ve ses gelir.
  - Klip kütüphanesi panelden yönetilir: yükleme, klasör tarama, etiket, **lisans/köken notu zorunlu**, kullanım sayacı, art arda aynı klibin seçilmemesi.
  - **Klip kaynakları:**
    - **Coverr API** (resmî API, ücretsiz kullanım lisansı): Ayarlar'dan API anahtarı girilir. Panelde arama → önizleme → "Kütüphaneye ekle" akışı. İndirilen klibin kaynak URL'si ve lisansı otomatik kaydedilir. Rate limit'e (demo anahtarda 50 istek/saat) uyulur.
    - **Mixkit** (ücretsiz Mixkit lisansı): Resmî API yok, bu yüzden **toplu otomatik indirme yapılmaz**. Kullanıcı klibi indirip panele yükler veya Mixkit sayfa URL'sini girer; uygulama yalnızca o tek dosyayı indirip kaynağı "Mixkit Free License" olarak işaretler.
    - Kullanıcının kendi kayıtları (örneğin Minecraft gameplay).
  - **Hak notu (`SOURCE_RIGHTS.md`'ye girer):** Minecraft gameplay videoları Mojang'ın kullanım kurallarına göre genel olarak serbesttir. Ancak başkasının kaydettiği hazır "parkur" kliplerinin hakkı onu kaydedene aittir. Bu yüzden ya kendi kaydımız, ya da açıkça yeniden kullanıma izin veren paketler kullanılır; köken her klip için kayda geçer. Videoya değer katan şey özgün anlatım ve sestir; arka plan yalnızca dekordur.
  - Sahne bazlı stok görseller (`scene_stock`: medya kütüphanesi ve isteğe bağlı Pexels) v0.2'ye ertelenir.
- **Reddit:**
  - v0.1'de `reddit_rss` ana yoldur. Gönderinin RSS girdisindeki gövde metni kullanılır, `inspired` modu için yeterlidir.
  - Resmî API adaptörü (`reddit`) yazılır ama kimlik bilgileri **Ayarlar → Kaynak kimlik bilgileri**'nden sonradan eklenir. Kimlik yoksa adaptör "yapılandırılmamış" olarak görünür.
- **YouTube bağlantısı:** Kod v0.1'de hazır olur (kanal bağlama, yeniden bağlanma, private yükleme). Gerçek bağlantıyı kullanıcı, proje tamamlandıktan sonra Ayarlar'dan yapar. v0.1 kabulü iki adımlıdır:
  1. Yerel olarak "onaylandı, yüklenmeye hazır" durumuna kadar giden bir video.
  2. Bağlantı kurulunca tek bir private yükleme.

## 16b. Tasarımcının kararları (builder kontrolünden)

- **Konsept–kanal ilişkisi:** Her konsept tek bir kanala aittir (`concept_profiles.channel_id`). "Ortak konsept motoru", aynı üretim kodunun kullanılması demektir. Bir konsept başka bir kanala **kopyalanabilir** (şablon olarak). Bir kaynak öğe birden fazla konsepte bağlıysa her konsept için ayrı bir iş ve video oluşur. Mükerrer içerik ve benzerlik kontrolleri **kanal bazında** yapılır: aynı kaynaktan iki farklı kanala video çıkabilir, aynı kanala ikinci kez çıkamaz.
- **Thumbnail:** v0.1'de ayrı bir `thumbnail` aşaması (render ile quality_check arasında) olur. Render edilen videodan en iyi kare seçilir (keskinlik + parlaklık skoru), üzerine Pillow ile başlık metni ve konseptin `thumbnail_template` düzeni çizilir. AI ile görsel üretimi (`image` görevi ve görsel sağlayıcı tipi) v0.3'e ertelenir. v0.1'de `image` görev rotası tanımlı değildir.
- **Google OAuth token ömrü:** Doğrulanmamış (Testing modundaki) Google projelerinde refresh token 7 günde düşer. Bu yüzden v0.1 şunları içerir:
  - kanal bağlantı durumu göstergesi,
  - token geçersizleşince panelde uyarı ve "Yeniden bağlan" akışı,
  - yükleme işinin `needs_review` yerine `retry_wait` durumuna geçip yeniden bağlantıyı beklemesi.

  `DEPLOYMENT.md`, doğrulanmamış projelerde yüklemelerin YouTube tarafından private'a kilitlendiğini ve public/zamanlanmış yayının (v0.3) Google API denetimi gerektirebileceğini açıkça yazar.

## 17. Kurucuya (builder'a) bırakılanlar

- Kütüphane sürümleri, ORM ayrıntıları, frontend bileşen kütüphanesi seçimi.
- Kuyruk worker'ının iç yapısı ve kilitleme ayrıntıları.
- API uç noktalarının tam listesi ve şemaları.
- Panelin görsel tasarımı. Tek kural: sade ve mobil uyumlu; durumlar anlaşılır aşamalarla gösterilir.
- Medya klasörlerinin tam düzeni ve saklama süresi varsayılanları.
