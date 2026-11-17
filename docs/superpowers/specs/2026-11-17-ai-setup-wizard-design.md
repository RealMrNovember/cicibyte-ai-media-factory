# Tek Başına Çalışan Uygulama ve Kolay Kurulum — Tasarım Belgesi

**Tarih:** 17 Kasım 2026
**Durum:** Onaylandı (17 Kasım 2026)
**Sürüm hedefi:** v0.5.0 önce Windows; macOS ve Linux sonraki sürümde (v0.5.x)

## 1. Amaç ve neden

**Kullanıcı ne diyor:** "İnsanlar sadece uygulamamı kullanacak. Varsa kendi sunucularını kullanacaklar, yoksa API üzerinden anlaşmalı oldukları yapay zekâ araçlarını kullanacaklar."

**Bugünkü durum:**
- Masaüstü uygulaması yalnızca bir pencere. Bütün üretim (veritabanı, iş sırası, ses, altyazı, render, yayın) ayrı bir Media Factory sunucusunda çalışıyor.
- Uygulamada varsayılan sunucu adresi `http://mediafactory:8080`. Bu ad yalnızca geliştiricinin kendi Tailscale ağında var.
- Sonuç: uygulamayı kuran başka biri "Tailscale bağlı değil" mesajıyla karşılaşıyor. Kendi bilgisayarındaki yapay zekâyı da bağlayamıyor.

**Hedef:**
- Uygulama kurulduğu bilgisayarda **kendi başına** çalışsın; video üretimi tamamen o bilgisayarda olsun.
- Yapay zekâ kullanıcının seçimine göre gelsin:
  - **kendi yapay zekâ sunucusu:** aynı bilgisayardaki Ollama/LM Studio ya da başka bir yerde kurduğu bir sunucu,
  - **anlaşmalı olduğu bir servis:** OpenAI, Anthropic, Gemini, OpenRouter… API anahtarıyla.
- İlk açılışta adım adım bir **Kolay Kurulum** bunu birkaç dakikada tamamlatsın.

## 2. Hedefler, kapsam dışı olanlar, başarısızlık sayılanlar

**Hedefler**
- Yeni kurulan uygulama hiçbir sunucu, Docker ya da Tailscale istemeden çalışsın.
- Üretim motoru (API + iş sırası + zamanlayıcı + kaynak toplayıcı) uygulamanın içinde, kullanıcının bilgisayarında çalışsın.
- Kolay Kurulum şunları yaptırsın:
  - yapay zekâ seçimi: bilgisayarda bulunan / kendi sunucusu / hazır servis listesi + API anahtarı,
  - modeller,
  - kısa bir deneme.
- Ağır modeller (ses, altyazı) zaten ilk kullanımda iniyor; ilk açılışta ilerleme göstererek önceden indirilsin.
- Geliştiricinin bugünkü düzeni (uzak sunucu, CT 175) bozulmasın. Bu düzen "Gelişmiş: uzak Media Factory sunucusuna bağlan" seçeneği olarak kalsın.

**Kapsam dışı (bu sürümde değil)**
- Ollama ya da LM Studio'yu kullanıcı adına kurmak, LLM modeli indirmek. Sihirbaz yalnızca bulur; hiçbiri yoksa indirme bağlantılarını gösterir.
- Masaüstü aracısı (önceki taslaktaki Yol B). Motor yapay zekâyla aynı bilgisayarda olduğu için gerek kalmadı.
- Uygulama kapalıyken arka planda üretim (sistem tepsisi servisi). Bu sürümde motor uygulama açıkken çalışır; pencere küçültülse de devam eder.
- Chatterbox (GPU ses) kurulumu. Varsayılan Piper sesleri kullanılır; uzak Chatterbox ayarı gelişmiş seçenek olarak kalır.

**Başarısızlık sayılanlar**
- Herhangi bir yerde Tailscale ya da geliştiricinin kendi altyapısının varsayılması.
- Kullanıcının API anahtarının düz metin olarak diske yazılması ya da bir yere gönderilmesi.
- İki uygulama penceresinin aynı motoru ikinci kez başlatıp veritabanını bozması.
- Uygulama kapanınca arkada yetim süreç (Postgres, worker) kalması.
- Bir kurulum adımı başarısız olunca kullanıcının ne yapacağını bilmemesi.

## 3. Mimari

### 3.1 Çalışma modları
Masaüstü `config.json` dosyasına `mode` alanı eklenir:
- **`local` (yeni kurulumlarda varsayılan):** motor uygulamanın içinde başlar; panel `http://127.0.0.1:<port>` adresinden yerel motora bağlanır.
- **`remote`:** bugünkü davranış; panel kayıtlı sunucu adresine bağlanır.

Geçiş kuralları:
- `server_url` kayıtlı eski kurulumlar ilk açılışta otomatik olarak `remote` olur. Geliştiricinin bilgisayarları böyle kalır.
- `DEFAULT_SERVER = "http://mediafactory:8080"` kaldırılır.
- Uzak mod yalnızca Ayarlar → Gelişmiş'ten seçilir.

### 3.2 Gömülü motor (`desktop_engine.py`, yeni)
Uygulama `local` modda açılınca:
1. **Veri klasörü:**
   - Windows: `%LOCALAPPDATA%\CiciByteMediaFactory\data`
   - macOS: `~/Library/Application Support/CiciByteMediaFactory`
   - Linux: `~/.local/share/cicibyte-mediafactory`
   - Videolar, modeller ve veritabanı burada durur.
2. **Tek kopya:** uygulama tek kopya çalışır. İkinci kez açılınca yeni pencere açılmaz; çalışan pencere öne gelir. Bu, kilit dosyası (`engine.lock`) ve yerel bir "öne gel" isteğiyle yapılır. Böylece motorun tek bir sahibi olur: o pencere kapanınca motor da durur.
3. **Gizli anahtar:** ilk açılışta `MF_SECRET_KEY` üretilir ve veri klasöründe yalnızca kullanıcının okuyabileceği bir dosyada (`engine.key`) saklanır. Ayar yedeği bu anahtara değil, kendi parolasına dayandığı için taşıma etkilenmez.
4. **Gömülü PostgreSQL:**
   - `pgserver` paketi kullanılır (PostgreSQL ikili dosyalarını Windows/macOS/Linux için Python paketi olarak getirir).
   - Veritabanı `data/pg` altında, yalnızca `127.0.0.1` adresinden, rastgele boş bir portta başlar.
   - Kod PostgreSQL'e özgü özellikler kullandığı için (`FOR UPDATE SKIP LOCKED`, advisory lock, JSONB) SQLite'a geçilmez.
5. **Migration:** `mf migrate` aynı süreçte çalıştırılır. Bekleme mantığı (60 sn) zaten var.
6. **API ve worker:** aynı çalıştırılabilir dosya, alt komutlarla iki alt süreç olarak başlatılır:
   - `--engine api`: uvicorn, `127.0.0.1` adresinde rastgele bir port.
   - `--engine worker`: iş sırası, zamanlayıcı ve kaynak toplayıcı; bugünkü `mf worker` ile aynı.
   - Ortam değişkenleri: `MF_DATABASE_URL`, `MF_SECRET_KEY`, `MF_DATA_DIR`, `MF_ALLOWED_HOSTS=["127.0.0.1","localhost"]`.
7. **Panel:** masaüstünün yerel proxy'si `/api` isteklerini yerel API'ye iletir. Bugünkü proxy yapısı aynen kullanılır; yalnızca hedef adres değişir.
8. **Kapanış:** pencere kapanınca worker'a durma isteği gönderilir. Windows'ta SIGTERM süreci anında öldürdüğü için bu istek sinyalle değil, bir **durma dosyasıyla** (`data/engine.stop`) yapılır; worker döngüsü bu dosyayı da izler. Worker 20 sn içinde kapanmazsa öldürülür.
   Masaüstü güncelleyicisi de kendini kapatmadan önce aynı kapanış yolunu kullanır; bugünkü `os._exit` motoru yetim bırakmaz. Ardından API ve Postgres durdurulur (`pg_ctl stop -m fast`). Uygulama çökse bile bir sonraki açılışta eski kilit ve PID dosyaları temizlenir.
9. **Sağlık denetimi:** masaüstü motoru izler; bir alt süreç ölürse bir kez yeniden başlatır, tekrar ölürse panelde "motor durdu — günlüğü göster" kartı gösterir. Günlükler `data/logs` altında döner (5 × 5 MB).

**Paketleme:**
- PyInstaller paketine motor bağımlılıkları eklenir: `pgserver`, `piper-tts`/onnxruntime, `faster-whisper`/ctranslate2, psycopg ve benzerleri.
- **ffmpeg/ffprobe** her platform için LGPL derlemesi olarak pakete dahil edilir ve motorun `PATH` değişkeninin başına eklenir. Lisans metni pakette yer alır.
- Kurulum dosyasının yaklaşık 200–300 MB olması beklenir. Ses ve altyazı modelleri pakete girmez, ilk açılışta iner.

### 3.2a Windows ve macOS'a taşıma
Üretim hattı bugüne kadar yalnızca Linux konteynerlerinde çalıştı. Bu iş bir **taşıma ve test aşaması** içerir:
- `data_dir` varsayılanı `/data` yerine motorun verdiği klasör olur.
- Yollar, yazı tipleri, ffmpeg çağrıları, Piper ve faster-whisper Windows ve macOS'ta uçtan uca denenir.
- Her platformda gerçek bir videonun baştan sona üretildiği bir duman testi yapılır.
- Bir özellik bir platformda çalışmazsa, sessizce kaybolmaz: açıkça kapatılır ve ekranda nedeni yazar.

### 3.3 Kolay Kurulum (ilk açılış, `web/setup.js`)
Motor `local` modda ilk kez açıldığında ve kurulum tamamlanmamışsa (`SystemSetting "setup"` yoksa) panel bu ekranla açılır. Ayarlar'dan her zaman yeniden başlatılabilir.

1. **Hoş geldin + dil:** Türkçe / English; panel dili de buna göre ayarlanır.
2. **Hazırlık:**
   - Varsayılan Piper sesleri (TR + EN) ve altyazı hizalama modeli (whisper, küçük) ilerleme çubuğuyla iner.
   - Bu adım arka planda sürerken kullanıcı sonraki adımlara geçebilir.
   - İnternet yoksa "sonra indir" seçilebilir; ilk video sırasında iner.
3. **Yapay zekâ:** üç sekmeden biri seçilir:
   - **Bu bilgisayarda:**
     - Motor `127.0.0.1` adresinde bilinen portları tarar (§3.4).
     - Bulunanlar kart olarak görünür: araç, model sayısı, ✓.
     - Hiçbiri yoksa Ollama ve LM Studio indirme bağlantıları ve "kurduktan sonra tekrar tara" düğmesi gösterilir.
   - **Kendi sunucum:**
     - OpenAI uyumlu adres (ör. `http://192.168.1.20:11434/v1`) ve isteğe bağlı API anahtarı girilir.
     - "Bağlantıyı dene" adresi kontrol edip modelleri listeler.
     - Ollama'nın yerel `/api` adresi girilirse `/v1` kendiliğinden eklenir.
   - **Yapay zekâ servisi:**
     - Hazır listeden seçilir (§3.5) ve API anahtarı yapıştırılır.
     - Anahtar denenir, modeller listelenir.
     - Servisin anahtar alma sayfasına bağlantı verilir.
4. **Modeller:**
   - Senaryo ve sınıflandırma için model seçilir; ikisinde de varsayılan olarak aynı model seçili gelir.
   - Servisler için önerilen bir varsayılan model işaretli gelir; yerel araçlarda en büyük "instruct/chat" model üstte durur.
   - İsteğe bağlı olarak ikinci bir yapay zekâ "yedek" olarak eklenebilir.
5. **Dene:**
   - Senaryo görevi kısa bir TR ve EN istemiyle çalıştırılır; süre ve ilk satırlar gösterilir.
   - Başarısızsa hata sade dille açıklanır, ör. "anahtar geçersiz", "model bulunamadı", "zaman aşımı — daha küçük bir model seç".
6. **Bitti:** "İlk videonu yap" (Stüdyo) ve "YouTube / Instagram / TikTok bağla" (Ayarlar) kısayolları gösterilir.

**Sihirbazın kaydettikleri:**
- Bir `AIProvider` kaydı; ad otomatik verilir, ör. "Ollama (bu bilgisayar)", "OpenAI".
- Senaryo ve sınıflandırma rotaları:
  - Rota boşsa yalnızca bu model kullanılır.
  - Rota doluysa seçilen model rotanın başına eklenir, eski adımlar yedek olarak arkada kalır.
  - Mevcut rota hiçbir zaman sormadan silinmez.

### 3.4 Yerel tarama (`ai/discovery.py`)
- Bilinen araç profilleri ve portları:

  | Araç | Port |
  |---|---|
  | Ollama | 11434 |
  | LM Studio | 1234 |
  | Jan | 1337 |
  | llama.cpp | 8080 |
  | KoboldCpp | 5001 |
  | LocalAI | 8080 |
  | vLLM | 8000 |
  | text-generation-webui | 5000 |
  | GPT4All | 4891 |

  Aynı porttaki araçlar yanıtlarından ayırt edilir. Ollama `/api/version` adresinden tanınır, ötekiler `GET /v1/models` ile.
- Tarama yalnızca `127.0.0.1` adresinde ve yalnızca bu portlarda yapılır. Genel amaçlı bir tarayıcı değildir.
- Uç noktalar:
  - `GET /api/ai-setup/scan`
  - `POST /api/ai-setup/check {base_url, api_key?}`: kendi sunucusu ve servisler için.
  - `POST /api/ai-setup/apply`
  - `POST /api/ai-setup/try`
- Uzak modda da çalışır. Sunucu kendi yerelini tarar; geliştiricinin düzeninde bu yine faydalı.
- Uygulamada giriş yok; API'ye ulaşan herkes yönetici sayılıyor. Bu yüzden:
  - Serbest adres kabul eden `check` ve `try` yalnızca **yerel modda**, yani motor `127.0.0.1` adresinde çalışırken açıktır. Bu durumda yalnızca aynı bilgisayardan ulaşılabilirler.
  - Uzak modda (ağa açık sunucu) bu uç noktalar yalnızca hazır servis adreslerini ve sunucunun kendi `127.0.0.1` taramasını kabul eder. Böylece sunucu, ağdaki birine açık bir proxy olmaz.

### 3.5 Hazır servis listesi (`ai/presets.py`)
Mevcut istemci OpenAI uyumlu uç noktalarla çalışıyor. Aşağıdaki servislerin hepsi OpenAI uyumlu adres sunuyor, bu yüzden yeni bir istemci gerekmiyor:

| Servis | Adres | Anahtar sayfası |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | platform.openai.com/api-keys |
| Anthropic (Claude) | `https://api.anthropic.com/v1` | console.anthropic.com |
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` | aistudio.google.com/apikey |
| OpenRouter | `https://openrouter.ai/api/v1` | openrouter.ai/keys |
| Groq | `https://api.groq.com/openai/v1` | console.groq.com/keys |
| DeepSeek | `https://api.deepseek.com/v1` | platform.deepseek.com |
| Mistral | `https://api.mistral.ai/v1` | console.mistral.ai |
| xAI | `https://api.x.ai/v1` | console.x.ai |

- Her servis için önerilen varsayılan modeller listede tutulur; model listesi servisten canlı olarak da çekilir.
- Bu adresler ve önerilen modeller uygulama içindeki tek bir dosyada durur ve sürümle güncellenir.
- Anahtar, mevcut `AIProvider.api_key_enc` alanına şifreli olarak yazılır; yerel motorun gizli anahtarıyla şifrelenir.
- Uyumluluk uç noktasının bir servis için model listeleme desteği yoksa, önerilen modeller elle seçilebilir.
- **Servise özel küçük ayarlar:** her hazır servis şu bayrakları taşıyabilir:
  - `json_mode: "prompt"`: `response_format` gönderme, JSON talimatını isteme ekle. Örneğin Anthropic uyumluluk katmanı `response_format`'ı yok sayabiliyor; bu bayrak olmadan senaryo çıktısı ayrıştırılamaz.
  - ek başlıklar.
  - `check: "chat"`: anahtarı model listesi yerine küçük bir sohbet isteğiyle dene.
  
  `ai/client.py` bu bayrakları okuyacak şekilde küçük bir değişiklik alır. Bunun için `AIProvider` tablosuna bir `options` JSON alanı eklenir (migration). Her servis kurulumdan önce gerçek bir anahtarla denenir; denenemeyenler listede "deneysel" etiketiyle durur.

### 3.6 Panel ve masaüstü değişiklikleri
- Sunucuya ulaşılamadığında çıkan rehber kartı yalnızca `remote` modda görünür. Tailscale anılmaz; "sunucu adresini kontrol et ya da Yerel moda dön" yazar.
- **Ayarlar → Gelişmiş:** "Bu bilgisayarda çalış (önerilen)" / "Uzak Media Factory sunucusuna bağlan" seçimi. Mod değişince uygulama yeniden başlar.
- Yerel modda sunucuya özel kartlar gizlenir:
  - Sunucu güncellemeleri (GitHub otomatik güncelleyicisi): uygulama güncellemesi zaten masaüstü güncelleyicisiyle geliyor.
  - Sunucu adresi.
- Genel Bakış'ta motor durumu ve veri klasörü (diskteki yer, "klasörü aç") gösterilir.
- `deploy/install.sh` paneli nerede yayınlayacağını sorar (yalnızca bu makine / yerel ağ / Tailscale varsa Tailscale). Bu yalnızca sunucu kuranlar içindir; Tailscale artık varsayılan değildir.

### 3.7 Sürüm
- **Önce Windows (kullanıcı kararı):**
  - v0.5.0 Windows'ta yerel modla çıkar.
  - macOS ve Linux paketleri bu sürümde bugünkü gibi yalnızca uzak modla derlenmeye devam eder. Yerel mod bu platformlarda "yakında" olarak görünür ve seçilemez.
  - Taşıma ve testleri tamamlanınca macOS ve Linux v0.5.x ile gelir.
- Windows paketi yerelde derlenir ve duman testinden geçer. Duman testi yerel modda motoru başlatıp `/api/health` adresini kontrol eder ve kısa bir test videosu üretir.
- İndirme sitesi güncellenir (sürüm kontrol listesi).
- README "kurulum" bölümü yeniden yazılır: önce uygulamayı indir; sunucu kurmak gelişmiş bir seçenek.

## 4. Değerlendirilen yaklaşımlar
- **Gömülü PostgreSQL ile motor (seçilen):** mevcut kod ve testler neredeyse değişmeden kalır; risk paketleme ve süreç yönetiminde. Kullanıcı bunu seçti.
- **SQLite'a geçiş:** paket daha hafif olurdu, ama kuyruk kilitleri (`SKIP LOCKED`, advisory lock) ve JSONB sorguları yeniden yazılmalı. Risk yüksek. Reddedildi.
- **Docker ile sunucu kurdurmak:** kullanıcıdan Docker Desktop, WSL ve yönetici izni ister; "yalnızca uygulamam" hedefine aykırı. Reddedildi.
- **Masaüstü aracısı (önceki taslak, Yol B):** motor yerel olunca gereksiz kaldı. Çıkarıldı.
- **API ve worker'ı tek süreçte (thread) çalıştırmak:** daha az süreç demek, ama render/ffmpeg işi paneli yavaşlatır ve worker'ın SIGTERM ile düzgün durma mantığı süreç bekliyor. Ayrı alt süreçler seçildi.

## 5. Tasarımcının kararları (onaya açık)
- Gömülü veritabanı için `pgserver`. Planın ilk görevi bunu üç platformda doğrulayan bir deneme (spike). Başarısız olursa yedek: resmî PostgreSQL ikili dosyalarını pakete koymak.
- ffmpeg indirilmez, pakete dahil edilir. Çalışma anında ikili dosya indirmek güvenlik ve güvenilirlik açısından daha zayıf.
- Motor yalnızca uygulama açıkken çalışır; sistem tepsisi sonraki sürüme kaldı. Zamanlanmış işler uygulama kapalıyken bekler ve açılınca yetişir (zamanlayıcı bugün de kaçırılan zamanı sonraki turda yakalıyor).
- Eski kurulumlar (`server_url` kayıtlı) otomatik olarak `remote` modda kalır.
- Sürüm numarası v0.5.0.

## 6. Kurucuya bırakılanlar
- Araç tanıma sezgilerinin ayrıntısı; servisler için önerilen varsayılan model adları (sürümde güncel olanlar).
- Kurulum ekranının görsel ayrıntıları (mevcut kart ve modal stiline uyulacak).
- Günlük döndürme ve port seçimi yöntemi.
