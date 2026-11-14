# CiciByte AI Media Factory: Yol Haritası

**Son güncelleme:** 14 Kasım 2026 · **Sürüm:** 0.1.0.dev0 (`main`)
**İlgili belgeler:** [Tasarım](docs/superpowers/specs/2026-11-14-media-factory-design.md) · [Ürün şartnamesi](docs/PROJECT_SPEC.md) · [Kaynak ve hak politikası](docs/SOURCE_RIGHTS.md) · [Kurulum](docs/DEPLOYMENT.md)

**Hedef (v0.1):** Reddit'teki bir korku hikâyesinden ilham alınarak yazılmış **özgün** bir İngilizce (ve istenirse Türkçe) Shorts'u Hazır Video Kataloğu'na koymak, onayınla bir YouTube kanalına **private** yüklemek.

---

## Genel durum

| # | Parça | Durum |
|---|---|---|
| 1 | Temel: kurulum, giriş, AI yönlendirme, iş kuyruğu | ✅ Tamamlandı, `main`'de |
| 2 | Kaynaklar ve alım | ✅ Tamamlandı, `main`'de |
| 3 | Üretim hattı ve medya | ⬜ Sıradaki |
| 4 | Yönetim paneli (React, tr/en) | ⬜ |
| 5 | YouTube yayıncı ve DL380 dağıtımı | ⬜ |
| — | Showroom ve indirme sitesi | ⬜ v0.1 ekran görüntüleri hazır olunca |

**Test durumu:** 224 otomatik testin hepsi geçiyor. Docker kurulumu, yedekleme/geri yükleme ve gerçek `r/nosleep` beslemesinden toplama, laptop'taki Docker'da uçtan uca denendi.

---

## ✅ Tamamlananlar

### Plan 1: Temel
- **Kurulum ve bakım:**
  - Docker Compose ile tek komutla kurulum (`deploy/install.sh`). İlk kurulumda rastgele gizli anahtar ve yönetici parolası üretiliyor.
  - Yedekleme ve geri yükleme script'leri. Geri yükleme tek transaction'da yapılıyor ve öncesinde güvenlik yedeği alınıyor.
- **Giriş ve oturum:**
  - Argon2 parolalar, oturum çerezi, CSRF koruması, yönetici/editör rolleri, giriş deneme sınırı.
  - Çıkış yapınca ve parola sıfırlanınca bütün oturumlar kapanıyor.
- **Gizli bilgiler:** API anahtarları ve token'lar şifreli saklanıyor; loglarda ve denetim kaydında maskeleniyor.
- **Denetim kaydı:** Kimin neyi ne zaman yaptığı tutuluyor.
- **AI sağlayıcıları:** OpenAI uyumlu her uç nokta bağlanabiliyor (Ollama, llama.cpp, 9router, bulut).
- **Görev yönlendirme:** Her görev için sıralı sağlayıcı listesi. Liste bitince **3 sn** bekleniyor ve en fazla **3 tur** deneniyor.
- **İş kuyruğu:** PostgreSQL tabanlı. Aşama sınıfı başına eşzamanlılık sınırı (llm 1, render 1…), yeniden deneme, iptal, kaldığı yerden devam. Ölen worker'ın işleri heartbeat ile kurtarılıyor.
- **Güvenlik varsayılanları:** Sağlık kontrolü, host kontrolü, güvenlik başlıkları, güvenilen proxy ayarı, 12 MB istek gövdesi sınırı.

### Plan 2: Kaynaklar ve alım
- **Adaptörler:** `reddit_rss` (kimlik bilgisi gerekmez), `reddit` (resmî API; kimlik bilgisi Ayarlar'dan), `rss`, `web`, ve elle ekleme (metin, URL, `.txt` `.md` `.pdf` `.docx`).
- **Güvenli çekici:**
  - İç ağ adreslerini her yönlendirme adımında engelliyor (SSRF).
  - Yanıt boyutu en fazla 5 MB; robots.txt'e uyuyor.
  - Site başına istek aralığı ve 429 sonrası soğuma süresi API ile worker arasında **ortak**. `Retry-After` başlığına uyuluyor; Reddit için 5 sn aralık.
- **Tekilleştirme ve hak kaydı:**
  - Kanonik URL ve içerik hash'iyle tekilleştirme; içeriği değişen öğe "güncellendi" olarak işaretleniyor.
  - Her öğe için hak durumu (varsayılan `unknown`) ve hak geçmişi.
- **Zamanlayıcı:** Worker içinde çalışıyor. Hata alan kaynak üstel olarak geri çekiliyor (en fazla 24 saat); bir kaynağın hatası diğerlerini etkilemiyor.
- **REST API:** Kaynak yönetimi, "şimdi topla" (60 sn kuralıyla), Gelen Kutusu filtreleri, hak değişikliği.

---

## ⬜ Kalanlar

### Plan 3: Üretim hattı ve medya *(sıradaki, en büyük parça)*
- [ ] **Kanal ve konsept modelleri:** Dil(ler), ses, görsel stil, hedef süre, otomatik üretim, `ready_buffer` (varsayılan 10), günlük üretim sınırı (varsayılan 6), kaynak–konsept bağlantısı.
- [ ] **Otomatik üretim:** Kaynak öğelerinden iş üretimi. Konsept filtreleri, stok hedefi ve çok dilli `content_group` desteğiyle.
- [ ] **normalize:** Dil algılama ve uzunluk kontrolü.
- [ ] **classify:** Kategori, hassasiyet, güven puanı. Düşük güvenli öğeler manuel incelemeye düşüyor.
- [ ] **rights_review:** `inspired` modunda otomatik geçiş, `adaptation` modunda insan onayı.
- [ ] **script:** Hook, gelişme, doruk, kapanış ve CTA; başlık, açıklama ve etiketler. **Script Doctor** öz-değerlendirme döngüsü; sürüm geçmişi.
- [ ] **Özgünlük kontrolü:** Kaynak metinle n-gram örtüşmesine bakılıyor; eşik aşılırsa iş `needs_review`'e düşüyor.
- [ ] **voice:** Kokoro (İngilizce) ve Piper (Türkçe); telaffuz sözlüğü, hız ayarı.
- [ ] **subtitles:** faster-whisper ile kelime düzeyinde hizalama, SRT ve VTT, dile duyarlı büyük harf (Türkçe "i → İ").
- [ ] **visuals:** Oyun arka planı kütüphanesi (lisans notu zorunlu), Coverr API ile arama ve ekleme, Mixkit tek dosya içe aktarma, art arda aynı klibi seçmeme.
- [ ] **render:** ffmpeg ile 9:16, `libx264` (NVENC/VAAPI algılanırsa o), konsept bazlı render ayarları.
- [ ] **thumbnail:** En iyi kare + başlık yazısı.
- [ ] **quality_check:** Şartname §10'daki kontroller.
- [ ] **Hazır Video Kataloğu:** "Yayına al", "Reddet", "Yeniden üret".

### Plan 4: Yönetim paneli
- [ ] React + TypeScript paneli, Türkçe ve İngilizce, mobil uyumlu, "Quiet Luxury" tarzı.
- [ ] Sayfalar: Genel Bakış, Kanallar, Konseptler, Kaynaklar, Gelen Kutusu, Editoryal Kuyruk, Üretim Kuyruğu (canlı log), Video Kütüphanesi / Hazır Katalog, Sağlayıcılar ve görev rotaları, Ayarlar (kaynak kimlik bilgileri, Coverr anahtarı), Denetim Kaydı.
- [ ] Alt bilgi ve "Hakkında" sayfası: "Powered by CiciByte Technology" ve Buy Me a Coffee.
- [ ] `reddit_rss` öğelerinin "yedek yol / sınırlı metin" olarak işaretlenmesi.

### Plan 5: YouTube yayıncı ve DL380'e dağıtım
- [ ] Kanal başına Google OAuth bağlantısı: "Kanal bağla", şifreli refresh token, 7 günde bir düşen bağlantı için uyarı ve "Yeniden bağlan".
- [ ] Parçalı (resumable) **private** yükleme, idempotency, kota yönetimi; thumbnail, playlist, altyazı, sentetik içerik beyanı, Made for Kids ayarı.
- [ ] Kanal başına günlük yükleme sınırı (varsayılan 2). Public veya zamanlanmış yayın yalnızca açıkça etkinleştirilince.
- [ ] Video açıklamasında isteğe bağlı CiciByte satırı (varsayılan kapalı, bizim kanallarımızda açık).
- [ ] **DL380'e kurulum:**
  - Yeni LXC `medya` container'ı (Docker, `vmbr0` + `vmbr1`).
  - Sağlayıcı olarak 9router (`http://ai-router:20128/v1`), görevler `mf-senaryo` ve `mf-siniflandir` combo'larına yönlenecek.
  - Panele Tailscale üzerinden erişim.
- [ ] `OPERATIONS.md` (günlük bakım, hata giderme) ve `SECURITY.md`.

### Showroom ve indirme sitesi *(ayrı proje)*
- [ ] Subdomain adının seçilmesi (öneri: `mediafactory.cicibyte.com`).
- [ ] Cloudflare'de DNS kaydı. **Senin yapman gereken bir adım.**
- [ ] `cicibytetechnology` sunucusunda aaPanel/nginx üzerinden yayın. Sunucuya dokunan her adım için önce onay alınacak.
- [ ] İçerik: ürün tanıtımı, ekran görüntüleri, GitHub'dan kurulum, CiciByte tanıtımı, Buy Me a Coffee.
- [ ] cicibyte.com'daki **Cicibyte Hub → AI & Data** listesine eklenmesi. **Senin yapman gereken bir adım.**

---

## 🔧 Altyapı ve operasyon (kod dışı)

| İş | Durum | Kim |
|---|---|---|
| DL380 erişimi (DHCP watchdog, Tailscale) | ✅ | — |
| 9router sunucuda (CT 171), Funnel kapalı, combo'lar kuruldu | ✅ | — |
| Yerel LLM için Qwen3.6-35B-A3B ve Gemma 4 26B-A4B indirildi | ✅ indirildi, **test edilmedi** | Ben |
| Türkçe ve İngilizce model kalite testi, kazanan modelin `local`'e bağlanması | ⬜ | Ben |
| 9router: ses, görsel ve STT combo'ları (yerel Piper ve whisper kurulunca) | ⬜ | Ben |
| Sohbete yazılan Proxmox parolalarının değiştirilmesi | ⬜ | **Sen** |
| Coverr API anahtarının yenilenmesi (sohbette açık geçti) | ⬜ | **Sen** |
| Google Cloud OAuth projesi (YouTube için) | ⬜ Plan 5'te | **Sen** |
| Reddit API uygulaması (isteğe bağlı) | ⬜ | **Sen** |
| Oyun arka planı klipleri (kendi kaydın / Coverr / Mixkit) | ⬜ Plan 3'te | Sen + ben |
| iLO kablosunun DL380'in 2. portuna bağlanması | ⬜ | **Sen** |

---

## 📋 Şartname §19 kabul kriterleri

| Kriter | Durum |
|---|---|
| Temiz Docker Compose kurulumu | ✅ |
| Yeniden başlatmada verilerin korunması | ✅ |
| Health check'ler | ✅ |
| Güvenli admin oluşturma | ✅ |
| Ollama/yerel LLM health check, JSON yanıt | 🟡 İstemci hazır, uygulamadan uçtan uca test yok |
| Türkçe ve İngilizce örnek senaryo | ⬜ Plan 3 |
| Runtime'da ücretli LLM çağrısı olmaması | 🟡 Mimari olarak öyle; Plan 3'te doğrulanacak |
| RSS öğesi alınabiliyor | ✅ |
| Reddit izinli erişimle çalışıyor ya da eksik kimlik bilgisini gösteriyor | ✅ |
| Aynı URL/hash tekrar eklenmiyor | ✅ |
| Kaynak ve hak durumu saklanıyor | ✅ |
| Wattpad için izinsiz scraping yok | ✅ |
| TTS, SRT/VTT, 9:16 ve 16:9 render, kalite kontrolleri, thumbnail | ⬜ Plan 3 (16:9 → v0.2) |
| OAuth, private yükleme, video ID kaydı, mükerrer yükleme yok | ⬜ Plan 5 |
| Public/zamanlanmış yayın onaysız etkinleşmiyor | ⬜ Plan 5 |
| 2 kanal ve 3 konsept, farklı dil/ses/format | ⬜ Plan 3 |
| İş panelden izlenip iptal edilip yeniden denenebiliyor | 🟡 API/kuyruk hazır, panel Plan 4'te |

---

## 🐞 Bilinen küçük eksikler (ertelendi)

**Temel (Plan 1):**
- Veritabanı açılışta hazır değilse API container'ı birkaç kez yeniden başlıyor; Docker sonunda toparlıyor.
- `MF_SECRET_KEY` eksikse anlaşılması zor bir hata çıktısı veriyor.
- Giriş deneme sınırlayıcısının belleği zamanla büyüyor.
- Giriş süresinden bir hesabın var olup olmadığı anlaşılabiliyor.
- İzinli host listesinden `localhost` çıkarılırsa Docker sağlık kontrolü bozuluyor.
- Yapılandırma hataları (TaskNotConfigured, 401) gereksiz yere yeniden deneniyor.
- FastAPI dışındaki Python bağımlılıklarının sürümleri sabit değil.
- E-posta benzersizliği büyük/küçük harfe duyarlı.
- Sağlayıcı adresindeki `kullanıcı:parola@` kısmı maskelenmiyor.
- `install.sh` her yönetici oluşturma hatasını "zaten var" diye bildiriyor.
- Sağlık kontrolünün bağlantı bekleme süresi Docker'ın 5 sn sınırından uzun.

**Kaynaklar (Plan 2):**
- Siteler arası yönlendirmede `Authorization` başlığı da iletiliyor.
- gzip ile sıkıştırılmış yanıt, tek bir parçada 5 MB sınırını kısa süreliğine aşabiliyor.
- Bellekteki throttle, aynı süreç içindeki thread'ler arasında tam kesin değil (API ve worker veritabanı throttle'ını kullanıyor).
- NAT64/6to4/Teredo biçimindeki IPv6 adreslerinin içine gömülü özel IPv4 adresleri yakalanmıyor.
- 2000 karakterden uzun elle girilen URL'ler veritabanı hatası verebilir.
- `.txt`/`.md` yüklemelerinde `<` ile `>` arasındaki metin siliniyor.
- RSS 1.0/RDF beslemeleri ve Atom'un `xhtml` içerikleri okunmuyor.
- Gizli anahtar değişince Reddit kimlik bilgisi "okunamıyor" yerine "yapılandırılmamış" görünüyor.
- `reddit_rss` öğeleri panel için "yedek yol" olarak işaretlenmiyor (Plan 4'te ele alınacak).

---

## Sıradaki adım

**Plan 3 (Üretim hattı ve medya)** için uygulama planını yazıp onayına sunmak. İlk iş, indirilmiş iki LLM'in Türkçe ve İngilizce senaryo testi olacak; kazanan model `local` sağlayıcısına bağlanacak.

---

Powered by [CiciByte Technology](https://cicibyte.com) · [Buy me a coffee](https://buymeacoffee.com/mikeross)
