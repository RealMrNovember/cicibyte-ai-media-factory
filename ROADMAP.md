# CiciByte AI Media Factory: Yol Haritası

**Son güncelleme:** 14 Kasım 2026 · **Sürüm:** 0.2.1 (`main`) · [Sürümler](https://github.com/RealMrNovember/cicibyte-ai-media-factory/releases)
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
| 2 | Kaynaklar ve alım + **kaynak kataloğu** (45 hazır kaynak, Türkçe ve İngilizce) | ✅ |
| 3 | Üretim hattı: senaryo → ses → altyazı → 9:16 video | ✅ çekirdek · 🟡 gelişmiş adımlar kaldı |
| 4 | Panel (tr/en) + Stüdyo | ✅ |
| 5 | YouTube: kanal bağlama, yükleme, zamanlı yayın + Takvim | ✅ kod · 🟡 gerçek kanalla denenmedi |
| 6 | Windows uygulaması ve kurulum sihirbazı | ✅ · Mac/Linux paketleri ⬜ |
| — | DL380 üretim sunucusu (CT 175 `mediafactory`) | ✅ çalışıyor, GitHub'dan kendini güncelliyor |
| 7 | Otomatik güncelleme (sunucu + masaüstü) ve ayar dışa/içe aktarma | ✅ |
| — | Showroom ve indirme sitesi (`mediafactory.cicibyte.com`) | ✅ yayında |

**Test durumu:** 324 otomatik testin hepsi geçiyor. Sunucuda Stüdyo ayarlarıyla gerçek video üretildi (yaklaşık 110 sn; AI senaryo + Piper ses + render). YouTube tarafı testlerde sahte Google yanıtlarıyla doğrulandı.

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
- **Kaynak kataloğu:**
  - Dile (EN/TR) ve türe göre filtrelenen, tek tıkla eklenen 43 hazır kaynak.
  - Türler: hikâye ve kurgu, korku ve gizem, gerçek hayat dramları, komik, ilginç bilgiler, bilim ve uzay, tarih ve kültür, teknoloji, haber.
  - İngilizce: Reddit topluluklarının yanı sıra Atlas Obscura, Live Science, NASA, ScienceDaily, HistoryExtra, Wikipedia, BBC ve diğerleri.
  - Türkçe: Kayıp Rıhtım, Onedio, Evrim Ağacı, Bilim Genç, Arkeofili, Independent Türkçe, Webtekno, BBC Türkçe, DW Türkçe, Euronews, NTV, Habertürk, r/Turkey.
  - Hepsi sunucuya eklendi; ilk toplamada 190+ İngilizce ve 100+ Türkçe hikâye geldi.
- **RSS tam metin:** Yalnızca özet veren beslemelerde makale sayfasından tam metin çekiliyor (robots.txt'e uyularak). En kısa uzunluk filtresi ve RSS 1.0/RDF desteği var.
- **Reddit:** Reddit kimlik bilgisi girilince Reddit RSS kaynakları otomatik olarak resmî API'yi kullanıyor. Reddit istekleri arası 10 sn.
- Gelen Kutusu ve Stüdyo'da dil filtresi (Tümü / English / Türkçe).
- **Konu filtresi:** Her hikâyenin konusu kaynağından geliyor. Konular: korku, dram, bilim, tarih, haber…; elle ve AI ile eklenenler "Elle / AI ile" altında. Stüdyo'da sayılarıyla konu çipleri ve kaynak seçici var.
- **Kaynak açma/kapama:** Kaynaklar sayfasında her kaynak için anahtar var; kapalı kaynak toplanmıyor, açılınca hemen sıraya giriyor.

### Plan 3: Üretim hattı (çekirdek)
- **Senaryo:** Bağlı AI ile özgün senaryo (hook, gelişme, twist, takip çağrısı); başlık, açıklama ve etiketler. Bozuk JSON'a dayanıklı ayrıştırma.
- **Ses (ses seçici):**
  - Piper ile İngilizcede 18 ses: erkek ve kadın; Amerikan, İngiliz ve İskoç aksanı; bazıları yüksek kalite.
  - Türkçede Piper'ın tek sesi (`dfki`) var. Çeşitlilik hız (0.8–1.3×) ve ton (−4…+4 yarım ton, süre korunarak) ile sağlanıyor.
  - **Chatterbox Multilingual** (Resemble AI, MIT lisansı): çok daha doğal Türkçe ve İngilizce ses. Ayrı bir sanal ortamda çalışıyor (`MF_CHATTERBOX_PYTHON`); kurulu değilse seçeneklerde görünmüyor.
    - CPU'da yavaş: sesin süresinin yaklaşık 9 katı (40 sn'lik ses ≈ 6 dk). Toplu ve takvimli üretim için uygun.
    - Çıktılara Resemble'ın PerTh filigranı gömülü.
  - Stüdyo'da dil başına ses seçimi ve "Dinle" önizlemesi var; önizlemeler önbelleğe alınıyor. Takvim, Stüdyo'daki sesi kullanabiliyor.
  - Ses modelleri ilk kullanımda indiriliyor (60–120 MB).
- **Altyazı:**
  - **faster-whisper ile gerçek kelime zamanlaması.** Ses dinleniyor, duyulan kelimeler senaryodaki metinle eşleştiriliyor; metin her zaman senaryodaki gibi kalıyor. Yanlış duyulan kelimelerin zamanı komşularından hesaplanıyor.
  - Gerçek denemede İngilizcede 86 kelimenin 85'i, Türkçede 87 kelimenin 76'sı birebir eşleşti. Whisper çalışmazsa tahmini zamanlamaya düşülüyor.
  - Model `MF_WHISPER_MODEL` (varsayılan `small`), CPU'da int8; 40 sn'lik ses için birkaç saniye.
  - Çıktılar: ASS (videoya gömülü), SRT ve VTT. Türkçe için doğru büyük harf (i → İ).
- **Render:** ffmpeg ile 1080×1920, libx264. Klip yoksa hareketli gradyan arka plan. Ses −14 LUFS'e normalize ediliyor ve sınırlayıcıyla kırpılması önleniyor.
- **Arka plan müziği:**
  - Kendi parçalarını yükleyebiliyorsun (mp3, wav, ogg, m4a, flac; lisans notu isteğe bağlı).
  - ffmpeg ile sentezlenen 3 telifsiz ambiyans var: Karanlık uğultu, Gerilim nabzı, Gizem.
  - Stüdyo'da parça seçimi, dinle, ses seviyesi ve anlatıcı konuşurken müziği kısma (ducking) var; başta ve sonda yumuşak geçiş yapılıyor.
  - Takvim aynı müzik ayarını kullanabiliyor.
- **Kapak görseli:** Arka plan klibinden en canlı ve altyazısız kare seçiliyor; üzerine Stüdyo yazı tipi ve vurgu rengiyle büyük başlık yazılıyor. Uzun başlıkta yazı küçülüyor. YouTube'a yüklerken kapak da gönderiliyor (kanal doğrulanmamışsa YouTube reddedebilir; yükleme yine tamamlanır).
- **Kalite kontrolü:** Her videoda çözünürlük, süre, ses varlığı, ses yüksekliği (LUFS), tepe seviyesi, uzun sessizlik, siyah ekran ve altyazı kontrol ediliyor. Hazır Videolar'da ✓/⚠ rozeti ve ayrıntı penceresi var. QC'den geçmeyen video, otomatik onaylı takvimde bile incelemeye düşüyor.
- **Arka plan kütüphanesi:** Klip yükleme (2 GB'a kadar), isteğe bağlı lisans notu, küçük resim, art arda aynı klibi seçmeme.
  - Kliplere birden çok **konu etiketi** verilebiliyor (Stüdyo'da 🏷). "Rastgele" arka planda önce hikâyenin konusuyla etiketli klipler kullanılıyor, yoksa tüm klipler.
- **Hazır Videolar:** Onayla / Reddet / İndir / Düzenle ve yeniden üret. İki dil seçilince aynı içerik için iki ayrı video.
- **Senaryo düzenleme:**
  - Stüdyo'da "Videoyu yapmadan önce senaryoyu bana göster" seçeneği var. AI yazar ve iş durur; başlık, anlatım (kelime ve süre sayacıyla), açıklama ve etiketleri düzenleyip "Onayla ve videoyu üret" dersin.
  - Hazır videolarda metni değiştirip aynı ayarlarla yeniden üretebilirsin.

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
  - **"Her X saatte bir"** sıklığı ve etkin saat aralığı (ör. 09:00–23:00, gece paylaşım yok).
  - **Otopilot (üret ve yayınla):**
    - Her çalışmada seçilen konudan (ya da rastgele bir konudan) kullanılmamış rastgele bir hikâye seçiliyor; dil rastgele, EN ya da TR olabiliyor.
    - Video Stüdyo stili, sesi ve müziğiyle üretiliyor; kalite kontrolünden geçerse otomatik onaylanıp hemen YouTube'a gönderiliyor.
    - Kontrolden geçmezse yayınlanmıyor, incelemeye düşüyor. Kanal bağlı değilse video onaylı olarak bekliyor.

### Plan 6: Masaüstü uygulaması
- Windows uygulaması (pywebview / WebView2) ve **Inno Setup kurulum sihirbazı**: Türkçe/İngilizce kurulum, Başlat menüsü ve masaüstü kısayolu, kaldırma desteği.
- Panel sunucudan yükleniyor (arayüz güncellemeleri için yeniden kurulum gerekmez); sunucuya ulaşılamazsa uygulamadaki kopya kullanılıyor. Sunucu adresi Ayarlar'dan değiştirilebiliyor. Google girişi gibi sayfalar sistem tarayıcısında açılıyor.
- Derleme: `packaging/build_windows.ps1`.

### Plan 7: Otomatik güncelleme ve taşıma
- **Sunucu:**
  - systemd zamanlayıcısıyla 30 dakikada bir GitHub `main` kontrol ediliyor. Yeni commit varsa kurulum, veritabanı geçişi, yeniden başlatma ve sağlık kontrolü yapılıyor; sağlık kontrolü geçmezse önceki commit'e dönülüyor.
  - Video üretilirken güncelleme bekliyor.
  - Ayarlar → Güncellemeler'de sürüm, durum, kayıt, otomatik açma/kapama ve "Şimdi güncelle" var.
  - Docker kurulumları için de çalışıyor (`MF_UPDATE_MODE=docker`).
  - Gerçek deneme: sunucu 202a638'den 7adc246'ya yaklaşık 8 sn'de geçti.
- **Masaüstü:**
  - GitHub Releases'teki son sürüm kontrol ediliyor; panelde "Şimdi güncelle" şeridi çıkıyor.
  - Kurulum dosyası yalnızca bu deponun sürümlerinden ve SHA-256 eşleşirse kabul ediliyor; sessiz kurulumdan sonra uygulama yeniden açılıyor.
  - Gerçek deneme: v0.2.0 kendini v0.2.1'e güncelledi.
- **Yedekle ve taşı:**
  - AI sağlayıcıları ve anahtarlar, görev rotaları, kaynaklar, takvimler, YouTube ve Reddit tek dosyaya aktarılıyor.
  - Anahtarlar yalnızca parolayla ve şifreli dahil ediliyor (PBKDF2 + Fernet).
  - İçe aktarma isimle birleştiriyor, hiçbir şeyi silmiyor.
- **Masaüstünden dosya indirme** (video, kapak, ayar dosyası) düzeltildi.

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
- [ ] **Reddit erişimi:** Reddit, kimliksiz RSS isteklerini sunucunun IP'sinden engelliyor (403/429). Ayarlar → Reddit'e resmî API uygulamasının bilgileri girilince bütün Reddit kaynakları otomatik olarak API'ye geçer. **Senin yapman gereken bir adım** (reddit.com/prefs/apps → "script" uygulaması).
- [x] **GitHub Releases:** v0.2.0 ve v0.2.1 yayında; masaüstü uygulaması buradan güncelleniyor.
- [x] **Otopilot:** "Her X saatte bir rastgele konu ve hikâye seç → video → YouTube'da yayınla".

### Üretim kalitesi (Plan 3'ün devamı)
- [x] faster-whisper ile gerçek kelime hizalaması.
- [x] Senaryo düzenleme ekranı (üretimden önce ve sonra).
- [ ] Script Doctor öz-değerlendirme döngüsü (AI'ın kendi senaryosunu puanlayıp iyileştirmesi).
- [ ] Özgünlük kontrolü: kaynakla n-gram örtüşmesi, eşik aşılırsa incelemeye düşme.
- [x] Ses seçimi, hız ve ton ayarı (Stüdyo ve Takvim).
- [x] Daha doğal Türkçe ses (Chatterbox Multilingual, isteğe bağlı).
- [ ] Chatterbox'ı hızlandırma (GPU ya da kalıcı model süreci), kendi sesinle klonlama (referans ses yükleme), telaffuz sözlüğü.
- [ ] classify / rights_review aşamaları, hassas içerik işaretleme.
- [ ] Coverr API ile arama ve Mixkit içe aktarma (lisans notuyla).
- [x] Kapak görseli ve kalite kontrolü.
- [x] Arka plan müziği (kütüphane + telifsiz ambiyanslar, kısma).
- [ ] Ses efektleri (kapı gıcırtısı, kalp atışı…) ve 16:9 format (v0.2).
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
- **Stüdyo önizlemesi:** Yazı tiplerini Google Fonts'tan yüklüyor; internet yoksa önizleme yedek yazı tipine düşer (videoyu etkilemez).
- **Önizleme ve video farkı:** Önizleme CSS ile yapılıyor; konturda ve satır kırılmasında videodan küçük farklar olabilir.
- **YouTube:** Yükleme yarıda kesilip tekrar denenirse aynı video iki kez yüklenebilir (idempotency yok).
- **Kurulum dosyası imzasız:** Windows ilk açılışta SmartScreen uyarısı gösterebilir.
- Plan 1–2'den ertelenen küçük maddeler (sağlık kontrolü süreleri, RSS 1.0 desteği, IPv6 gömülü adresler vb.) git geçmişindeki önceki ROADMAP sürümünde listeli.

---

## Sıradaki adım

1. Google OAuth istemcisiyle kanalı bağlayıp ilk gerçek YouTube gönderimini yapmak; Reddit API bilgilerini girmek.
2. Ses klonlama (kendi sesin) ve Chatterbox'ı hızlandırma.
3. Yerel LLM'lerin testi ve kazananın `local` sağlayıcıya bağlanması.

---

Powered by [CiciByte Technology](https://cicibyte.com) · [Buy me a coffee](https://buymeacoffee.com/mikeross)
