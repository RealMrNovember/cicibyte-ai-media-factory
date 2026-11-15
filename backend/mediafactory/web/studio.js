// Studio: pick the story, the background clip and the caption look, preview it live, then produce.
"use strict";

const ST = {
  en: {
    studio: "Studio", studioSub: "Choose the story, background and caption style — then produce.",
    story: "Story", pickStory: "Choose a story…", background: "Background", random: "Random", none: "No clip (gradient)",
    upload: "Upload clip", licence: "Licence / note (optional)", sourceUrl: "Where it came from (optional)",
    uploading: "Uploading…", uploaded: "Clip added", captions: "Captions", font: "Font", size: "Size",
    textColor: "Text", highlight: "Highlight", outlineColor: "Outline", outline: "Outline width", shadow: "Shadow",
    uppercase: "UPPER CASE", words: "Words per line", position: "Position on screen", animation: "Animation",
    aspect: "Format", aspect916: "9:16 vertical (Shorts, Reels)", aspect169: "16:9 horizontal (YouTube video)",
    sfx: "Sound effects where the story mentions them (knocks, heartbeat, thunder…)", sfxVol: "Effects volume",
    anim_none: "None", anim_fade: "Fade", anim_pop: "Pop", anim_slide_up: "Slide up", anim_karaoke: "Word highlight (karaoke)",
    presets: "Presets", output: "Output", produce: "Produce", top: "Top", middle: "Middle", bottom: "Bottom",
    stockFind: "Find stock clips", stockTitle: "Free stock clips", stockSearch: "Search Coverr (e.g. parkour, foggy forest, rain window)",
    stockNoKey: "Add your free Coverr API key in Settings → Stock clips to search here. You can still import Mixkit links.",
    stockMixkit: "Or paste a Mixkit video link", stockImport: "Add to library", stockTopic: "Topic of the clip", stockAdded: "Clip added",
    stockMore: "More", stockLicence: "Coverr: free for commercial use, do not register in Content ID. Mixkit: free, no attribution needed.",
    pron: "Pronunciation", pronTitle: "Pronunciation dictionary", pronHelp: "Words the voice reads wrongly: write them the way they should sound. Only the voice changes — captions, titles and descriptions keep the original spelling. Whole words only; suffixes after an apostrophe stay (YouTube'da → Yu tüb'da).",
    pronWord: "Written", pronSay: "Say it as", pronLang: "Language", pronAny: "All", pronAdd: "Add a word", pronTry: "Listen with the English/Turkish voice above",
    realFrame: "Show the real frame", realFrameHelp: "This is rendered on the server with the same caption engine as the video, so outline and line breaks are exact.",
    previewHint: "Click the preview to place the captions.", myVoices: "My voices (clone)", addClone: "Clone a voice", cloneName: "Name", cloneNamePh: "e.g. My voice",
    cloneHint: "Upload 5–30 seconds of clear speech by one person, without music or background noise. The clone speaks both English and Turkish.",
    cloneConsent: "This is my voice, or I have the speaker's permission to clone it.", cloneAdded: "Voice added — choose it in the lists above", deleteClone: "Delete this voice",
    cloneNeedsConsent: "Tick the permission box first", addStory: "Add your own story", storyTitle: "Title", storyText: "Story text (paste it here)", orFile: "…or upload a file (.txt, .md, .pdf, .docx)", storyLang: "Language of the text", storyAdded: "Story added", storyDup: "This story was already in your list", needText: "Paste a text or choose a file", aiStory: "Write with AI", aiTitle: "Write a new story with AI", topic: "Topic or idea (optional)", topicPh: "e.g. noises from the attic of a village house", length: "Length", writing: "Writing… this can take a minute", allLangs: "All languages", noTags: "no topic", tagClip: "Topics of this clip", tagHelp: "When a video is made with a random background, clips tagged with the story's topic are used first.", clipTopics: "Topics (used for random backgrounds)", allTopics: "All topics", allSources: "All sources", music: "Music", noMusic: "No music", randomMusic: "Random from my library", ambiences: "Ambiences (royalty-free)", myTracks: "My tracks", musicVol: "Music volume", ducking: "Lower the music while the narrator speaks", uploadMusic: "Upload track", musicHint: "Upload music you are allowed to use (mp3, wav, ogg, m4a, flac).", voice: "Voice", voiceEn: "English voice", voiceTr: "Turkish voice", speed: "Speed", pitch: "Pitch (deeper ← → higher)", listen: "Listen", preparing: "Preparing (first time downloads the voice)…", male: "male", female: "female", neutral: "neutral voice", reviewFirst: "Show me the script before making the video", reviewScript: "Review script", editRerender: "Edit & remake", scriptTitle: "Title", narration: "Narration (read aloud)", ytDesc: "YouTube description", tagsComma: "Tags (comma separated)", wordsN: "words", approxSec: "≈ seconds", saveOnly: "Save", approveMake: "Approve & make video", saveRemake: "Save & remake video", draftsWaiting: "script(s) waiting for your review", remakeStarted: "Making the video again", short: "Short", medium: "Medium", long: "Long", noStories: "No stories yet — add a source and collect.",
    noClips: "No clips yet. Upload gameplay or stock footage you are allowed to use.", sure: "Delete this clip?",
  },
  tr: {
    studio: "Stüdyo", studioSub: "Hikâyeyi, arka planı ve altyazı stilini seç — sonra üret.",
    story: "Hikâye", pickStory: "Bir hikâye seç…", background: "Arka plan", random: "Rastgele", none: "Klip yok (gradyan)",
    upload: "Klip yükle", licence: "Lisans / not (isteğe bağlı)", sourceUrl: "Nereden geldi (isteğe bağlı)",
    uploading: "Yükleniyor…", uploaded: "Klip eklendi", captions: "Altyazı", font: "Yazı tipi", size: "Boyut",
    textColor: "Yazı", highlight: "Vurgu", outlineColor: "Kontur", outline: "Kontur kalınlığı", shadow: "Gölge",
    uppercase: "BÜYÜK HARF", words: "Satır başına kelime", position: "Ekrandaki konum", animation: "Animasyon",
    aspect: "Format", aspect916: "9:16 dikey (Shorts, Reels)", aspect169: "16:9 yatay (YouTube videosu)",
    sfx: "Hikâyede geçen yerlere ses efekti (kapı vuruşu, kalp atışı, gök gürültüsü…)", sfxVol: "Efekt seviyesi",
    anim_none: "Yok", anim_fade: "Belirme", anim_pop: "Zıplama", anim_slide_up: "Aşağıdan kayma", anim_karaoke: "Kelime vurgusu (karaoke)",
    presets: "Hazır stiller", output: "Çıktı", produce: "Üret", top: "Üst", middle: "Orta", bottom: "Alt",
    stockFind: "Stok klip bul", stockTitle: "Ücretsiz stok klipler", stockSearch: "Coverr'da ara (ör. parkour, sisli orman, yağmurlu pencere)",
    stockNoKey: "Burada arama yapmak için ücretsiz Coverr API anahtarını Ayarlar → Stok klipler'e ekle. Mixkit bağlantılarını yine de içe aktarabilirsin.",
    stockMixkit: "Ya da bir Mixkit video bağlantısı yapıştır", stockImport: "Kütüphaneye ekle", stockTopic: "Klibin konusu", stockAdded: "Klip eklendi",
    stockMore: "Daha fazla", stockLicence: "Coverr: ticari kullanım serbest, Content ID'ye kaydedilemez. Mixkit: ücretsiz, atıf gerekmez.",
    pron: "Telaffuz", pronTitle: "Telaffuz sözlüğü", pronHelp: "Sesin yanlış okuduğu kelimeleri nasıl okunması gerekiyorsa öyle yaz. Yalnızca ses değişir — altyazı, başlık ve açıklama orijinal yazımı korur. Yalnızca tam kelimeler; kesme işaretinden sonraki ek korunur (YouTube'da → Yu tüb'da).",
    pronWord: "Yazılışı", pronSay: "Böyle oku", pronLang: "Dil", pronAny: "Hepsi", pronAdd: "Kelime ekle", pronTry: "Yukarıda seçili İngilizce/Türkçe sesle dinle",
    realFrame: "Gerçek kareyi göster", realFrameHelp: "Bu kare sunucuda, videoyla aynı altyazı motoruyla çizildi; kontur ve satır kırılması birebir aynıdır.",
    previewHint: "Altyazıyı yerleştirmek için önizlemeye tıkla.", myVoices: "Kendi seslerim (klon)", addClone: "Ses klonla", cloneName: "Ad", cloneNamePh: "ör. Benim sesim",
    cloneHint: "Tek kişinin 5–30 saniyelik net konuşmasını yükle; müzik ya da arka plan gürültüsü olmasın. Klon hem Türkçe hem İngilizce konuşur.",
    cloneConsent: "Bu ses benim ya da sahibinden klonlamak için izin aldım.", cloneAdded: "Ses eklendi — yukarıdaki listelerden seçebilirsin", deleteClone: "Bu sesi sil",
    cloneNeedsConsent: "Önce izin kutusunu işaretle", addStory: "Kendi hikâyeni ekle", storyTitle: "Başlık", storyText: "Hikâye metni (buraya yapıştır)", orFile: "…ya da dosya yükle (.txt, .md, .pdf, .docx)", storyLang: "Metnin dili", storyAdded: "Hikâye eklendi", storyDup: "Bu hikâye zaten listende vardı", needText: "Bir metin yapıştır ya da dosya seç", aiStory: "AI ile yaz", aiTitle: "AI ile yeni hikâye yaz", topic: "Konu ya da fikir (isteğe bağlı)", topicPh: "ör. köy evinin tavanından gelen sesler", length: "Uzunluk", writing: "Yazılıyor… bir dakika sürebilir", allLangs: "Tüm diller", noTags: "konu yok", tagClip: "Bu klibin konuları", tagHelp: "Rastgele arka planla video üretilirken önce hikâyenin konusuyla etiketli klipler kullanılır.", clipTopics: "Konular (rastgele arka plan için)", allTopics: "Tüm konular", allSources: "Tüm kaynaklar", music: "Müzik", noMusic: "Müzik yok", randomMusic: "Kütüphanemden rastgele", ambiences: "Ambiyanslar (telifsiz)", myTracks: "Parçalarım", musicVol: "Müzik seviyesi", ducking: "Anlatıcı konuşurken müziği kıs", uploadMusic: "Parça yükle", musicHint: "Kullanma iznin olan müziği yükle (mp3, wav, ogg, m4a, flac).", voice: "Ses", voiceEn: "İngilizce ses", voiceTr: "Türkçe ses", speed: "Hız", pitch: "Ton (kalın ← → ince)", listen: "Dinle", preparing: "Hazırlanıyor (ilk seferde ses indirilir)…", male: "erkek", female: "kadın", neutral: "nötr ses", reviewFirst: "Videoyu yapmadan önce senaryoyu bana göster", reviewScript: "Senaryoyu incele", editRerender: "Düzenle ve yeniden üret", scriptTitle: "Başlık", narration: "Anlatım (seslendirilecek metin)", ytDesc: "YouTube açıklaması", tagsComma: "Etiketler (virgülle)", wordsN: "kelime", approxSec: "≈ saniye", saveOnly: "Kaydet", approveMake: "Onayla ve videoyu üret", saveRemake: "Kaydet ve videoyu yeniden üret", draftsWaiting: "senaryo incelemeni bekliyor", remakeStarted: "Video yeniden üretiliyor", short: "Kısa", medium: "Orta", long: "Uzun", noStories: "Henüz hikâye yok — kaynak ekleyip topla.",
    noClips: "Henüz klip yok. Kullanma iznin olan oyun ya da stok görüntüsü yükle.", sure: "Bu klip silinsin mi?",
  },
};
const st = (k) => (ST[lang] && ST[lang][k]) || t(k);

const FONT_CSS = {
  montserrat_black: ["Montserrat Black", "'Montserrat', sans-serif", 900],
  montserrat: ["Montserrat ExtraBold", "'Montserrat', sans-serif", 800],
  bebas: ["Bebas Neue", "'Bebas Neue', sans-serif", 400],
  roboto: ["Roboto Bold", "'Roboto', sans-serif", 700],
  open_sans: ["Open Sans Bold", "'Open Sans', sans-serif", 700],
  lato_black: ["Lato Black", "'Lato', sans-serif", 900],
  dejavu: ["DejaVu Sans Bold", "'DejaVu Sans', Verdana, sans-serif", 700],
};
const DEFAULT_STYLE = {
  font: "montserrat_black", size: 92, color: "#FFFFFF", highlight_color: "#FFD84D", outline_color: "#000000",
  outline: 7, shadow: 3, uppercase: true, words_per_cue: 3, position: 50, animation: "pop", aspect: "9:16",
};
const PRESETS = {
  "Classic": { ...DEFAULT_STYLE },
  "Karaoke": { ...DEFAULT_STYLE, animation: "karaoke", highlight_color: "#FFD84D", words_per_cue: 3 },
  "Bebas XL": { ...DEFAULT_STYLE, font: "bebas", size: 140, outline: 6, words_per_cue: 2, animation: "pop" },
  "Minimal": { ...DEFAULT_STYLE, font: "roboto", size: 66, outline: 4, shadow: 0, uppercase: false, position: 78, words_per_cue: 5, animation: "fade" },
  "Horror red": { ...DEFAULT_STYLE, color: "#FFFFFF", highlight_color: "#E0302A", animation: "karaoke", font: "lato_black" },
};

let studioState = null;
let previewTimer = null;

const DEFAULT_VOICE_SETTINGS = { en: "en_US-ryan-high", tr: "tr_TR-dfki-medium", speed: 1.0, pitch: 0 };
function loadVoice() {
  try { return { ...DEFAULT_VOICE_SETTINGS, ...JSON.parse(localStorage.getItem("mf_voice") || "{}") }; } catch { return { ...DEFAULT_VOICE_SETTINGS }; }
}
function saveVoice(v) { try { localStorage.setItem("mf_voice", JSON.stringify(v)); } catch { /* private mode */ } }

async function drawVoice() {
  const box = document.getElementById("voiceBox");
  if (!box) return;
  const s = studioState;
  s.voice = s.voice || loadVoice();
  if (!s.voiceList) {
    try {
      const r = await api("/api/voices");
      s.voiceList = r.voices; s.voiceCloning = !!r.cloning;
      // One-time move to the server's current default Turkish voice (e.g. Chatterbox when installed).
      let rev = null; try { rev = localStorage.getItem("mf_voice_rev"); } catch { /* private mode */ }
      if (rev !== "2" && r.defaults && r.defaults.tr) {
        s.voice.tr = r.defaults.tr; saveVoice(s.voice);
        try { localStorage.setItem("mf_voice_rev", "2"); } catch { /* private mode */ }
      }
      if (!s.voiceList.some((x) => x.id === s.voice.tr) && r.defaults) s.voice.tr = r.defaults.tr;
      if (!s.voiceList.some((x) => x.id === s.voice.en) && r.defaults) s.voice.en = r.defaults.en;
    } catch { s.voiceList = []; }
  }
  const v = s.voice;
  const opts = (language) => {
    const groups = {};
    s.voiceList.filter((x) => x.language === language || x.language === "any").forEach((x) => {
      const g = x.language === "any" ? st("myVoices") : x.accent; (groups[g] = groups[g] || []).push(x);
    });
    return Object.entries(groups).map(([acc, list]) => `<optgroup label="${esc(acc)}">${list.map((x) =>
      `<option value="${x.id}" ${v[language] === x.id ? "selected" : ""}>${esc(x.label)}${x.language === "any" ? "" : ` · ${st(x.gender)}`}${x.quality === "high" ? " · HD" : ""}</option>`).join("")}</optgroup>`).join("");
  };
  const chosenClones = [...new Set([v.en, v.tr].filter((id) => /^clone-/.test(id || "")))];
  const cloneRow = s.voiceCloning ? `<div class="row" style="margin-top:10px">
      <button class="btn" id="cloneAdd">🎙️ ${st("addClone")}</button>
      ${chosenClones.map((id) => `<button class="btn" data-clonedel="${id}">🗑 ${st("deleteClone")}: ${esc((s.voiceList.find((x) => x.id === id) || {}).label || id)}</button>`).join("")}
    </div>` : "";
  box.innerHTML = `<div class="grid g2">
      <div><label>${st("voiceEn")}</label><div class="row" style="flex-wrap:nowrap"><select data-vk="en">${opts("en")}</select><button class="btn" data-listen="en">▶</button></div></div>
      <div><label>${st("voiceTr")}</label><div class="row" style="flex-wrap:nowrap"><select data-vk="tr">${opts("tr")}</select><button class="btn" data-listen="tr">▶</button></div></div>
      <div><label>${st("speed")} <b class="val">${v.speed.toFixed(2)}×</b></label><input type="range" data-vk="speed" min="0.8" max="1.3" step="0.05" value="${v.speed}"></div>
      <div><label>${st("pitch")} <b class="val">${v.pitch > 0 ? "+" : ""}${v.pitch}</b></label><input type="range" data-vk="pitch" min="-4" max="4" step="1" value="${v.pitch}"></div>
    </div>${cloneRow}<div class="row" style="margin-top:8px"><button class="btn" id="pronOpen">📖 ${st("pronTitle")}</button></div>`;
  box.querySelector("#pronOpen").addEventListener("click", pronunciationDialog);
  const add = box.querySelector("#cloneAdd");
  add && add.addEventListener("click", cloneDialog);
  box.querySelectorAll("[data-clonedel]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm(st("sure"))) return;
    try {
      await api(`/api/voices/clones/${b.dataset.clonedel}`, { method: "DELETE" });
      s.voiceList = null; drawVoice();
    } catch (err) { toast(err.message, true); }
  }));
  box.querySelectorAll("[data-vk]").forEach((n) => n.addEventListener("input", () => {
    const k = n.dataset.vk;
    v[k] = n.type === "range" ? Number(n.value) : n.value;
    saveVoice(v);
    const lab = n.parentElement.querySelector(".val");
    if (lab) lab.textContent = k === "speed" ? `${v.speed.toFixed(2)}×` : `${v.pitch > 0 ? "+" : ""}${v.pitch}`;
  }));
  box.querySelectorAll("[data-listen]").forEach((b) => b.addEventListener("click", async () => {
    const lang2 = b.dataset.listen;
    b.disabled = true; b.textContent = "…"; toast(st("preparing"));
    try {
      const res = await fetch("/api/voices/preview", { method: "POST", headers: { "Content-Type": "application/json", "X-MF-Client": "panel" },
        body: JSON.stringify({ voice: v[lang2], speed: v.speed, pitch: v.pitch, language: lang2 }) });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
      const url = URL.createObjectURL(await res.blob());
      if (s.audio) s.audio.pause();
      s.audio = new Audio(url); s.audio.play();
    } catch (err) { toast(err.message, true); }
    b.disabled = false; b.textContent = "▶";
  }));
}

const DEFAULT_MUSIC = { track: "none", volume_db: -18, ducking: true, sfx: false, sfx_volume_db: -8 };
function loadMusic() {
  try { return { ...DEFAULT_MUSIC, ...JSON.parse(localStorage.getItem("mf_music") || "{}") }; } catch { return { ...DEFAULT_MUSIC }; }
}
function saveMusic(m) { try { localStorage.setItem("mf_music", JSON.stringify(m)); } catch { /* private mode */ } }

async function drawMusic(refresh = false) {
  const box = document.getElementById("musicBox");
  if (!box) return;
  const s = studioState;
  s.music = s.music || loadMusic();
  if (!s.musicList || refresh) { try { s.musicList = await api("/api/music"); } catch { s.musicList = { generated: [], tracks: [] }; } }
  const m = s.music, L = s.musicList;
  const known = ["none", "random", ...L.generated.map((g) => g.id), ...L.tracks.map((x) => x.name)];
  if (!known.includes(m.track)) m.track = "none";
  const opt = (v, label) => `<option value="${esc(v)}" ${m.track === v ? "selected" : ""}>${esc(label)}</option>`;
  box.innerHTML = `<div class="row" style="flex-wrap:nowrap"><select data-mk="track">
      ${opt("none", st("noMusic"))}${L.tracks.length ? opt("random", st("randomMusic")) : ""}
      <optgroup label="${esc(st("ambiences"))}">${L.generated.map((g) => opt(g.id, g.label[lang] || g.label.en)).join("")}</optgroup>
      ${L.tracks.length ? `<optgroup label="${esc(st("myTracks"))}">${L.tracks.map((x) => opt(x.name, x.name)).join("")}</optgroup>` : ""}
    </select><button class="btn" id="musicPlay">▶</button>
    ${L.tracks.some((x) => x.name === m.track) ? `<button class="btn danger" id="musicDel" title="${t("delete")}">×</button>` : ""}</div>
    <div class="grid g2" style="margin-top:6px">
      <div><label>${st("musicVol")} <b class="val">${m.volume_db} dB</b></label><input type="range" data-mk="volume_db" min="-35" max="-6" step="1" value="${m.volume_db}"></div>
      <div style="align-self:end"><label class="row"><input type="checkbox" data-mk="ducking" ${m.ducking ? "checked" : ""} style="width:auto"> ${st("ducking")}</label></div>
    </div><p class="muted small" style="margin:6px 0 0">${st("musicHint")}</p>
    <div class="grid g2" style="margin-top:10px">
      <div style="align-self:end"><label class="row"><input type="checkbox" data-mk="sfx" ${m.sfx ? "checked" : ""} style="width:auto"> 🔊 ${st("sfx")}</label></div>
      <div><label>${st("sfxVol")} <b class="val">${m.sfx_volume_db} dB</b></label><input type="range" data-mk="sfx_volume_db" min="-24" max="0" step="1" value="${m.sfx_volume_db}"></div>
    </div>`;
  box.querySelectorAll("[data-mk]").forEach((n) => n.addEventListener("input", () => {
    const k = n.dataset.mk;
    m[k] = n.type === "checkbox" ? n.checked : n.type === "range" ? Number(n.value) : n.value;
    saveMusic(m);
    if (k === "volume_db" || k === "sfx_volume_db") n.parentElement.querySelector(".val").textContent = `${m[k]} dB`;
    if (k === "track") drawMusic();
  }));
  box.querySelector("#musicPlay").addEventListener("click", () => {
    if (s.audio) s.audio.pause();
    const pick = m.track === "random" ? (L.tracks[0] || {}).name : m.track;
    if (!pick || pick === "none") return;
    s.audio = new Audio(`/api/music/${encodeURIComponent(pick)}/audio`);
    s.audio.volume = Math.min(1, Math.pow(10, (m.volume_db + 12) / 20));
    s.audio.play().catch((err) => toast(err.message, true));
  });
  const del = box.querySelector("#musicDel");
  del && del.addEventListener("click", async () => {
    if (!confirm(st("sure"))) return;
    try { await api(`/api/music/${encodeURIComponent(m.track)}`, { method: "DELETE" }); m.track = "none"; saveMusic(m); drawMusic(true); }
    catch (err) { toast(err.message, true); }
  });
}

async function pronunciationDialog() {
  let items;
  try { items = (await api("/api/pronunciations")).items; } catch (err) { return toast(err.message, true); }
  if (!items.length) items = [{ word: "", say: "", language: "any" }];
  const v = studioState.voice || loadVoice();
  const row = (r, i) => `<tr data-i="${i}"><td><input data-f="word" value="${esc(r.word)}" placeholder="CiciByte"></td>
      <td><input data-f="say" value="${esc(r.say)}" placeholder="Çiçi bayt"></td>
      <td><select data-f="language">${[["any", st("pronAny")], ["tr", "Türkçe"], ["en", "English"]].map(([k, l]) => `<option value="${k}" ${r.language === k ? "selected" : ""}>${l}</option>`).join("")}</select></td>
      <td><button class="btn small-btn" data-try="${i}" title="${esc(st("pronTry"))}">▶</button> <button class="btn danger small-btn" data-del="${i}">×</button></td></tr>`;
  const md = modal(`<h1>📖 ${st("pronTitle")}</h1><p class="muted small">${st("pronHelp")}</p>
    <table id="pronT"><tr><th>${st("pronWord")}</th><th>${st("pronSay")}</th><th>${st("pronLang")}</th><th></th></tr>${items.map(row).join("")}</table>
    <div class="row" style="margin-top:10px"><button class="btn" id="pronAdd">＋ ${st("pronAdd")}</button><span class="spacer"></span><button class="btn primary" id="pronSave">${t("save")}</button></div>`);
  const read = () => [...md.querySelectorAll("#pronT tr[data-i]")].map((tr) => Object.fromEntries([...tr.querySelectorAll("[data-f]")].map((n) => [n.dataset.f, n.value.trim()])));
  const redraw = (list) => { md.querySelector("#pronT").innerHTML = `<tr><th>${st("pronWord")}</th><th>${st("pronSay")}</th><th>${st("pronLang")}</th><th></th></tr>${list.map(row).join("")}`; bind(); };
  const bind = () => {
    md.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", () => { const l = read(); l.splice(Number(b.dataset.del), 1); redraw(l.length ? l : [{ word: "", say: "", language: "any" }]); }));
    md.querySelectorAll("[data-try]").forEach((b) => b.addEventListener("click", async () => {
      const r = read()[Number(b.dataset.try)];
      if (!r.say) return;
      const lng = r.language === "en" ? "en" : r.language === "tr" ? "tr" : (studioState.languages || ["tr"])[0];
      b.disabled = true; b.textContent = "…";
      try {
        const res = await fetch("/api/voices/preview", { method: "POST", headers: { "Content-Type": "application/json", "X-MF-Client": "panel" },
          body: JSON.stringify({ voice: v[lng], speed: v.speed, pitch: v.pitch, language: lng, text: r.say }) });
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
        new Audio(URL.createObjectURL(await res.blob())).play();
      } catch (err) { toast(err.message, true); }
      b.disabled = false; b.textContent = "▶";
    }));
  };
  bind();
  md.querySelector("#pronAdd").addEventListener("click", () => redraw([...read(), { word: "", say: "", language: "any" }]));
  md.querySelector("#pronSave").addEventListener("click", async () => {
    try { await api("/api/pronunciations", { method: "PUT", body: { items: read().filter((r) => r.word && r.say) } }); md.remove(); toast(t("saved")); }
    catch (err) { toast(err.message, true); }
  });
}

function cloneDialog() {
  const md = modal(`<h1>🎙️ ${st("addClone")}</h1><form id="cvf">
    <p class="muted" style="margin-top:0">${st("cloneHint")}</p>
    <label>${st("cloneName")}</label><input name="label" maxlength="60" placeholder="${esc(st("cloneNamePh"))}">
    <label>Audio (wav, mp3, m4a, ogg, flac, webm)</label><input type="file" name="file" accept="audio/*" required>
    <label class="row" style="gap:8px;align-items:flex-start;margin-top:12px;font-weight:400"><input type="checkbox" name="consent" value="true" style="width:auto;margin-top:3px"> ${st("cloneConsent")}</label>
    <div class="progress" hidden><div></div></div>
    <div class="row" style="margin-top:14px"><button class="btn primary">${st("addClone")}</button></div></form>`);
  md.querySelector("#cvf").addEventListener("submit", (e) => {
    e.preventDefault();
    const fd = new FormData(e.target), bar = md.querySelector(".progress"), btn = md.querySelector("button.primary");
    if (!fd.get("consent")) return toast(st("cloneNeedsConsent"), true);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/voices/clones");
    xhr.setRequestHeader("X-MF-Client", "panel");
    bar.hidden = false; btn.disabled = true; btn.textContent = st("uploading");
    xhr.upload.onprogress = (ev) => { if (ev.lengthComputable) bar.firstElementChild.style.width = `${(ev.loaded / ev.total) * 100}%`; };
    xhr.onload = () => {
      let d = null; try { d = JSON.parse(xhr.responseText); } catch { /* not json */ }
      if (xhr.status !== 201) { btn.disabled = false; btn.textContent = st("addClone"); return toast((d && d.detail) || xhr.statusText, true); }
      md.remove(); toast(st("cloneAdded"));
      studioState.voiceList = null; drawVoice();
    };
    xhr.onerror = () => { btn.disabled = false; btn.textContent = st("addClone"); toast(t("offline"), true); };
    xhr.send(fd);
  });
}

function uploadMusicDialog() {
  const md = modal(`<h1>${st("uploadMusic")}</h1><form id="umf">
    <label>Audio (mp3, wav, ogg, m4a, flac)</label><input type="file" name="file" accept="audio/*" required>
    <label>${st("licence")}</label><input name="licence" placeholder="Pixabay Music / YouTube Audio Library / own recording">
    <div class="progress" hidden><div></div></div>
    <div class="row" style="margin-top:14px"><button class="btn primary">${st("uploadMusic")}</button></div></form>`);
  md.querySelector("#umf").addEventListener("submit", (e) => {
    e.preventDefault();
    const fd = new FormData(e.target), bar = md.querySelector(".progress"), btn = md.querySelector("button.primary");
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/music");
    xhr.setRequestHeader("X-MF-Client", "panel");
    bar.hidden = false; btn.disabled = true; btn.textContent = st("uploading");
    xhr.upload.onprogress = (ev) => { if (ev.lengthComputable) bar.firstElementChild.style.width = `${(ev.loaded / ev.total) * 100}%`; };
    xhr.onload = async () => {
      let d = null; try { d = JSON.parse(xhr.responseText); } catch { /* not json */ }
      if (xhr.status !== 201) { btn.disabled = false; btn.textContent = st("uploadMusic"); return toast((d && d.detail) || xhr.statusText, true); }
      md.remove(); toast(st("uploaded"));
      studioState.music = { ...(studioState.music || loadMusic()), track: d.name }; saveMusic(studioState.music); drawMusic(true);
    };
    xhr.onerror = () => { btn.disabled = false; btn.textContent = st("uploadMusic"); toast(t("offline"), true); };
    xhr.send(fd);
  });
}

function loadStyle() {
  try { return { ...DEFAULT_STYLE, ...JSON.parse(localStorage.getItem("mf_style") || "{}") }; } catch { return { ...DEFAULT_STYLE }; }
}
function saveStyle(s) { try { localStorage.setItem("mf_style", JSON.stringify(s)); } catch { /* private mode */ } }

async function studio(el) {
  clearInterval(previewTimer);
  const pre = Number((location.hash.split("/")[1] || "").split("?")[0]) || null;
  const [items, clips, topics] = await Promise.all([api("/api/items?limit=200"), api("/api/backgrounds"), api("/api/items/topics")]);
  const prev = studioState || {};
  studioState = {
    items: items.items, clips: clips.items, topics, style: prev.style || loadStyle(),
    itemId: pre || prev.itemId || (items.items[0] && items.items[0].id) || null,
    langFilter: prev.langFilter || "", topic: prev.topic || "", sourceFilter: prev.sourceFilter || "",
    background: prev.background || "random", languages: prev.languages || ["en"], seconds: prev.seconds || 50,
  };
  el.innerHTML = `<h1>${st("studio")}</h1><p class="sub">${st("studioSub")}</p>
    <div class="studio">
      <div class="studio-controls">
        <div class="card"><div class="row"><h3>1 · ${st("story")}</h3><span class="spacer"></span>
          <button class="btn" id="aiStory">✨ ${st("aiStory")}</button><button class="btn" id="addStory">＋ ${st("addStory")}</button></div><div id="storyBox"></div></div>
        <div class="card"><div class="row"><h3>2 · ${st("background")}</h3><span class="spacer"></span>
          <button class="btn" id="upBtn">＋ ${st("upload")}</button><button class="btn" id="stockBtn">🔎 ${st("stockFind")}</button></div><div id="bgBox"></div></div>
        <div class="card"><h3>3 · ${st("captions")}</h3><div id="capBox"></div></div>
        <div class="card"><h3>4 · ${st("voice")}</h3><div id="voiceBox"></div></div>
        <div class="card"><div class="row"><h3>5 · ${st("music")}</h3><span class="spacer"></span>
          <button class="btn" id="upMusic">＋ ${st("uploadMusic")}</button></div><div id="musicBox"></div></div>
        <div class="card"><h3>6 · ${st("output")}</h3><div id="outBox"></div></div>
      </div>
      <div class="studio-preview"><div class="phone" id="phone"><div class="phone-bg" id="phoneBg"></div>
        <div class="cap" id="cap"></div></div><p class="muted small" style="text-align:center">${st("previewHint")}</p>
        <div style="text-align:center"><button class="btn" id="realFrame">🎯 ${st("realFrame")}</button></div></div>
    </div>`;
  drawStory(); drawBackgrounds(); drawCaptions(); drawVoice(); drawMusic(); drawOutput(); drawPreview();
  document.getElementById("upMusic").addEventListener("click", uploadMusicDialog);
  document.getElementById("upBtn").addEventListener("click", uploadDialog);
  document.getElementById("stockBtn").addEventListener("click", stockDialog);
  document.getElementById("realFrame").addEventListener("click", showRealFrame);
  document.getElementById("aiStory").addEventListener("click", () => aiStoryDialog(async (item) => {
    Object.assign(studioState, { itemId: item.id, langFilter: item.language || "", topic: "", sourceFilter: "" }); await reloadStories();
  }));
  document.getElementById("addStory").addEventListener("click", () => addStoryDialog(async (item) => {
    Object.assign(studioState, { itemId: item.id, topic: "", sourceFilter: "" }); await reloadStories();
  }));
  document.getElementById("phone").addEventListener("click", (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    setStyle({ position: Math.max(8, Math.min(92, Math.round(((e.clientY - r.top) / r.height) * 100))) });
    drawCaptions();
  });
}

function setStyle(patch) { Object.assign(studioState.style, patch); saveStyle(studioState.style); drawPreview(); }

const TOPICS = {
  stories: ["Stories & fiction", "Hikâye ve kurgu"], horror: ["Horror & mystery", "Korku ve gizem"],
  drama: ["Real-life drama", "Gerçek hayat dramları"], humor: ["Funny & fails", "Komik ve talihsiz"],
  curious: ["Curiosities", "İlginç bilgiler"], science: ["Science & space", "Bilim ve uzay"],
  history: ["History & culture", "Tarih ve kültür"], tech: ["Technology", "Teknoloji"], news: ["News & world", "Haber ve dünya"],
  manual: ["Mine / AI-written", "Elle / AI ile"], other: ["Other sources", "Diğer kaynaklar"],
};
const topicLabel = (k) => (TOPICS[k] || [k, k])[lang === "tr" ? 1 : 0];

function storyQuery(s) {
  const q = new URLSearchParams({ limit: "200" });
  if (s.langFilter) q.set("language", s.langFilter);
  if (s.topic) q.set("category", s.topic);
  if (s.sourceFilter) q.set("source_id", s.sourceFilter);
  return q.toString();
}

async function reloadStories() {
  const s = studioState;
  const lq = s.langFilter ? `?language=${s.langFilter}` : "";
  [s.items, s.topics] = await Promise.all([api(`/api/items?${storyQuery(s)}`).then((r) => r.items), api(`/api/items/topics${lq}`)]);
  drawStory(); drawPreview();
}

function drawStory() {
  const s = studioState, box = document.getElementById("storyBox");
  const lf = s.langFilter || "", tp = s.topic || "", sf = String(s.sourceFilter || "");
  const topics = (s.topics && s.topics.topics) || [];
  const srcs = ((s.topics && s.topics.sources) || []).filter((x) => !tp || x.category === tp);
  const chip = (attr, v, label, on) => `<button class="btn small-btn ${on ? "primary" : ""}" ${attr}="${esc(v)}">${label}</button>`;
  const filters = `<div class="row" style="margin-bottom:8px">${[["", st("allLangs")], ["en", "English"], ["tr", "Türkçe"]].map(([v, l]) => chip("data-lf", v, l, lf === v)).join("")}</div>
    <div class="row" style="margin-bottom:8px">${chip("data-tp", "", st("allTopics"), !tp)}${topics.map((x) => chip("data-tp", x.key, `${esc(topicLabel(x.key))} <span class="muted">${x.count}</span>`, tp === x.key)).join("")}</div>
    ${srcs.length > 1 ? `<select id="srcFilter" style="margin-bottom:10px"><option value="">${st("allSources")}</option>${srcs.map((x) => `<option value="${x.id}" ${sf === String(x.id) ? "selected" : ""}>${esc(x.name)} (${x.count})</option>`).join("")}</select>` : ""}`;
  const list = s.items;
  const bind = () => {
    box.querySelectorAll("[data-lf]").forEach((b) => b.addEventListener("click", () => { s.langFilter = b.dataset.lf; s.topic = ""; s.sourceFilter = ""; reloadStories(); }));
    box.querySelectorAll("[data-tp]").forEach((b) => b.addEventListener("click", () => { s.topic = b.dataset.tp; s.sourceFilter = ""; reloadStories(); }));
    const sel = box.querySelector("#srcFilter");
    sel && sel.addEventListener("change", () => { s.sourceFilter = sel.value; reloadStories(); });
  };
  if (!list.length) { box.innerHTML = filters + `<p class="muted">${st("noStories")}</p>`; return bind(); }
  const cur = list.find((i) => i.id === s.itemId) || list[0];
  s.itemId = cur.id;
  box.innerHTML = filters + `<select id="story">${list.map((i) => `<option value="${i.id}" ${i.id === cur.id ? "selected" : ""}>${(i.language || "en").toUpperCase()} · ${esc(i.title)}</option>`).join("")}</select>
    <p class="muted small clip3" style="margin:10px 0 0">${esc(cur.text)}</p>
    <p class="muted small" style="margin:6px 0 0"><span class="pill">${esc(topicLabel(cur.category))}</span> ${cur.source_name ? esc(cur.source_name) + " · " : ""}${cur.chars} ${t("chars")} · <span class="pill">${esc(cur.rights_status)}</span></p>`;
  document.getElementById("story").addEventListener("change", (e) => { s.itemId = Number(e.target.value); drawStory(); drawPreview(); });
  bind();
}

function aiStoryDialog(onAdded) {
  const m = modal(`<h1>${st("aiTitle")}</h1><form id="aif">
    <label>${st("topic")}</label><input name="topic" maxlength="500" placeholder="${esc(st("topicPh"))}">
    <div class="grid g2"><div><label>${t("languages")}</label><select name="language"><option value="tr">Türkçe</option><option value="en">English</option></select></div>
    <div><label>${st("length")}</label><select name="words"><option value="350">${st("short")}</option><option value="600" selected>${st("medium")}</option><option value="1000">${st("long")}</option></select></div></div>
    <div class="row" style="margin-top:14px"><button class="btn primary">✨ ${st("aiStory")}</button></div></form>`);
  m.querySelector("#aif").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target, btn = f.querySelector("button.primary");
    btn.disabled = true; btn.textContent = st("writing");
    try {
      const r = await api("/api/items/ai-story", { method: "POST", body: { topic: f.topic.value, language: f.language.value, words: Number(f.words.value) } });
      m.remove(); toast(st("storyAdded"));
      if (onAdded) await onAdded(r.item);
    } catch (err) { toast(err.message, true); btn.disabled = false; btn.textContent = "✨ " + st("aiStory"); }
  });
}

function addStoryDialog(onAdded) {
  const m = modal(`<h1>${st("addStory")}</h1><form id="storyf">
    <label>${st("storyTitle")}</label><input name="title" maxlength="500">
    <label>${st("storyText")}</label><textarea name="text" style="min-height:220px"></textarea>
    <label>${st("orFile")}</label><input type="file" name="file" accept=".txt,.md,.pdf,.docx">
    <label>${st("storyLang")}</label><select name="language"><option value="en">English</option><option value="tr" ${lang === "tr" ? "selected" : ""}>Türkçe</option></select>
    <div class="row" style="margin-top:14px"><button class="btn primary">${t("add")}</button></div></form>`);
  m.querySelector("#storyf").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target, file = f.file.files[0], text = f.text.value.trim();
    if (!file && !text) return toast(st("needText"), true);
    try {
      let r;
      if (file) {
        const fd = new FormData();
        fd.append("file", file); fd.append("language", f.language.value);
        if (f.title.value.trim()) fd.append("title", f.title.value.trim());
        r = await api("/api/items/manual/upload", { method: "POST", body: fd });
      } else {
        r = await api("/api/items/manual", { method: "POST", body: { title: f.title.value.trim() || null, text, language: f.language.value, rights_status: "user_owned" } });
      }
      m.remove(); toast(r.duplicate ? st("storyDup") : st("storyAdded"));
      if (onAdded) await onAdded(r.item);
    } catch (err) { toast(err.message, true); }
  });
}

function drawBackgrounds() {
  const s = studioState, box = document.getElementById("bgBox");
  const tile = (key, inner, title = "", del = false) => `<div class="bg-tile ${s.background === key ? "on" : ""}" data-bg="${esc(key)}" title="${esc(title)}">${inner}
      ${del ? `<button class="bg-del" data-delbg="${esc(key)}" title="${t("delete")}">×</button>` : ""}</div>`;
  box.innerHTML = `<div class="bg-grid">
      ${tile("random", `<div class="bg-icon">🎲</div><span>${st("random")}</span>`)}
      ${tile("none", `<div class="bg-icon grad"></div><span>${st("none")}</span>`)}
      ${s.clips.map((c) => tile(c.name, `<img loading="lazy" src="/api/backgrounds/${encodeURIComponent(c.name)}/thumb"><span>${esc(c.name)}</span>
        <span class="clip-tags">${(c.tags || []).map((x) => esc(topicLabel(x))).join(" · ") || `<i>${st("noTags")}</i>`}</span>
        <button class="bg-tag" data-tagbg="${esc(c.name)}" title="${esc(st("tagClip"))}">🏷</button>`,
        `${c.licence}${c.source ? " · " + c.source : ""}`, true)).join("")}
    </div>${s.clips.length ? "" : `<p class="muted small">${st("noClips")}</p>`}`;
  box.querySelectorAll("[data-bg]").forEach((n) => n.addEventListener("click", (e) => {
    if (e.target.closest("[data-delbg]") || e.target.closest("[data-tagbg]")) return;
    s.background = n.dataset.bg; drawBackgrounds(); drawPreview();
  }));
  box.querySelectorAll("[data-tagbg]").forEach((n) => n.addEventListener("click", () => {
    const clip = s.clips.find((c) => c.name === n.dataset.tagbg);
    tagDialog(clip.tags || [], async (tags) => {
      await api(`/api/backgrounds/${encodeURIComponent(clip.name)}/tags`, { method: "PUT", body: { tags } });
      s.clips = (await api("/api/backgrounds")).items; drawBackgrounds();
    }, clip.name);
  }));
  box.querySelectorAll("[data-delbg]").forEach((n) => n.addEventListener("click", async () => {
    if (!confirm(st("sure"))) return;
    try {
      await api(`/api/backgrounds/${encodeURIComponent(n.dataset.delbg)}`, { method: "DELETE" });
      if (s.background === n.dataset.delbg) s.background = "random";
      s.clips = (await api("/api/backgrounds")).items; drawBackgrounds(); drawPreview();
    } catch (err) { toast(err.message, true); }
  }));
}

function tagChecks(selected) {
  return `<div class="row">${Object.keys(TOPICS).filter((k) => k !== "other").map((k) => `<label class="row"><input type="checkbox" name="tag" value="${k}" ${selected.includes(k) ? "checked" : ""} style="width:auto"> ${esc(topicLabel(k))}</label>`).join("")}</div>`;
}

function tagDialog(selected, onSave, title) {
  const m = modal(`<h1>🏷 ${esc(title || st("tagClip"))}</h1><p class="muted small">${st("tagHelp")}</p><form id="tagf">${tagChecks(selected)}
    <div class="row" style="margin-top:14px"><button class="btn primary">${t("save")}</button></div></form>`);
  m.querySelector("#tagf").addEventListener("submit", async (e) => {
    e.preventDefault();
    const tags = [...e.target.querySelectorAll("[name=tag]:checked")].map((x) => x.value);
    try { await onSave(tags); m.remove(); toast(t("saved")); } catch (err) { toast(err.message, true); }
  });
}

async function stockDialog() {
  const status = await api("/api/stock").catch(() => ({ coverr: false }));
  const topicSel = `<select name="topic">${Object.keys(TOPICS).filter((k) => k !== "other").map((k) => `<option value="${k}" ${k === "horror" ? "selected" : ""}>${esc(topicLabel(k))}</option>`).join("")}</select>`;
  const m = modal(`<h1>🔎 ${st("stockTitle")}</h1>
    <div class="grid g2" style="align-items:end"><div><label>${st("stockTopic")}</label>${topicSel}</div><div class="muted small">${st("stockLicence")}</div></div>
    ${status.coverr ? `<form id="sq" class="row" style="margin-top:10px;flex-wrap:nowrap"><input name="q" placeholder="${esc(st("stockSearch"))}" required><button class="btn primary">🔎</button></form>
      <div id="sres" class="bg-grid" style="margin-top:10px"></div><div class="row"><button class="btn" id="smore" hidden>${st("stockMore")}</button><span class="spacer"></span>
      <a href="#" id="coverrLink" class="muted small">Videos by Coverr ↗</a></div>` : `<p class="muted small">${st("stockNoKey")}</p>`}
    <form id="mk" style="margin-top:14px"><label>${st("stockMixkit")}</label><div class="row" style="flex-wrap:nowrap">
      <input name="url" placeholder="https://mixkit.co/free-stock-video/…-12345/" required><button class="btn">${st("stockImport")}</button></div></form>`);
  const tags = () => [m.querySelector("[name=topic]").value];
  const added = async (d) => { toast(`${st("stockAdded")}: ${d.name}`); studioState.clips = (await api("/api/backgrounds")).items; drawBackgrounds(); };
  m.querySelector("#mk").addEventListener("submit", async (e) => {
    e.preventDefault();
    const b = e.target.querySelector("button"); b.disabled = true; b.textContent = "…";
    try { await added(await api("/api/stock/mixkit", { method: "POST", body: { url: e.target.url.value.trim(), tags: tags() } })); e.target.reset(); }
    catch (err) { toast(err.message, true); }
    b.disabled = false; b.textContent = st("stockImport");
  });
  if (!status.coverr) return;
  m.querySelector("#coverrLink").addEventListener("click", (e) => { e.preventDefault(); openExternal("https://coverr.co"); });
  let q = "", page = 0;
  const res = m.querySelector("#sres"), more = m.querySelector("#smore");
  const load = async (append) => {
    try {
      const r = await api(`/api/stock/coverr?q=${encodeURIComponent(q)}&page=${page}`);
      const html = r.items.map((c) => `<div class="bg-tile" title="${esc(c.title)}"><img loading="lazy" src="${esc(c.thumbnail || "")}"
          data-prev="${esc(c.preview || "")}"><span>${esc(c.title)} · ${Math.round(c.duration || 0)}s${c.vertical ? " · 9:16" : ""}</span>
          <button class="btn small-btn" data-imp="${esc(c.id)}" style="position:absolute;right:6px;bottom:28px">＋</button></div>`).join("");
      res.innerHTML = (append ? res.innerHTML : "") + (html || `<p class="muted">${t("noData")}</p>`);
      more.hidden = page + 1 >= (r.pages || 1);
      res.querySelectorAll("[data-imp]").forEach((b) => { b.onclick = async () => {
        b.disabled = true; b.textContent = "…";
        try { await added(await api(`/api/stock/coverr/${encodeURIComponent(b.dataset.imp)}/import`, { method: "POST", body: { tags: tags() } })); b.textContent = "✓"; }
        catch (err) { toast(err.message, true); b.disabled = false; b.textContent = "＋"; }
      }; });
      res.querySelectorAll("img[data-prev]").forEach((img) => { img.onmouseenter = () => {
        if (!img.dataset.prev) return;
        const v = document.createElement("video"); v.src = img.dataset.prev; v.muted = true; v.autoplay = true; v.loop = true; v.style.cssText = img.style.cssText;
        v.className = img.className; v.setAttribute("style", "width:100%;aspect-ratio:9/16;object-fit:cover"); img.replaceWith(v);
      }; });
    } catch (err) { toast(err.message, true); }
  };
  m.querySelector("#sq").addEventListener("submit", (e) => { e.preventDefault(); q = e.target.q.value.trim(); page = 0; load(false); });
  more.addEventListener("click", () => { page += 1; load(true); });
}

function uploadDialog() {
  const m = modal(`<h1>${st("upload")}</h1><form id="upf">
    <label>Video (mp4, mov, mkv, webm)</label><input type="file" name="file" accept="video/*" required>
    <label>${st("licence")}</label><input name="licence" placeholder="Mixkit Free License / Coverr / own recording">
    <label>${st("sourceUrl")}</label><input name="source" placeholder="https://mixkit.co/...">
    <label>${st("clipTopics")}</label>${tagChecks([])}
    <div class="progress" hidden><div></div></div>
    <div class="row" style="margin-top:14px"><button class="btn primary">${st("upload")}</button></div></form>`);
  m.querySelector("#upf").addEventListener("submit", (e) => {
    e.preventDefault();
    const fd = new FormData(e.target), bar = m.querySelector(".progress"), btn = m.querySelector("button.primary");
    fd.delete("tag"); fd.set("tags", [...e.target.querySelectorAll("[name=tag]:checked")].map((x) => x.value).join(","));
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/backgrounds");
    xhr.setRequestHeader("X-MF-Client", "panel");
    bar.hidden = false; btn.disabled = true; btn.textContent = st("uploading");
    xhr.upload.onprogress = (ev) => { if (ev.lengthComputable) bar.firstElementChild.style.width = `${(ev.loaded / ev.total) * 100}%`; };
    xhr.onload = async () => {
      let d = null; try { d = JSON.parse(xhr.responseText); } catch { /* not json */ }
      if (xhr.status !== 201) { btn.disabled = false; btn.textContent = st("upload"); return toast((d && d.detail) || xhr.statusText, true); }
      m.remove(); toast(st("uploaded"));
      studioState.clips = (await api("/api/backgrounds")).items; studioState.background = d.name; drawBackgrounds(); drawPreview();
    };
    xhr.onerror = () => { btn.disabled = false; btn.textContent = st("upload"); toast(t("offline"), true); };
    xhr.send(fd);
  });
}

function drawCaptions() {
  const y = studioState.style, box = document.getElementById("capBox");
  const range = (k, min, max, label) => `<div><label>${label} <b class="val">${y[k]}</b></label><input type="range" data-k="${k}" min="${min}" max="${max}" value="${y[k]}"></div>`;
  const color = (k, label) => `<div><label>${label}</label><input type="color" data-k="${k}" value="${y[k]}"></div>`;
  box.innerHTML = `<label>${st("presets")}</label><div class="row">${Object.keys(PRESETS).map((p) => `<button class="btn small-btn" data-preset="${esc(p)}">${esc(p)}</button>`).join("")}</div>
    <div class="grid g2">
      <div><label>${st("font")}</label><select data-k="font">${Object.entries(FONT_CSS).map(([k, v]) => `<option value="${k}" ${y.font === k ? "selected" : ""}>${esc(v[0])}</option>`).join("")}</select></div>
      <div><label>${st("aspect")}</label><select data-k="aspect"><option value="9:16" ${y.aspect !== "16:9" ? "selected" : ""}>${st("aspect916")}</option><option value="16:9" ${y.aspect === "16:9" ? "selected" : ""}>${st("aspect169")}</option></select></div>
      <div><label>${st("animation")}</label><select data-k="animation">${["none", "fade", "pop", "slide_up", "karaoke"].map((a) => `<option value="${a}" ${y.animation === a ? "selected" : ""}>${st("anim_" + a)}</option>`).join("")}</select></div>
      ${range("size", 36, 180, st("size"))}${range("words_per_cue", 1, 7, st("words"))}
      ${range("outline", 0, 14, st("outline"))}${range("shadow", 0, 10, st("shadow"))}
    </div>
    <div class="grid g3c">${color("color", st("textColor"))}${color("highlight_color", st("highlight"))}${color("outline_color", st("outlineColor"))}</div>
    <div>${range("position", 8, 92, st("position") + " %")}
      <div class="row"><button class="btn small-btn" data-pos="18">${st("top")}</button><button class="btn small-btn" data-pos="50">${st("middle")}</button><button class="btn small-btn" data-pos="78">${st("bottom")}</button></div></div>
    <label class="row" style="margin-top:12px"><input type="checkbox" data-k="uppercase" ${y.uppercase ? "checked" : ""} style="width:auto"> ${st("uppercase")}</label>`;
  box.querySelectorAll("[data-k]").forEach((n) => n.addEventListener("input", () => {
    const k = n.dataset.k;
    const v = n.type === "checkbox" ? n.checked : n.type === "range" ? Number(n.value) : n.type === "color" ? n.value.toUpperCase() : n.value;
    setStyle({ [k]: v });
    const lab = n.parentElement.querySelector(".val"); if (lab) lab.textContent = v;
  }));
  box.querySelectorAll("[data-preset]").forEach((n) => n.addEventListener("click", () => { studioState.style = { ...PRESETS[n.dataset.preset], aspect: studioState.style.aspect || "9:16" }; saveStyle(studioState.style); drawCaptions(); drawPreview(); }));
  box.querySelectorAll("[data-pos]").forEach((n) => n.addEventListener("click", () => { setStyle({ position: Number(n.dataset.pos) }); drawCaptions(); }));
}

function drawOutput() {
  const s = studioState, box = document.getElementById("outBox");
  box.innerHTML = `<label>${t("languages")}</label><div class="row">
      <label class="row"><input type="checkbox" data-lang="en" ${s.languages.includes("en") ? "checked" : ""} style="width:auto"> English</label>
      <label class="row"><input type="checkbox" data-lang="tr" ${s.languages.includes("tr") ? "checked" : ""} style="width:auto"> Türkçe</label></div>
    <label>${t("seconds")} <b class="val">${s.seconds}</b></label><input type="range" id="secs" min="15" max="170" step="5" value="${s.seconds}">
    <label class="row" style="margin-top:14px"><input type="checkbox" id="reviewFirst" ${s.reviewFirst ? "checked" : ""} style="width:auto"> ${st("reviewFirst")}</label>
    <div class="row" style="margin-top:16px"><button class="btn primary big" id="produce">▶ ${st("produce")}</button></div>`;
  document.getElementById("reviewFirst").addEventListener("change", (e) => { s.reviewFirst = e.target.checked; });
  box.querySelectorAll("[data-lang]").forEach((n) => n.addEventListener("change", () => {
    s.languages = [...box.querySelectorAll("[data-lang]")].filter((x) => x.checked).map((x) => x.dataset.lang);
  }));
  document.getElementById("secs").addEventListener("input", (e) => { s.seconds = Number(e.target.value); e.target.previousElementSibling.querySelector(".val").textContent = s.seconds; });
  document.getElementById("produce").addEventListener("click", async (e) => {
    if (!s.itemId) return toast(st("noStories"), true);
    if (!s.languages.length) return toast(t("languages"), true);
    e.target.disabled = true;
    try {
      await api(`/api/items/${s.itemId}/make`, { method: "POST", body: { languages: s.languages, seconds: s.seconds, background: s.background, style: s.style, review_script: !!s.reviewFirst, voice: s.voice || loadVoice(), music: s.music || loadMusic() } });
      toast(t("makeStarted")); location.hash = "#production";
    } catch (err) { toast(err.message, true); e.target.disabled = false; }
  });
}

async function scriptEditor(jobId) {
  const j = await api(`/api/jobs/${jobId}`);
  const sc0 = j.script || { title: j.title || "", narration: "", description: "", tags: [] };
  const draft = j.status === "script_draft";
  const m = modal(`<h1>✎ ${draft ? st("reviewScript") : st("editRerender")}</h1><p class="muted small">#${j.id} · ${esc((j.language || "").toUpperCase())}</p>
    <form id="scf"><label>${st("scriptTitle")}</label><input name="title" maxlength="100" required value="${esc(sc0.title || "")}">
    <label>${st("narration")} <span class="muted" id="wc"></span></label><textarea name="narration" required style="min-height:280px">${esc(sc0.narration || "")}</textarea>
    <label>${st("ytDesc")}</label><textarea name="description" style="min-height:80px">${esc(sc0.description || "")}</textarea>
    <label>${st("tagsComma")}</label><input name="tags" value="${esc((sc0.tags || []).join(", "))}">
    <div class="row" style="margin-top:14px"><button class="btn primary" data-render="1">▶ ${draft ? st("approveMake") : st("saveRemake")}</button>
      <button class="btn" data-render="0">${st("saveOnly")}</button></div></form>`);
  const f = m.querySelector("#scf");
  const count = () => { const n = f.narration.value.trim().split(/\s+/).filter(Boolean).length; m.querySelector("#wc").textContent = `${n} ${st("wordsN")} · ${Math.round(n / 2.5)} ${st("approxSec")}`; };
  f.narration.addEventListener("input", count); count();
  f.querySelectorAll("[data-render]").forEach((b) => b.addEventListener("click", async (e) => {
    e.preventDefault();
    if (!f.reportValidity()) return;
    const renderIt = b.dataset.render === "1";
    try {
      await api(`/api/jobs/${jobId}/script`, { method: "POST", body: { title: f.title.value, narration: f.narration.value, description: f.description.value,
        tags: f.tags.value.split(",").map((x) => x.trim()).filter(Boolean), render: renderIt } });
      m.remove(); toast(renderIt ? st("remakeStarted") : t("saved"));
      if (renderIt) location.hash = "#production"; else render();
    } catch (err) { toast(err.message, true); }
  }));
}

function sampleWords() {
  const it = studioState.items.find((i) => i.id === studioState.itemId);
  const words = ((it && it.text) || "The house was quiet until the door opened by itself at three in the morning").split(/\s+/).filter(Boolean);
  return words.slice(0, 60);
}

function upperFor(text) {
  const tr = studioState.languages[0] === "tr";
  return (tr ? text.replace(/i/g, "İ").replace(/ı/g, "I") : text).toUpperCase();
}

function drawPreview() {
  clearInterval(previewTimer);
  const s = studioState, y = s.style, phone = document.getElementById("phone"), cap = document.getElementById("cap"), bg = document.getElementById("phoneBg");
  if (!phone) return;
  const clip = s.background === "random" ? (s.clips[0] && s.clips[0].name) : s.background === "none" ? null : s.background;
  const want = clip ? `/api/backgrounds/${encodeURIComponent(clip)}/video` : "";
  if (bg.dataset.src !== want) {
    bg.dataset.src = want;
    bg.innerHTML = clip ? `<video src="${want}" poster="/api/backgrounds/${encodeURIComponent(clip)}/thumb" muted autoplay loop playsinline></video>` : `<div class="grad-bg"></div>`;
  }
  const wide = y.aspect === "16:9";
  phone.classList.toggle("wide", wide);
  const scale = wide ? (phone.clientWidth / 1920) * 0.72 : phone.clientWidth / 1080;
  const [, family, weight] = FONT_CSS[y.font];
  Object.assign(cap.style, {
    top: `${y.position}%`, fontFamily: family, fontWeight: weight, fontSize: `${y.size * scale}px`, color: y.color,
    webkitTextStroke: `${y.outline * 2 * scale}px ${y.outline_color}`,
    textShadow: y.shadow ? `${y.shadow * 1.5 * scale}px ${y.shadow * 1.5 * scale}px ${y.shadow * scale}px rgba(0,0,0,.6)` : "none",
  });
  const words = sampleWords();
  let i = 0, k = 0;
  const step = () => {
    const group = words.slice(i, i + y.words_per_cue);
    if (!group.length) { i = 0; return step(); }
    const shown = group.map((w) => esc(y.uppercase ? upperFor(w) : w));
    if (y.animation === "karaoke") {
      cap.className = "cap";
      cap.innerHTML = shown.map((w, j) => (j === k ? `<span style="color:${y.highlight_color}">${w}</span>` : w)).join(" ");
      k += 1; if (k >= group.length) { k = 0; i += y.words_per_cue; }
    } else {
      cap.innerHTML = shown.join(" ");
      cap.className = "cap";
      void cap.offsetWidth; // restart the CSS animation
      cap.className = `cap anim-${y.animation}`;
      i += y.words_per_cue;
    }
  };
  step();
  previewTimer = setInterval(() => { if (!document.getElementById("cap")) return clearInterval(previewTimer); step(); }, y.animation === "karaoke" ? 380 : 900);
}

async function showRealFrame() {
  const s = studioState, b = document.getElementById("realFrame");
  b.disabled = true; b.textContent = "…";
  try {
    const res = await fetch("/api/studio/frame", { method: "POST", headers: { "Content-Type": "application/json", "X-MF-Client": "panel" },
      body: JSON.stringify({ style: s.style, text: sampleWords().join(" "), language: (s.languages || ["en"])[0], background: s.background || "random" }) });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
    const url = URL.createObjectURL(await res.blob());
    const wide = s.style.aspect === "16:9";
    modal(`<h1>🎯 ${st("realFrame")}</h1><p class="muted small">${st("realFrameHelp")}</p>
      <img src="${url}" style="display:block;margin:0 auto;max-width:100%;max-height:70vh;${wide ? "" : "aspect-ratio:9/16;"}border-radius:10px">`);
  } catch (err) { toast(err.message, true); }
  b.disabled = false; b.textContent = "🎯 " + st("realFrame");
}
