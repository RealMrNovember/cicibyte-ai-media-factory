# CiciByte AI Media Factory

## Tek Repo Üzerinden Geliştirme, DL380 Kurulumu ve İşletim Şartnamesi

**Belge türü:** Claude Code / Claude IDE için ana proje talimatı\
**Hedef ortam:** HP ProLiant DL380, 93 GB RAM\
**Repo başlangıcı:** https://github.com/Chamanrajragu/purffle-shorts\
**Ürün hedefi:** Tek uygulama içinde çok kaynaklı içerik toplama,
sınıflandırma, AI destekli özgün senaryo üretimi, seslendirme, altyazı,
video render ve çoklu YouTube kanalına kontrollü yayınlama.

------------------------------------------------------------------------

# 1. Claude için ana görev

Bu depoyu HP DL380 sunucusunda çalışacak, tek bir ürün gibi yönetilen
**CiciByte AI Media Factory** uygulamasına dönüştür.

Başlangıç reposunu incele, mevcut işlevlerini koru ve yeniden kullan.
Gerekli modülleri ekle. Projeyi gereksiz yere sıfırdan yazma; ancak
başlangıç reposunun mimarisi ihtiyaçları karşılamıyorsa kontrollü
refactor yap.

**Önemli:** Bu belge bir ürün şartnamesidir. Önce mevcut repo ve
sunucuyu incele; sonra uygulanabilir bir plan çıkar. Donanımı ve mevcut
işletim sistemini doğrulamadan kurulum komutlarını çalıştırma. Yıkıcı
işlem, disk biçimlendirme, bölüm değiştirme, mevcut servisi durdurma,
güvenlik duvarını değiştirme, SSH ayarlarını değiştirme veya sistemi
yeniden başlatma öncesinde açık onay iste.

Üretim zamanında Claude API veya başka ücretli LLM API'si zorunlu
olmasın. Ana AI sağlayıcısı DL380 üzerinde çalışan **Ollama** olsun.
Claude yalnızca geliştirme/kurulum asistanı olarak kullanılabilir;
uygulamanın runtime bağımlılığı olmamalıdır.

# 2. Başlangıç reposu ve ilk işlem

Repo:

`https://github.com/Chamanrajragu/purffle-shorts`

Klonlama:

``` bash
git clone https://github.com/Chamanrajragu/purffle-shorts.git
cd purffle-shorts
```

Claude'un ilk görevleri:

1.  Repo README, LICENSE, bağımlılıklar, Docker dosyaları, testler, API,
    MCP ve yayınlama kodunu incele.
2.  Çalışılan commit hash'ini ve lisansı kaydet.
3.  Mevcut video üretim akışını değiştirmeden bir demo render al.
4.  `git status` ve mevcut dosyaları kontrol et; kullanıcı
    değişikliklerini ezme.
5.  Mevcut kodda güvenlik veya lisans riski varsa raporla.
6.  Aşağıdaki gereksinimlerle gap analysis hazırla.
7.  Ardından aşamalı uygulamaya geç.

Başlangıç reposunun Reddit, RSS, web sayfası, fikir kuyruğu, Ollama,
TTS, altyazı, FFmpeg, Studio, REST API, MCP ve YouTube yayınlama
kabiliyetlerini doğrula. README'de yazan bir özelliği kodda ve testte
doğrulamadan tamamlanmış kabul etme.

# 3. Ürün hedefi ve temel prensipler

Uygulama tek bir web panelinden yönetilecek. Kullanıcı birden fazla
YouTube kanalı ve her kanal için birden fazla içerik konsepti
tanımlayabilecek.

Örnek konseptler: - Korku ve gizem hikâyeleri - Tarih ve mini belgesel -
Bilim ve teknoloji - Özgün kurgu ve sesli hikâye - Eğitici kısa
videolar - Kullanıcının kendi podcast/video kayıtlarından Shorts

Her konseptin kendi dili, kaynakları, prompt profili, anlatıcı sesi,
görsel stili, video oranı, hedef süresi, yayın takvimi ve kalite
kuralları olacak.

**Tek uygulama, tek veritabanı, ortak üretim motoru; kanal ve konsept
bazında ayrılmış konfigürasyon ve veri.**

Temel prensipler: - Local-first ve mümkün olduğunca sıfır abonelik
maliyeti. - CPU üzerinde çalışabilir; GPU varsa otomatik kullan. -
Kaynak toplama, senaryo, TTS, altyazı, render ve upload birbirinden
bağımsız tekrar çalıştırılabilir aşamalar olsun. - Her içerik için
kaynak URL, kaynak türü, alınma zamanı, lisans/izin notu ve içerik
hash'i kaydedilsin. - Aynı kaynak veya aynı senaryo tekrar işlenmesin. -
Otomatik yayın varsayılan olarak kapalı başlasın. İlk sürümde YouTube'a
**private** yükle ve panelden onayla. Kullanıcı açıkça etkinleştirirse
planlı yayın moduna geç. - Hatalar kayıt altına alınsın; başarısız iş
kaldığı aşamadan yeniden başlatılabilsin. - Kullanıcı onayı olmadan
dışarıya içerik yayımlama. - Şifre, OAuth token, API anahtarı veya SSH
private key loglara yazılmasın.

# 4. Hedef mimari

Tek repo içinde modüler monolith mimarisi kullan. İlk sürümde
mikroservis karmaşıklığı oluşturma. Worker süreçleri ayrı container
olabilir ancak aynı repo ve aynı ürünün parçaları olmalı.

Önerilen bileşenler:

-   **Web UI:** Mevcut Purffle Studio'yu değerlendir; yeterli değilse
    Next.js veya mevcut stack ile tek yönetim paneli geliştir.
-   **Backend API:** Mevcut REST API'yi genişlet; gerekiyorsa FastAPI.
-   **Database:** PostgreSQL tercih et. Mevcut repo SQLite kullanıyorsa
    önce geçiş planı ve migration hazırla; veri kaybı yaratma.
-   **Queue:** Redis + RQ/Celery/benzeri bir worker kuyruğu. Mevcut repo
    mekanizması yeterliyse koru.
-   **Local LLM:** Ollama.
-   **TTS:** Öncelik tamamen yerel Kokoro veya Piper; lisans ve
    Türkçe/istenen dil ses kalitesini doğrula. Edge TTS gibi ağ tabanlı
    seçenekler opsiyonel sağlayıcı olabilir, offline olduğu iddia
    edilmemeli.
-   **Speech-to-text/alignment:** faster-whisper veya mevcut yerel
    hizalama yöntemi.
-   **Video:** FFmpeg. GPU encoder varsa NVENC/VAAPI gibi donanım
    hızlandırmayı algıla; yoksa libx264.
-   **Scheduling:** Veritabanı tabanlı zamanlayıcı/queue.
-   **Publishing:** Resmî YouTube Data API v3 ve OAuth 2.0.
-   **Observability:** Uygulama logları, worker durumu, disk kullanımı,
    CPU/RAM, render süresi ve hata ekranı.

n8n zorunlu bir bağımlılık olmasın. Kullanıcı isterse webhook/API
üzerinden sonradan entegre edilebilir. Temel iş akışı uygulamanın kendi
içinde çalışmalı.

# 5. Kaynak toplama sistemi (Source Manager)

Kaynaklar adapter mimarisiyle eklenmeli. Her adapter aynı standart veri
formatını üretmeli.

İlk sürüm kaynakları:

1.  **Reddit:** Resmî Reddit API veya izinli erişim yöntemleri.
    Subreddit, arama sorgusu, zaman aralığı ve minimum puan gibi
    filtreler.
2.  **RSS/Atom:** Kullanıcının eklediği feed URL'leri.
3.  **Web sayfası:** Kamuya açık ve erişimine izin verilen sayfalar;
    robots.txt, site koşulları, rate limit ve telif kuralları
    gözetilsin.
4.  **Kullanıcı girdisi:** Metin, URL, Markdown, TXT, DOCX/PDF gibi
    kullanıcı tarafından sağlanan içerik.
5.  **Wattpad:** Resmî ve izinli erişim yoksa scraping veya erişim
    engelini aşma yapma. Kullanıcının sahip olduğu veya kullanım izni
    bulunan hikâyeleri dosya/metin olarak içe aktarma seçeneği sun.
    İleride yalnızca platform kurallarına ve hak sahibinin iznine uygun
    bir adapter ekle.
6.  **Kendi medya arşivi:** Kullanıcının lisanslı video, görsel, müzik
    ve ses dosyaları.

Her kaynak kaydında: - source_id - source_type - canonical_url - title -
author/publisher (varsa) - published_at - fetched_at - raw_text /
normalized_text - language - content_hash - rights_status: `unknown`,
`user_owned`, `licensed`, `permission_granted`, `public_domain`,
`restricted` - attribution_required - processing_status - error_message

Kaynaklar varsayılan olarak `unknown` hak durumunda olsun. Hak durumu
belirsiz kaynaklar otomatik ticari yayın kuyruğuna girmesin. Reddit
içeriği veya başka bir kullanıcının hikâyesi otomatik olarak serbest
ticari kullanım kabul edilmemeli.

Toplayıcı özellikleri: - Per-source polling interval. - Rate limit ve
backoff. - URL canonicalization. - Duplicate detection. - İçerik hash
kontrolü. - Kaynağın güncellendiğini algılama. - Hata ve yeniden
deneme. - Kaynak bazında etkin/pasif anahtarı.

# 6. Kategorilendirme ve editoryal kontrol

Toplanan her öğe önce normalize edilsin, ardından Ollama ile
kategorilendirilsin.

Kategori örnekleri: - Story / Fiction - Horror / Mystery - History -
Science / Technology - Education - News / Current Affairs -
Entertainment - Podcast / Interview - User Original

AI sınıflandırma alanları: - primary_category - secondary_categories -
language - topic - short_summary - suggested_format -
estimated_duration - sensitivity_flags - factuality_risk -
copyright_risk - source_quality - confidence_score

Kullanıcı panelden kategorileri ve kuralları değiştirebilsin. Düşük
güven puanlı veya hassas içerikler manuel incelemeye düşsün.

Haber ve gerçek bilgi içeren videolarda: - Kaynak doğrulama ve mümkünse
birden fazla güvenilir kaynak kontrolü. - Tarih ve bağlam kontrolü. -
AI'nın doğrulanmamış iddiayı kesin bilgi gibi yazmaması. - Kaynak
listesi ve araştırma notlarının video kaydıyla saklanması.

# 7. Konsept ve kanal profilleri

Kanal ve konsept birbirinden ayrılmalı.

**Channel** alanları: - channel_id - channel_name - youtube_channel_id -
oauth_connection_id - default_language - timezone - default_visibility -
upload_schedule - daily_upload_limit - monetization_notes - active

**Concept/Profile** alanları: - profile_id - channel_id - name -
description - allowed_categories - source_filters - system_prompt -
writing_style - target_audience - language - voice_id - video_format:
`short`, `long`, `both` - aspect_ratio: `9:16`, `16:9`, `1:1` -
target_duration - visual_style - subtitle_style -
background_music_policy - thumbnail_template - publishing_rules -
originality_rules - active

Birden fazla kanal aynı konsept motorunu kullanabilsin; fakat OAuth
bağlantıları, yayın takvimleri ve istatistikleri ayrı tutulsun.

# 8. AI senaryo üretimi

Ollama ana LLM sağlayıcısı olacak. Model adı `.env` veya admin ayarından
değiştirilebilir olsun.

Claude şu sırayla uygulamalı: 1. Sunucu CPU, RAM, GPU/VRAM ve diskini
algıla. 2. Ollama kurulu mu kontrol et. 3. Donanıma uygun model öner. 4.
Kullanıcıya model boyutu, yaklaşık RAM kullanımı ve hız/kalite
ödünleşimini açıkla. 5. Onay sonrası modeli indir. 6. Basit Türkçe ve
İngilizce test prompt'ları çalıştır. 7. Model endpoint ve health check'i
doğrula.

Modeli donanım görülmeden sabitleme. GPU yoksa quantized küçük/orta
modellerle başla. 93 GB RAM'in tamamını modele ayırma; OS, veritabanı,
worker ve video render için pay bırak. Aynı anda çok sayıda LLM isteği
başlatma.

Senaryo motoru: - Kaynağı kopyalamak yerine özgün anlatım üretmeli. -
Kaynak metnin telifli/korumalı olabileceği durumda uzun pasajları aynen
kullanmamalı. - Kullanıcıya ait veya lisanslı kaynaklarda dahi
dönüştürücü katkı, yorum, yapı ve özgün anlatı eklemeli. - Hook, giriş,
ana bölümler, kapanış ve CTA üretmeli. - Video süresine göre kelime
hedefi hesaplamalı. - Shorts ve long-form için ayrı yapı kullanmalı. -
Başlık, açıklama, etiket önerileri ve thumbnail brief'i üretmeli. -
Gerçek bilgi içeren içerikte kaynakça/atıf metadatasını saklamalı. -
Script versiyonları ve kullanıcı düzenlemeleri kaydedilmeli.

Her senaryo `draft` olarak başlasın. Kalite kontrol geçmeden TTS'ye
gitmesin.

# 9. Ses, altyazı ve video üretimi

## Ses

-   Yerel TTS motoru.
-   Kanal/konsept bazında ses profili.
-   Türkçe ve İngilizce ses testi.
-   Telaffuz sözlüğü ve özel kelime düzeltmeleri.
-   Konuşma hızı, ton ve duraklama ayarı.
-   TTS çıktısı WAV olarak saklanmalı; final miks için uygun formata
    dönüştürülmeli.
-   Kullanıcının izni olmadan gerçek kişilerin sesini klonlama.

## Altyazı

-   Sesle senkronize altyazı.
-   SRT ve VTT çıktısı.
-   İsteğe bağlı kelime kelime animasyon.
-   Türkçe karakter ve Unicode font desteği.
-   Güvenli alan (safe area) kontrolü.
-   Kullanıcı tarafından düzenlenebilir altyazı metni.

## Görsel/video

-   İlk sürümde CPU uyumlu FFmpeg pipeline.
-   Kullanıcının kendi medya kütüphanesi.
-   Lisansı doğrulanmış stok medya adapter'ları.
-   Görsel arama sorgusu sahne bazında üretilecek.
-   Aynı stok kliplerin sürekli tekrar kullanılmasını engelle.
-   Basit pan/zoom, crop, geçiş, altyazı, intro/outro, logo ve ses
    miksleme.
-   9:16 Shorts ve 16:9 uzun video.
-   1080p hedef; donanım yetmiyorsa ayarlanabilir kalite.
-   Render preset'leri kanal/konsept bazında.
-   AI text-to-video üretimi ilk sürümde zorunlu değil; GPU ve lisans
    değerlendirmesi sonrası opsiyonel modül.

Müzik ve efekt: - Yalnızca kullanım hakkı doğrulanmış müzik/efekt. -
YouTube Audio Library veya kullanıcının lisanslı dosyaları. - Lisans
bilgisi ve kaynak dosyası kaydı. - Telif belirsiz müziği otomatik
kullanma.

# 10. Video kalite kontrolü

YouTube'a yüklemeden önce otomatik kontroller:

-   Video dosyası açılıyor mu?
-   Süre ve çözünürlük doğru mu?
-   Ses var mı, clipping veya aşırı düşük ses var mı?
-   Altyazı zamanları video süresini aşıyor mu?
-   Siyah/boş kare veya eksik medya var mı?
-   Thumbnail üretildi mi?
-   Başlık/açıklama boş mu?
-   Kaynak ve hak durumu yayın için uygun mu?
-   İçerik daha önce yayınlandı mı?
-   Aynı kanalda yakın zamanda çok benzer içerik üretildi mi?
-   AI/synthetic content disclosure gerekliliği değerlendirildi mi?
-   Made for Kids ayarı doğru belirlenmiş mi?

Başarısız kontrol `needs_review` durumuna düşürsün. Kontrolü geçemeyen
içerik otomatik yayınlanmasın.

# 11. YouTube Publisher

Yalnızca resmî YouTube Data API v3 ve Google OAuth 2.0 kullan.

Özellikler: - Birden fazla YouTube kanalına ayrı OAuth bağlantısı. -
Kanalı bağlama, bağlantı durumunu gösterme ve güvenli token yenileme. -
Video dosyası yükleme. - Başlık, açıklama, etiket, kategori, dil ve
thumbnail. - Playlist seçimi. - Public/private/unlisted görünürlük. -
Uygun olduğunda `publishAt` ile zamanlama. - YouTube altyazı dosyası
yükleme opsiyonu. - Synthetic/altered content açıklama alanı. - Made for
Kids alanı; otomatik tahmin yerine kullanıcı/kanal kuralı ve inceleme. -
Upload progress. - Quota ve API hata yönetimi. - Idempotency: aynı video
iki kez yüklenmesin. - Retry sırasında önce mevcut upload kaydını
kontrol et. - Upload sonucu, video ID ve URL veritabanına yazılsın.

**Güvenli başlangıç politikası:** - İlk kurulumda tüm yüklemeler
`private`. - Kullanıcı panelden videoyu izleyip onaylasın. - Google API
projesinin doğrulama/audit ve kota kısıtları araştırılsın. - Public
otomatik yayın ancak OAuth, API izinleri, test ve kullanıcı onayından
sonra etkinleştirilsin. - Günlük yayın sayısı kullanıcı tarafından
belirlenebilsin; agresif seri yükleme varsayılan olmasın.

# 12. Dashboard sayfaları

Tek panelde şu sayfalar olsun:

1.  **Overview:** Bugünkü işler, bekleyen onaylar, render kuyruğu,
    yayınlanan videolar, hata ve sunucu durumu.
2.  **Channels:** YouTube kanalları, OAuth bağlantısı, dil, saat dilimi,
    yayın ayarları.
3.  **Concepts:** Konsept profilleri, prompt'lar, ses ve görsel
    şablonları.
4.  **Sources:** Reddit/RSS/web/kullanıcı kaynakları, filtreler, toplama
    sıklığı.
5.  **Inbox:** Yeni toplanan içerikler ve kategori sonuçları.
6.  **Editorial Queue:** Senaryo taslakları, AI değerlendirmesi,
    düzenleme ve onay.
7.  **Production Queue:** TTS, altyazı, görsel, render aşamaları ve
    canlı log.
8.  **Video Library:** Önizleme, dosyalar, SRT, thumbnail, kaynaklar,
    versiyonlar.
9.  **Publishing Calendar:** Kanal bazlı yayın takvimi.
10. **Analytics:** YouTube'dan erişilebilen izlenme, gösterim, CTR,
    izlenme süresi ve video performans bilgileri.
11. **Settings:** Ollama, TTS, kaynak adapter'ları, storage, OAuth,
    güvenlik.
12. **Audit Log:** Kim hangi içeriği ne zaman onayladı, değiştirdi veya
    yayınladı.

Panel mobil uyumlu olsun. Üretim durumları anlaşılır aşamalarla
gösterilsin.

# 13. İş akışı ve durum makinesi

Her içerik için aşağıdaki durumlar kullanılmalı:

`discovered` → `normalized` → `classified` → `rights_review` →
`script_draft` → `script_approved` → `voice_generated` →
`subtitles_generated` → `visuals_ready` → `rendering` → `quality_check`
→ `needs_review` → `approved` → `scheduled` → `uploading` → `published`

Ek durumlar: - `rejected` - `failed` - `retry_wait` - `archived`

Her aşama: - Başlangıç/bitiş zamanı. - Input/output dosya
referansları. - Log ve hata bilgisi. - Deneme sayısı. - Tekrar başlatma
desteği.

Bir aşama başarısız olduğunda önceki başarılı aşamaları yeniden
çalıştırma. Örneğin render başarısızsa senaryoyu ve TTS'yi tekrar
üretmek zorunda kalma.

# 14. Veri modeli

Asgari tablolar: - users - channels - channel_oauth_connections -
concept_profiles - source_connectors - source_items -
source_rights_records - categories - content_ideas - scripts -
script_versions - production_jobs - job_stage_runs - media_assets -
subtitles - rendered_videos - thumbnails - publishing_jobs -
published_videos - analytics_snapshots - prompt_templates - audit_logs -
system_settings

İlişkiler ve migration'lar açıkça tanımlansın. OAuth token'ları şifreli
sakla. Hassas ayarları veritabanına düz metin yazma.

# 15. Sunucu kurulumu ve güvenlik

İlk önce sunucu envanterini çıkar:

``` bash
hostnamectl
cat /etc/os-release
lscpu
free -h
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL
df -h
lspci | grep -Ei 'vga|3d|display'
nvidia-smi 2>/dev/null || true
docker --version 2>/dev/null || true
```

Bu komutlar bilgi toplamak içindir. Çıktıları kullanıcıya özetle ve
kurulum planını donanıma göre belirle.

Önerilen hedef: - Ubuntu Server LTS (mevcut işletim sistemi uygunsa
değiştirme). - Docker Engine + Docker Compose. - Ollama. - PostgreSQL. -
Redis. - Uygulama API/UI. - Worker. - FFmpeg. - TTS/STT modelleri. -
Reverse proxy (Caddy veya Nginx) ve HTTPS.

Kurulum kuralları: - Var olan servisleri ve diskleri incele. - Docker
volume'ları kalıcı olsun. - Uygulama verileri, modeller, medya ve
yedekler ayrı klasörlerde tutulsun. - Disk doluluk eşiği ve otomatik
temizlik politikası olsun. - Kaynak videoları ve final videoları için
saklama süresi ayarlanabilsin. - PostgreSQL yedekleri ve geri yükleme
testi olsun. - `.env` dosyası git'e eklenmesin. - Güçlü admin parolası
ve HTTPS. - Dashboard internete doğrudan açık bırakılmasın; reverse
proxy, kimlik doğrulama ve mümkünse VPN/IP kısıtlaması kullan. - SSH
private key veya parola Claude prompt'una, repo'ya veya log'a
yazılmasın. - Container'ları mümkün olduğunca root olmayan kullanıcıyla
çalıştır. - Güvenlik güncellemelerini ve Docker image sürümlerini
kontrollü uygula. - `latest` image tag'lerini üretim kurulumunda
sabitlemeden kullanma.

Claude, SSH üzerinden bağlandığında önce yalnızca envanter ve read-only
kontrolleri yapsın. Kurulumdan önce planı ve etkilenecek servisleri
açıklasın. Reboot, firewall, SSH, disk, partition veya mevcut servis
değişikliklerinde açık onay alsın.

# 16. Donanım kaynak yönetimi

93 GB RAM bilgisi tek başına model seçmek için yeterli değildir. CPU
modeli/çekirdek sayısı, GPU/VRAM, disk tipi ve boş alan tespit edilmeli.

Kaynak yönetimi: - LLM concurrency başlangıçta 1. - Video render worker
sayısı CPU ve RAM ölçümüne göre belirlenmeli. - Whisper ve TTS işleri
kuyruklanmalı. - Aynı anda LLM inference + ağır render sayısı
sınırlandırılmalı. - GPU varsa Ollama ve FFmpeg encoder
kullanılabilirliği ayrı ayrı test edilmeli. - Model context ve
quantization seçimi bellek ölçümüne göre yapılmalı. - Sistem RAM'inin
tamamını LLM'e ayırma. - İlk performans testi tek video ve tek worker
ile yapılmalı.

Claude bir model indirmeden önce modelin lisansını, boyutunu,
quantization seçeneğini, RAM/VRAM gereksinimini ve dil kalitesini
kontrol etsin. Türkçe ve İngilizce örnek test yapmadan varsayılan model
seçimini kesinleştirmesin.

# 17. YouTube para kazanma ve politika güvenliği

Uygulama para kazanmayı garanti edemez. YouTube Partner Program
uygunluğu, kanal incelemesi, ülke, içerik ve güncel YouTube
politikalarına bağlıdır.

Ürün, kanal sahibinin özgün ve değerli içerik üretmesine yardımcı
olmalı; tekrarlayan/seri üretilmiş düşük değerli videoları teşvik
etmemeli.

Zorunlu editoryal korumalar: - Kaynak metni aynen seslendirip yayınlama
varsayılan olarak yasak. - Özgün anlatı, yorum, analiz, öğretici değer
veya belirgin dönüştürücü katkı gerekli. - Aynı şablonla yalnızca
isim/kelime değiştirerek seri video üretimine karşı benzerlik
kontrolü. - Kaynak ve lisans kaydı. - Müzik/görsel lisans kontrolü. -
Gerçekçi sentetik/değiştirilmiş içeriklerde YouTube disclosure
gerekliliği kontrolü. - Çocuklara yönelik içeriklerde Made for Kids
kararını dikkatli yönet. - Telif şikâyeti veya hak belirsizliği olan
içeriği durdur. - İnsan onayı ve yayın öncesi önizleme.

YouTube'un güncel resmi politikaları ve YPP şartları uygulama yapılırken
tekrar kontrol edilsin: -
https://support.google.com/youtube/answer/1311392 -
https://support.google.com/youtube/answer/72851 -
https://support.google.com/youtube/answer/14328491 -
https://developers.google.com/youtube/v3

# 18. Ücretsiz kullanım hedefi ve dış servisler

Hedef, zorunlu ücretli API olmadan çalışmaktır. Ancak her servisin
lisans ve kullanım koşulu doğrulanmalı.

Ücretsiz/yerel tercih: - Ollama: local LLM. - Kokoro veya Piper: local
TTS. - faster-whisper: local STT. - FFmpeg: render. - PostgreSQL:
database. - Redis: queue. - Docker Compose: deployment. - YouTube Data
API: Google'ın ücretsiz kota sınırları dahilinde. - RSS ve kullanıcı
tarafından sağlanan kaynaklar.

Opsiyonel harici kaynaklar (ör. Pexels/Pixabay) ana sistemin zorunlu
bağımlılığı olmasın. API key gerekiyorsa opsiyonel adapter olarak
tanımla. API key olmadan sistem kendi medya arşivi ve RSS/kullanıcı
girdileriyle çalışabilsin.

Microsoft Edge TTS gibi internet bağlantısı gerektiren ücretsiz
servisler, tamamen offline çözüm gibi sunulmamalı. Uygulamada sağlayıcı
tipi `local` veya `remote` olarak işaretlenmeli.

# 19. Test ve kabul kriterleri

Aşağıdaki testler geçmeden projeyi tamamlandı sayma:

## Kurulum

-   Temiz Docker Compose kurulumu yapılabiliyor.
-   Servisler yeniden başlatıldığında veriler korunuyor.
-   Health check'ler çalışıyor.
-   Admin hesabı güvenli oluşturuluyor.

## Local AI

-   Ollama health check başarılı.
-   Modelden yapılandırılmış JSON yanıtı alınıyor.
-   Türkçe ve İngilizce örnek senaryo üretiliyor.
-   Üretim runtime'ında ücretli LLM API çağrısı yok.

## Kaynak

-   RSS öğesi alınabiliyor.
-   Reddit adapter izinli API/erişimle çalışıyor veya eksik credential
    durumunu anlaşılır gösteriyor.
-   Aynı URL/hash tekrar eklenmiyor.
-   Kaynak ve hak durumu saklanıyor.
-   Wattpad için izinsiz scraping yapılmıyor.

## Medya

-   Bir senaryo TTS'ye dönüştürülüyor.
-   SRT/VTT altyazı oluşturuluyor.
-   FFmpeg ile 9:16 ve 16:9 test videoları render ediliyor.
-   Video ve ses kalite kontrolleri geçiyor.
-   Thumbnail oluşturuluyor.

## YouTube

-   OAuth bağlantısı kurulabiliyor.
-   Test videosu private olarak yüklenebiliyor.
-   Video ID ve URL kaydediliyor.
-   Aynı job tekrar çalıştırıldığında mükerrer upload oluşmuyor.
-   Public/scheduled upload kullanıcı onayı olmadan etkinleşmiyor.

## Yönetim

-   En az iki test kanalı ve üç konsept oluşturulabiliyor.
-   Her konseptin dili, sesi, formatı ve yayın ayarı farklı olabiliyor.
-   Bir job panelden izlenebiliyor, iptal edilebiliyor ve güvenli
    biçimde yeniden denenebiliyor.

# 20. Geliştirme sırası

Claude tüm sistemi tek seferde yazmaya çalışma. Aşağıdaki fazları
sırayla tamamla; her fazda test, dokümantasyon ve kullanıcıya kısa rapor
ver.

**Faz 0 --- İnceleme** - Repo analizi, lisans, mevcut özellikler. -
Sunucu envanteri. - Gap analysis. - Mimari ve kurulum planı. - Hiçbir
yıkıcı işlem yapma.

**Faz 1 --- Sunucu altyapısı** - Docker, Ollama, PostgreSQL, Redis. -
Kalıcı volume'lar. - Güvenlik ve health check. - Local model kurulumu ve
test.

**Faz 2 --- Mevcut video motoru** - PurffleShorts mevcut akışını
çalıştır. - Ollama entegrasyonunu doğrula. - Local TTS/STT
sağlayıcılarını ekle/doğrula. - 1 test Short ve 1 test long-form render
et.

**Faz 3 --- Kaynak ve kategori** - Source adapter interface. - RSS ve
Reddit. - Kullanıcı metni/dosya/URL içe aktarma. - Deduplication,
kategori ve hak kaydı. - Wattpad'i yalnızca izinli import yöntemiyle ele
al.

**Faz 4 --- Çoklu kanal/konsept** - Channel ve Concept modelleri. -
Profil bazlı prompt, ses, dil, format. - Kanal bazlı yayın takvimi ve
limit.

**Faz 5 --- Panel ve editoryal kuyruk** - Inbox, script editor, preview,
approval. - Production queue ve log. - Video library.

**Faz 6 --- YouTube** - OAuth. - Private upload. - Thumbnail, metadata,
playlist. - Zamanlama ve kota kontrolü. - Onaylı yayın akışı.

**Faz 7 --- Analitik ve iyileştirme** - YouTube Analytics
erişimi/izinleri. - Performans metrikleri. - Konsept bazlı raporlama. -
AI'ya performans sinyallerini kontrollü aktarma. - Benzerlik ve özgünlük
denetimini güçlendirme.

# 21. Claude'un teslim etmesi gerekenler

Proje sonunda aynı repo içinde şunları teslim et:

-   Çalışır uygulama.
-   `docker-compose.yml` veya Compose dosyaları.
-   `.env.example` (gerçek secret içermeyen).
-   Tek komutla güvenli kurulum script'i.
-   Güvenli güncelleme script'i.
-   Yedekleme ve geri yükleme script'i.
-   Admin paneli.
-   Veritabanı migration'ları.
-   Testler.
-   `README.md` Türkçe kurulum ve kullanım dokümanı.
-   `DEPLOYMENT.md` sunucu işletim dokümanı.
-   `OPERATIONS.md` günlük bakım ve hata giderme.
-   `SECURITY.md` güvenlik ve secret yönetimi.
-   `SOURCE_RIGHTS.md` kaynak/telif/lisans kayıt ilkeleri.

Kullanıcıya her faz sonunda: 1. Ne yapıldığını, 2. Hangi servislerin
çalıştığını, 3. Hangi testlerin geçtiğini, 4. Hangi credential veya
manuel adımın kullanıcıdan beklendiğini, 5. Bir sonraki fazı açıkça
bildir.

# 22. Claude için çalışma biçimi --- kesin talimatlar

-   Önce repo ve sunucuyu incele; varsayım yapma.
-   Mevcut çalışan sistemi bozma.
-   Gerekli olmayan teknoloji ekleme.
-   Lisans ve kullanım koşullarını doğrula.
-   Gizli anahtarları isteme veya dosyaya yazma; `.env.example` üret ve
    kullanıcıya güvenli biçimde nerede tanımlayacağını göster.
-   OAuth bağlantısını kullanıcı Google hesabında kendisi tamamlasın.
-   Kullanıcı adına YouTube'da public yayın yapma; önce private test ve
    açık onay.
-   Reddit/Wattpad/web kaynaklarında erişim ve telif kurallarını aşma.
-   Hataları gizleme; test sonucu ve log ile raporla.
-   Her fazı küçük, geri alınabilir commit'lerle ilerlet.
-   Her değişiklikten sonra ilgili testleri çalıştır.
-   README'de yazan özelliği gerçek kod/test ile doğrula.
-   Donanım uygun değilse pahalı veya ağır model indirmeden önce
    kullanıcıya seçenek sun.
-   Kurulum bitince sunucu yeniden başlatma ve otomatik başlangıç
    davranışını doğrula; reboot gerekiyorsa önceden onay al.
-   Tamamlanmayan özellikleri tamamlandı gibi gösterme.

**İlk cevap olarak yalnızca Faz 0'ı yap:** repo incelemesini ve sunucu
read-only envanterini tamamla; tespitleri, riskleri, donanım uygunluğunu
ve fazlı kurulum planını raporla. Kullanıcı onayı olmadan sistem
kurulumu veya değişiklik başlatma.

------------------------------------------------------------------------

## Başlangıç komutları

Kullanıcı repo'yu kendi geliştirme bilgisayarına klonladıktan sonra
Claude IDE'de bu klasörü açsın. Ardından Claude'a bu belgenin tamamını
ana şartname olarak ver.

Sunucuya SSH erişimi Claude IDE üzerinden yapılandırılabilir. Önce SSH
bağlantısını read-only envanter için kullan. SSH private key'i proje
klasörüne koyma ve Claude sohbetine yapıştırma.

**Ürün adı:** CiciByte AI Media Factory\
**Repo başlangıcı:** PurffleShorts\
**Çalışma ilkesi:** Local-first, modular monolith, human-approved
publishing, source-aware and rights-aware content production.
