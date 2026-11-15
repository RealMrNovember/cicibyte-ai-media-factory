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
| 8 | Canlı izleme, pencere başlığında canlı durum, Windows bildirimleri, Program Files kurulumu | ✅ v0.3.0 |
| 9 | Ses klonlama ve Chatterbox'ı hızlandırma | ✅ |
| 10 | Script Doctor, özgünlük kontrolü, hassas içerik ve hak kontrolü | ✅ |
| 12 | Kanallar ve konseptler, hazır video stoku | ✅ |
| 13 | Ses efektleri ve 16:9 format | ✅ |
| 14 | YouTube: günlük sınır, kota takibi, altyazı dosyası, oynatma listesi, yeniden bağlanma uyarısı | ✅ |
| 11 | Instagram Reels: profesyonel hesapta otomatik yayın, kişisel hesapta elle paylaşım | ✅ kod · 🟡 gerçek hesapla denenmedi |
| — | Showroom ve indirme sitesi (`mediafactory.cicibyte.com`) | ✅ yayında |

**Test durumu:** 488 otomatik testin hepsi geçiyor. Sunucuda Stüdyo ayarlarıyla gerçek video üretildi (yaklaşık 110 sn; AI senaryo + Piper ses + render). YouTube tarafı testlerde sahte Google yanıtlarıyla doğrulandı.

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

### Plan 11: Instagram
- **Profesyonel hesap (Creator / İşletme):** Resmî Instagram API'si (Instagram girişiyle). Ayarlar → Instagram'a Meta uygulamasından alınan erişim anahtarı yapıştırılıyor; anahtar şifreli saklanıyor ve sunucu 60 günlük süresi dolmadan kendisi yeniliyor (haftada bir).
- Video sunucudan doğrudan (resumable) yükleniyor; sunucunun internete açık olması gerekmiyor. Açıklamaya başlık, açıklama ve etiketler (en fazla 30 hashtag, 2.200 karakter) yazılıyor.
- **Yayınla** penceresinde YouTube, Instagram ya da ikisi seçiliyor; zamanlamalar ve otopilot da aynı seçimi sunuyor. İkisi seçilince önce YouTube, hemen ardından Instagram yükleniyor (ikisi aynı anda iş durumunu bozmasın diye).
- Instagram API'sinde zamanlı yayın yok: zamanlanan Reels sunucuda bekleyip o saatte gönderiliyor.
- Instagram hatası YouTube'da yayınlanmış videoyu "başarısız" yapmıyor; hata Instagram rozetinde görünüyor ve yeniden denenebiliyor. Geçici hatalar (429/5xx) 5 ve 10 dakika sonra kendiliğinden tekrar deneniyor.
- **Kişisel hesap:** Instagram API'si kişisel hesaplardan paylaşıma izin vermiyor. Bu hesaplar için her videoda **Instagram'da elle paylaş** var: videoyu indir, hazır açıklamayı kopyala, Instagram'da Reels olarak paylaş, "Paylaştım" ile işaretle. Ayarlar ve pencerelerde bu fark açıklanıyor.
- Instagram bağlantısı ayar yedeğine (şifreli) dahil.

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

### Plan 8: Canlı izleme ve masaüstü deneyimi
- **Canlı sayfası:**
  - Şu an üretilen işler: aşama (senaryo, ses, altyazı, render, kapak), ilerleme çubuğu, geçen süre ve 3 sn'de bir akan canlı log.
  - Kuyruk, aktif zamanlamalar ve geri sayım, kaynak ve işçi durumu. Sol menüde ince bir canlı özet satırı var.
- **Altyapı:** Çalışan aşamalar log'larını 3 sn'de bir yazıyor; işçi 15 sn'de bir "hayattayım" sinyali gönderiyor. `/api/activity` her şeyi tek yanıtta veriyor.
- **Pencere başlığı:**
  - Masaüstü uygulamasında Windows çerçevesi yerine kendi başlık çubuğumuz var. Ortada renkli, animasyonlu canlı durum kapsülü (üretimde akan degrade, nabız noktası, ilerleme çizgisi; tıklayınca Canlı sayfası).
  - Küçült/büyüt/kapat düğmeleri, çift tıkla büyütme ve kenarlardan boyutlandırma var. Görev çubuğu yazısı da canlı özeti gösteriyor.
  - Sunucudaki panel eskiyse uygulama normal Windows çerçevesiyle açılıyor.
- **Windows bildirimleri:** Video hazır, YouTube'da yayınlandı/zamanlandı, üretim başarısız ve yeni sürüm olaylarında bildirim çıkıyor; Ayarlar → Sunucu'dan kapatılabiliyor.
- **Kurulum:** Varsayılan yer `C:\Program Files\CiciByte\MediaFactory` (yönetici izni), masaüstü kısayolu varsayılan olarak açık. Kendini güncelleme UAC onayı istiyor.

### Plan 9: Ses klonlama ve hızlı Chatterbox
- **Kendi sesin:** Stüdyo → Ses → "Ses klonla" ile tek kişinin 5–30 sn'lik net konuşmasını yüklüyorsun. Örnek 24 kHz mono WAV'a çevrilip `DATA_DIR/media/voices` içinde saklanıyor.
- **İzin onayı:** Sesin sahibi olduğunu ya da izin aldığını onaylamadan yükleme kabul edilmiyor; onay denetim kaydına yazılıyor.
- **Dil:** Klon hem Türkçe hem İngilizce listede "Kendi seslerim" grubunda çıkıyor; önizleme ve silme düğmesi var. Chatterbox kurulu değilse klonlar gizleniyor ve Piper'a dönülüyor.
- **Hız:** Chatterbox modeli (3 GB) artık her videoda yeniden yüklenmiyor. İşçide kalıcı bir süreç olarak bellekte duruyor, 10 dk iş gelmezse belleği bırakıyor. Klon sesin koşullandırması bir kez hesaplanıp önbellekte tutuluyor.

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
- [x] Script Doctor: AI her senaryoyu 1–10 puanlıyor; 7'nin altındaysa (ya da uzunluk hedeften çok saparsa) notlarla bir kez yeniden yazıp iyi olanı tutuyor. Puan iş detayında görünüyor; `MF_SCRIPT_DOCTOR=false` ile kapatılır.
- [x] Özgünlük kontrolü: senaryonun 5 kelimelik dizilerinin kaynakla örtüşmesi (%15 üstü) ya da arka arkaya 12+ kelime kopya varsa kalite kontrolü başarısız olur; video otopilotta bile yayınlanmaz, incelemeye düşer. Kendi hikâyelerin (AI hikâyesi) kontrol edilmez. Çeviriyle kopyayı yakalamaz.
- [x] Ses seçimi, hız ve ton ayarı (Stüdyo ve Takvim).
- [x] Daha doğal Türkçe ses (Chatterbox Multilingual, isteğe bağlı).
- [x] Chatterbox'ı hızlandırma (kalıcı model süreci) ve kendi sesinle klonlama (referans ses yükleme).
- [x] Telaffuz sözlüğü: Stüdyo → Ses → 📖 Telaffuz sözlüğü. Yalnızca seslendirilen metin değişir; altyazı, başlık ve açıklama orijinal yazımı korur. Satır satır dinleme.
- [x] Chatterbox için GPU: Doku2'deki RTX 5060'ta ses sunucusu (`mf-tts` servisi, yalnızca Tailscale adresinde, anahtarlı). Türkçe önizleme işlemcide 50–78 sn, ekran kartında 4–5 sn. Doku2 kapalıysa sunucudaki CPU kopyasına düşer.
- [x] Hassas içerik ve hak kontrolü: AI (`classify` rotası, yoksa `script`) senaryoda platformların kısıtladığı içeriği işaretliyor (çocuklara zarar, cinsellik, kendine zarar, nefret, tehlikeli talimat, aşırı vahşet, gerçek yakın trajedi). Korku türü sorun sayılmıyor. İşaretlenen ya da hakları "kısıtlı" olan video kalite kontrolünden geçemez; otopilotta bile yayınlanmaz, incelemeye düşer. AI kontrol yapamazsa da incelemeye düşer.
- [x] Coverr API ile arama (Ayarlar → Stok klipler'e kendi anahtarın) ve Mixkit bağlantısından içe aktarma; lisans ve kaynak her klibin yanında saklanıyor. İlk 4 Mixkit parkur klibi kütüphanede.
- [x] Kapak görseli ve kalite kontrolü.
- [x] Arka plan müziği (kütüphane + telifsiz ambiyanslar, kısma).
- [x] Ses efektleri: hikâyede geçen yerlere (kapı vuruşu, gıcırtı, kalp atışı, saat, fısıltı, gök gürültüsü, çığlık/çarpma) ve açılış cümlesine efekt; Türkçe ve İngilizce kelimelerle, en az 3 sn arayla, en fazla 6 tane. Efektler ffmpeg ile sentezleniyor (telif yok); `media/sfx` klasörüne kendi kayıtların konabiliyor. Stüdyo → Müzik'ten açılıp kapanıyor, seviyesi ayarlanıyor.
- [x] 16:9 format: Stüdyo → Altyazı → Format. 1920×1080 render, ölçeklenmiş altyazı, 1280×720 kapak, kalite kontrolü ve YouTube'da `#shorts` etiketsiz yükleme.
- [x] Kanallar ve konseptler: Takvim → Kanallar ve konseptler'de kanal başına tarif (dil, konu, süre, Stüdyo'dan stil/ses/müzik, YouTube kanalı, platformlar, görünürlük). "Şimdi bir tane üret", otopilot ve yayın zamanlamaları konsepti izleyebiliyor. **Stok hedefi:** sunucu 10 dakikada bir, hedefin altındaki konseptler için (her seferinde en fazla 2) yeni video üretiyor; isteğe bağlı otomatik onay. Ayar yedeğine dahil.

### YouTube (Plan 5'in devamı)
- [x] Kanal başına günlük yükleme sınırı (varsayılan 6) ve API kota takibi: sınır ya da kota dolunca yükleme bekliyor, Pasifik gece yarısı kota sıfırlanınca kendiliğinden gidiyor.
- [x] Kapak görseli, oynatma listesi (kanal başına) ve altyazı dosyasının (SRT, altyazı kanalı olarak) yüklenmesi; reddedilirse yükleme yine tamamlanıyor.
- [x] Erişimi geri alınan kanal için uyarı ve "Yeniden bağlan".
- [x] Video açıklamasında isteğe bağlı CiciByte satırı (Ayarlar → Açıklama satırı; varsayılan kapalı; YouTube ve Instagram, videonun dilinde).

### Dağıtım ve paketleme
- [x] Mac (`.dmg`, Apple Silicon ve Intel) ve Linux (`.AppImage`) paketleri: her sürümde GitHub Actions derliyor, açılış testinden geçiriyor ve sürüme ekliyor (v0.4.0). Mac/Linux'ta güncelleme indirme sayfasını açar.
- [x] Stüdyo yazı tipleri panelin içinde (Google Fonts'a bağlı değil; internetsiz de doğru önizleme).
- [ ] Windows kurulum dosyasının kod imzası (SmartScreen uyarısını kaldırmak için).
- [x] Docker kurulumunda Tailscale adı için `MF_ALLOWED_HOSTS` adımı (`deploy/install.sh` Tailscale adresini ve adını kendisi ekliyor).
- [x] `docs/OPERATIONS.md` (neler nerede çalışır, rutin bakım, sık sorunlar) ve `SECURITY.md` (güvenlik açığı bildirimi, güvenlik modeli).

---

## 🔧 Altyapı ve operasyon (kod dışı)

| İş | Durum | Kim |
|---|---|---|
| DL380 erişimi (DHCP watchdog, Tailscale) | ✅ | — |
| 9router sunucuda (CT 171), Funnel kapalı, combo'lar kuruldu | ✅ | — |
| Üretim sunucusu CT 175 `mediafactory` | ✅ | — |
| Yerel LLM'ler (Qwen3.6-35B-A3B, Gemma 4 26B-A4B) Türkçe/İngilizce kalite testi | ✅ test edildi (15 Kasım, CCSE işçileri 20 dk duraklatılarak): **Gemma 4 26B-A4B** Türkçede açık ara en doğal ve hatasız; uzunluğa en iyi uyan da o. Hız ~6,6 token/sn (mevcut Qwen3-30B ~9,5). Qwen3-30B ve Qwen3.6 Türkçede dil bilgisi hataları yapıyor. ✅ Media Factory'ye ayrı servis olarak bağlandı: CT 120'de `llama-gemma` (port 8081, 4 çekirdek, düşük öncelik); 9router'da `localg/gemma-4-26b-a4b`, `mf-senaryo` ve `mf-siniflandir` combo'larının son yedeği. CCSE kendi Qwen3-30B'sinde (8080) kaldı | — |
| Google Cloud OAuth istemcisi (YouTube) | ⬜ | **Sen** |
| Meta uygulaması + Instagram erişim anahtarı (profesyonel hesap) | ⬜ | **Sen** |
| Reddit API uygulaması (429 sorununu çözer) | ⬜ | **Sen** |
| Oyun arka planı klipleri (kendi kaydın / Coverr / Mixkit) | ⬜ | Sen + ben |
| Sohbete yazılan Proxmox parolalarının değiştirilmesi | ⬜ | **Sen** |
| Coverr API anahtarının yenilenmesi (sohbette açık geçti) | ⬜ | **Sen** |
| iLO kablosunun DL380'in 2. portuna bağlanması | ⬜ | **Sen** |
| cicibyte.com **Cicibyte Hub → AI & Data** listesine ekleme | ⬜ | **Sen** |

---

## 🐞 Bilinen eksikler

- **Ağ güvenliği:** Giriş olmadığı için sunucu portu internete açılmamalı (Tailscale veya `localhost` + reverse proxy kimlik doğrulaması).
- **Önizleme ve video farkı:** Canlı önizleme CSS ile yapılıyor; konturda ve satır kırılmasında küçük farklar olabilir. Birebir görmek için Stüdyo'da **🎯 Gerçek kareyi göster** (sunucuda videoyla aynı altyazı motoruyla çizilir).
- **Kurulum dosyası imzasız:** Windows ilk açılışta SmartScreen uyarısı gösterebilir.
- **Plan 1–2'den ertelenen küçük maddeler:**
  - ✅ 15 Kasım'da kapatıldı: IPv6 içine gömülü özel IPv4 adresleri (6to4, Teredo, NAT64) engelleniyor; yönlendirmede `Authorization`/`Cookie` başka siteye taşınmıyor; adreslerdeki `kullanıcı:parola@` kayıtlarda maskeleniyor; ayar eksikliği hataları (görev rotası yok) boşuna yeniden denenmiyor; 2000 karakterden uzun besleme adresleri hata vermiyor; .txt/.md yüklemelerinde `<…>` metni korunuyor; Atom `xhtml` içerikleri okunuyor. RSS 1.0/RDF daha önce eklenmişti.
  - Artık geçersiz (giriş ekranı kaldırıldı): giriş süresinden hesap tahmini, giriş deneme sınırlayıcısının belleği, e-posta büyük/küçük harf.
  - ✅ Kalanlar da kapatıldı: `mf migrate` veritabanını 60 sn bekliyor (Docker'da yeniden başlama döngüsü yok); eksik/yanlış `MF_SECRET_KEY` gibi ayarlar okunur bir mesajla bildiriliyor; Docker sağlık kontrolü `mf healthcheck` ile izinli host adını kullanıyor; sağlık kontrolünün bağlantı süresi 3 sn; bağımlılıklar ana sürümlerinde sabitlendi; indirmeler 64 KB parçalarla okunuyor (gzip'te de 5 MB sınırı kesin); bellekteki hız sınırlayıcı paralel istekleri sıraya koyuyor; okunamayan Reddit bilgisi Ayarlar'da "okunamıyor" diye görünüyor.

---

## Sıradaki adım

1. Google OAuth istemcisiyle kanalı bağlayıp ilk gerçek YouTube gönderimini yapmak; Instagram anahtarını girip ilk Reels'i göndermek; Reddit API bilgilerini girmek.
2. Yerel yedek (Gemma 4) gündüz CCSE ile aynı işlemciyi paylaşıyor; ikisi aynı anda çalışırsa yavaşlar. Gerekirse CT 120'ye çekirdek eklemek.
3. Telaffuz sözlüğü (TTS'in yanlış okuduğu kelimeler için).

---

Powered by [CiciByte Technology](https://cicibyte.com) · [Buy me a coffee](https://buymeacoffee.com/mikeross)
