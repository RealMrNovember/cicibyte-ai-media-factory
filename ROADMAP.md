# CiciByte AI Media Factory: Yol Haritası

**Son güncelleme:** 14 Kasım 2026 · **Sürüm:** 0.1.0 önizleme (`main`)
**İlgili belgeler:** [Tasarım](docs/superpowers/specs/2026-11-14-media-factory-design.md) · [Ürün şartnamesi](docs/PROJECT_SPEC.md) · [Kaynak ve hak politikası](docs/SOURCE_RIGHTS.md) · [Kurulum](docs/DEPLOYMENT.md)
**Site:** https://mediafactory.cicibyte.com

**Hedef (v0.1):** Reddit'teki bir korku hikâyesinden ilham alınarak yazılmış **özgün** bir İngilizce (ve istenirse Türkçe) Shorts'u Hazır Videolar'a koymak, onayınla bir YouTube kanalına göndermek.
**Durum:** Hedefin uygulama tarafı tamam. Geriye gerçek bir YouTube kanalıyla uçtan uca deneme kaldı (Google OAuth istemcisi gerekiyor).

---

## Mimari (karar verildi)

- **Sunucu her işi yapar:** Veritabanı, kaynak toplama, AI senaryo, ses (Piper), altyazı, render (ffmpeg), zamanlayıcı ve YouTube yükleme sunucuda çalışır.
- **Masaüstü uygulaması yalnızca istemcidir:** Windows uygulaması (kurulum sihirbazıyla) paneli kendi içinde taşır, istekleri Ayarlar'da girilen sunucuya iletir. Sunucuya ulaşılamasa da açılır.
- **Giriş ekranı yok:** Kurulumun tek sahibi var. Koruma ağ düzeyinde: sunucu yalnızca Tailscale ya da `localhost` üzerinden erişilebilir olmalı, **internete açılmamalı**. Yazma isteklerinde zorunlu `X-MF-Client` başlığı, başka web sayfalarının gizlice istek atmasını engeller.
- **Herkes kendi AI'ını ve anahtarlarını bağlar:** OpenAI uyumlu sağlayıcılar, Reddit API ve Google OAuth istemcisi Ayarlar'dan girilir, şifreli saklanır.

---

## Genel durum

| # | Parça | Durum |
|---|---|---|
| 1 | Temel: kurulum, AI yönlendirme, iş kuyruğu, yedekleme | ✅ |
| 2 | Kaynaklar ve alım (Reddit, RSS, web, dosya) | ✅ |
| 3 | Üretim hattı: senaryo → ses → altyazı → 9:16 video | ✅ çekirdek · 🟡 gelişmiş adımlar kaldı |
| 4 | Panel (tr/en) + Stüdyo | ✅ |
| 5 | YouTube: kanal bağlama, yükleme, zamanlı yayın + Takvim | ✅ kod · 🟡 gerçek kanalla denenmedi |
| 6 | Windows uygulaması ve kurulum sihirbazı | ✅ · Mac/Linux paketleri ⬜ |
| — | DL380 üretim sunucusu (CT 175 `mediafactory`) | ✅ çalışıyor |
| — | Showroom ve indirme sitesi (`mediafactory.cicibyte.com`) | ✅ yayında |

**Test durumu:** 237 otomatik testin hepsi geçiyor. Sunucuda Stüdyo ayarlarıyla gerçek video üretildi (yaklaşık 110 sn; AI senaryo + Piper ses + render). YouTube tarafı testlerde sahte Google yanıtlarıyla doğrulandı.

---

## ✅ Tamamlananlar

### Plan 1: Temel
- Docker Compose ile tek komutla kurulum, yedekleme ve geri yükleme script'leri.
- Gizli bilgiler (API anahtarları, token'lar) şifreli saklanıyor; loglarda ve denetim kaydında maskeleniyor. Denetim kaydı tutuluyor.
- **AI sağlayıcıları:** OpenAI uyumlu her uç nokta (Ollama, llama.cpp, 9router, bulut). Görev başına sıralı sağlayıcı listesi, **3 sn** bekleme, en fazla **3 tur**.
- **İş kuyruğu:** PostgreSQL tabanlı; aşama sınıfı başına eşzamanlılık sınırı, yeniden deneme, iptal, heartbeat ile ölü worker kurtarma.

### Plan 2: Kaynaklar ve alım
- Adaptörler: `reddit_rss` (kimlik bilgisi gerekmez), `reddit` (resmî API), `rss`, `web`, elle ekleme (metin, URL, `.txt` `.md` `.pdf` `.docx`).
- Güvenli çekici: SSRF engeli, 5 MB sınırı, robots.txt, site başına ortak istek aralığı ve 429 soğuması (Reddit 5 sn).
- Kanonik URL + hash ile tekilleştirme, hak durumu ve hak geçmişi, hata alan kaynakta üstel geri çekilme.

### Plan 3: Üretim hattı (çekirdek)
- **Senaryo:** Bağlı AI ile özgün senaryo (hook, gelişme, twist, takip çağrısı); başlık, açıklama ve etiketler. Bozuk JSON'a dayanıklı ayrıştırma.
- **Ses:** Piper; İngilizce `ryan-high`, Türkçe `dfki-medium`. Ses modelleri ilk kullanımda indiriliyor.
- **Altyazı:** Ses süresinden tahmini kelime zamanlaması; ASS (videoya gömülü), SRT ve VTT. Türkçe için doğru büyük harf (i → İ).
- **Render:** ffmpeg ile 1080×1920, libx264. Klip yoksa hareketli gradyan arka plan.
- **Arka plan kütüphanesi:** Klip yükleme (2 GB'a kadar), isteğe bağlı lisans notu, küçük resim, art arda aynı klibi seçmeme.
- **Hazır Videolar:** Onayla / Reddet / İndir. İki dil seçilince aynı içerik için iki ayrı video.

### Plan 4: Panel ve Stüdyo
- Derleme gerektirmeyen panel (tr/en), sabit yan menü, mobil uyumlu.
- Sayfalar: Genel Bakış, **Stüdyo**, Kaynaklar, Gelen Kutusu, Üretim (canlı log, iptal, yeniden dene), Hazır Videolar, **Takvim**, Ayarlar (sunucu, YouTube, AI sağlayıcıları, görev rotaları, Reddit).
- **Stüdyo:**
  - Hikâye seçimi (EN/TR filtresi), **kendi hikâyeni ekleme** (metin yapıştırma veya .txt/.md/.pdf/.docx) ya da **AI ile sıfırdan hikâye yazdırma** (konu + dil + uzunluk; Türkçe kaynak eksikliği için).
  - Arka plan klibi seçimi ya da yükleme.
  - Altyazı yazı tipi (Montserrat, Bebas Neue, Roboto, Open Sans, Lato, DejaVu), boyut, renkler, kontur, gölge, büyük harf, satır başına kelime.
  - Konum (önizlemeye tıklayarak) ve animasyon: belirme, zıplama, kayma, **kelime vurgulu karaoke**.
  - **Canlı önizleme** ve 5 hazır stil.
- "Powered by CiciByte Technology" ve Buy Me a Coffee bağlantıları.

### Plan 5: YouTube ve Takvim
- **Kanal bağlama:** Kullanıcının kendi Google OAuth istemcisi (Masaüstü uygulaması türü), PKCE, sistem tarayıcısında giriş. Refresh token şifreli saklanıyor. Birden fazla kanal bağlanabiliyor.
- **Gönderim:**
  - Parçalı (resumable) yükleme. Gönderim hemen ya da **zamanlı** yapılabiliyor: zamanlı video YouTube'a gizli yüklenip `publishAt` ile o saatte YouTube tarafından yayına alınıyor.
  - Görünürlük herkese açık, liste dışı ya da gizli seçilebiliyor.
  - Sentetik içerik beyanı otomatik açık, "çocuklara yönelik değil" işaretli. Başlık, açıklama, etiketler ve `#shorts` senaryodan dolduruluyor.
- **Takvim:**
  - "Video üret" zamanlamaları: seçilen saat ve günlerde, kullanılmamış hikâyelerden üretiyor; adet, dil, süre, kaynak ve Stüdyo stili seçilebiliyor; isteğe bağlı otomatik onay.
  - "YouTube'a gönder" zamanlamaları: her saatte en eski onaylı videoları gönderiyor.
  - Saat dilimine duyarlı.

### Plan 6: Masaüstü uygulaması
- Windows uygulaması (pywebview / WebView2) ve **Inno Setup kurulum sihirbazı**: Türkçe/İngilizce kurulum, Başlat menüsü ve masaüstü kısayolu, kaldırma desteği.
- Panel sunucudan yükleniyor (arayüz güncellemeleri için yeniden kurulum gerekmez); sunucuya ulaşılamazsa uygulamadaki kopya kullanılıyor. Sunucu adresi Ayarlar'dan değiştirilebiliyor. Google girişi gibi sayfalar sistem tarayıcısında açılıyor.
- Derleme: `packaging/build_windows.ps1`.

### Dağıtım (DL380)
- **CT 175 `mediafactory`:** Debian 13; PostgreSQL 17, ffmpeg, yazı tipleri; systemd servisleri `mf-api` ve `mf-worker`.
- Tailscale'de `mediafactory` adıyla görünüyor; uygulama `http://mediafactory:8080` adresine bağlanıyor.
- AI, aynı sunucudaki 9router'dan geliyor (`mf-senaryo`, `mf-siniflandir` combo'ları).

### Showroom
- https://mediafactory.cicibyte.com, `cicibytetechnology` sunucusunda yayında: tanıtım, ekran görüntüleri, Windows indirmesi, sunucu kurulumu, yol haritası, destek.

---

## ⬜ Kalanlar

### Yakın vade (v0.1'i kapatmak için)
- [ ] **Gerçek YouTube denemesi:** Google OAuth istemcisi oluşturulup kanal bağlanacak, ilk video gönderilecek. **Senin yapman gereken bir adım.** Google'ın doğrulanmamış uygulamalardan yüklenen videoları gizliye kilitleme durumu kontrol edilecek.
- [ ] **Arka plan klipleri:** Kütüphaneye ilk Minecraft/parkur kliplerinin (lisanslı) yüklenmesi.
- [ ] **Türkçe kaynaklar:** Güvenilir Türkçe korku RSS kaynağı bulunamadı; şimdilik elle ekleme ve "AI ile yaz" kullanılıyor. İzinli Türkçe kaynak (ör. kendi blogun, izinli siteler) eklenecek.
- [ ] **Reddit 429:** Reddit, sunucunun IP'sine sık sık 429 veriyor. Reddit API kimlik bilgisi Ayarlar'dan girilirse sorun çözülür; alternatif olarak istek aralığı uzatılacak.
- [ ] **GitHub Releases:** Kurulum dosyasının sürüm olarak yayınlanması.

### Üretim kalitesi (Plan 3'ün devamı)
- [ ] faster-whisper ile gerçek kelime hizalaması (şu an tahmini zamanlama).
- [ ] Script Doctor öz-değerlendirme döngüsü ve senaryo düzenleme ekranı (üretimden önce metni elle düzeltme).
- [ ] Özgünlük kontrolü: kaynakla n-gram örtüşmesi, eşik aşılırsa incelemeye düşme.
- [ ] Ses seçimi (Kokoro İngilizce; ses/hız ayarı Stüdyo'da), telaffuz sözlüğü.
- [ ] classify / rights_review aşamaları, hassas içerik işaretleme.
- [ ] Coverr API ile arama ve Mixkit içe aktarma (lisans notuyla).
- [ ] Kapak görseli (thumbnail) ve kalite kontrolü (ses seviyesi, süre, siyah kare).
- [ ] Arka plan müziği ve ses efektleri; 16:9 format (v0.2).
- [ ] Kanallar ve konseptler: kanal başına dil/ses/stil; stok hedefi (`ready_buffer`).

### YouTube (Plan 5'in devamı)
- [ ] Kanal başına günlük yükleme sınırı ve kota takibi.
- [ ] Kapak görseli, oynatma listesi ve altyazı dosyasının da yüklenmesi.
- [ ] Bağlantısı düşen kanal için uyarı ve "Yeniden bağlan".
- [ ] Video açıklamasında isteğe bağlı CiciByte satırı.

### Dağıtım ve paketleme
- [ ] Mac (`.dmg`) ve Linux (`.AppImage`) paketleri GitHub Releases'ta.
- [ ] Windows kurulum dosyasının kod imzası (SmartScreen uyarısını kaldırmak için).
- [ ] Docker kurulumunda Tailscale adı için `MF_ALLOWED_HOSTS` adımının kurulum script'ine eklenmesi.
- [ ] `OPERATIONS.md` (bakım, güncelleme, hata giderme) ve `SECURITY.md`.

---

## 🔧 Altyapı ve operasyon (kod dışı)

| İş | Durum | Kim |
|---|---|---|
| DL380 erişimi (DHCP watchdog, Tailscale) | ✅ | — |
| 9router sunucuda (CT 171), Funnel kapalı, combo'lar kuruldu | ✅ | — |
| Üretim sunucusu CT 175 `mediafactory` | ✅ | — |
| Yerel LLM'ler (Qwen3.6-35B-A3B, Gemma 4 26B-A4B) Türkçe/İngilizce kalite testi | ⬜ indirildi, **test edilmedi** | Ben |
| Google Cloud OAuth istemcisi (YouTube) | ⬜ | **Sen** |
| Reddit API uygulaması (429 sorununu çözer) | ⬜ | **Sen** |
| Oyun arka planı klipleri (kendi kaydın / Coverr / Mixkit) | ⬜ | Sen + ben |
| Sohbete yazılan Proxmox parolalarının değiştirilmesi | ⬜ | **Sen** |
| Coverr API anahtarının yenilenmesi (sohbette açık geçti) | ⬜ | **Sen** |
| iLO kablosunun DL380'in 2. portuna bağlanması | ⬜ | **Sen** |
| cicibyte.com **Cicibyte Hub → AI & Data** listesine ekleme | ⬜ | **Sen** |

---

## 🐞 Bilinen eksikler

- **Ağ güvenliği:** Giriş olmadığı için sunucu portu internete açılmamalı (Tailscale veya `localhost` + reverse proxy kimlik doğrulaması).
- **Altyazı zamanlaması:** Tahmini olduğu için uzun cümlelerde altyazı sesten biraz kayabilir (whisper hizalamasıyla düzelecek).
- **Stüdyo önizlemesi:** Yazı tiplerini Google Fonts'tan yüklüyor; internet yoksa önizleme yedek yazı tipine düşer (videoyu etkilemez).
- **Önizleme ve video farkı:** Önizleme CSS ile yapılıyor; konturda ve satır kırılmasında videodan küçük farklar olabilir.
- **YouTube:** Yükleme yarıda kesilip tekrar denenirse aynı video iki kez yüklenebilir (idempotency yok).
- **Kurulum dosyası imzasız:** Windows ilk açılışta SmartScreen uyarısı gösterebilir.
- Plan 1–2'den ertelenen küçük maddeler (sağlık kontrolü süreleri, RSS 1.0 desteği, IPv6 gömülü adresler vb.) git geçmişindeki önceki ROADMAP sürümünde listeli.

---

## Sıradaki adım

1. Google OAuth istemcisiyle kanalı bağlayıp ilk gerçek YouTube gönderimini yapmak.
2. Senaryo düzenleme ekranı ve whisper ile altyazı hizalaması.
3. Yerel LLM'lerin testi ve kazananın `local` sağlayıcıya bağlanması.

---

Powered by [CiciByte Technology](https://cicibyte.com) · [Buy me a coffee](https://buymeacoffee.com/mikeross)
