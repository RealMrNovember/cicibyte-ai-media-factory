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
    anim_none: "None", anim_fade: "Fade", anim_pop: "Pop", anim_slide_up: "Slide up", anim_karaoke: "Word highlight (karaoke)",
    presets: "Presets", output: "Output", produce: "Produce", top: "Top", middle: "Middle", bottom: "Bottom",
    previewHint: "Click the preview to place the captions.", addStory: "Add your own story", storyTitle: "Title", storyText: "Story text (paste it here)", orFile: "…or upload a file (.txt, .md, .pdf, .docx)", storyLang: "Language of the text", storyAdded: "Story added", storyDup: "This story was already in your list", needText: "Paste a text or choose a file", aiStory: "Write with AI", aiTitle: "Write a new story with AI", topic: "Topic or idea (optional)", topicPh: "e.g. noises from the attic of a village house", length: "Length", writing: "Writing… this can take a minute", allLangs: "All languages", short: "Short", medium: "Medium", long: "Long", noStories: "No stories yet — add a source and collect.",
    noClips: "No clips yet. Upload gameplay or stock footage you are allowed to use.", sure: "Delete this clip?",
  },
  tr: {
    studio: "Stüdyo", studioSub: "Hikâyeyi, arka planı ve altyazı stilini seç — sonra üret.",
    story: "Hikâye", pickStory: "Bir hikâye seç…", background: "Arka plan", random: "Rastgele", none: "Klip yok (gradyan)",
    upload: "Klip yükle", licence: "Lisans / not (isteğe bağlı)", sourceUrl: "Nereden geldi (isteğe bağlı)",
    uploading: "Yükleniyor…", uploaded: "Klip eklendi", captions: "Altyazı", font: "Yazı tipi", size: "Boyut",
    textColor: "Yazı", highlight: "Vurgu", outlineColor: "Kontur", outline: "Kontur kalınlığı", shadow: "Gölge",
    uppercase: "BÜYÜK HARF", words: "Satır başına kelime", position: "Ekrandaki konum", animation: "Animasyon",
    anim_none: "Yok", anim_fade: "Belirme", anim_pop: "Zıplama", anim_slide_up: "Aşağıdan kayma", anim_karaoke: "Kelime vurgusu (karaoke)",
    presets: "Hazır stiller", output: "Çıktı", produce: "Üret", top: "Üst", middle: "Orta", bottom: "Alt",
    previewHint: "Altyazıyı yerleştirmek için önizlemeye tıkla.", addStory: "Kendi hikâyeni ekle", storyTitle: "Başlık", storyText: "Hikâye metni (buraya yapıştır)", orFile: "…ya da dosya yükle (.txt, .md, .pdf, .docx)", storyLang: "Metnin dili", storyAdded: "Hikâye eklendi", storyDup: "Bu hikâye zaten listende vardı", needText: "Bir metin yapıştır ya da dosya seç", aiStory: "AI ile yaz", aiTitle: "AI ile yeni hikâye yaz", topic: "Konu ya da fikir (isteğe bağlı)", topicPh: "ör. köy evinin tavanından gelen sesler", length: "Uzunluk", writing: "Yazılıyor… bir dakika sürebilir", allLangs: "Tüm diller", short: "Kısa", medium: "Orta", long: "Uzun", noStories: "Henüz hikâye yok — kaynak ekleyip topla.",
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
  outline: 7, shadow: 3, uppercase: true, words_per_cue: 3, position: 50, animation: "pop",
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

function loadStyle() {
  try { return { ...DEFAULT_STYLE, ...JSON.parse(localStorage.getItem("mf_style") || "{}") }; } catch { return { ...DEFAULT_STYLE }; }
}
function saveStyle(s) { try { localStorage.setItem("mf_style", JSON.stringify(s)); } catch { /* private mode */ } }

async function studio(el) {
  clearInterval(previewTimer);
  const pre = Number((location.hash.split("/")[1] || "").split("?")[0]) || null;
  const [items, clips] = await Promise.all([api("/api/items?limit=200"), api("/api/backgrounds")]);
  const prev = studioState || {};
  studioState = {
    items: items.items, clips: clips.items, style: prev.style || loadStyle(),
    itemId: pre || prev.itemId || (items.items[0] && items.items[0].id) || null,
    background: prev.background || "random", languages: prev.languages || ["en"], seconds: prev.seconds || 50,
  };
  el.innerHTML = `<h1>${st("studio")}</h1><p class="sub">${st("studioSub")}</p>
    <div class="studio">
      <div class="studio-controls">
        <div class="card"><div class="row"><h3>1 · ${st("story")}</h3><span class="spacer"></span>
          <button class="btn" id="aiStory">✨ ${st("aiStory")}</button><button class="btn" id="addStory">＋ ${st("addStory")}</button></div><div id="storyBox"></div></div>
        <div class="card"><div class="row"><h3>2 · ${st("background")}</h3><span class="spacer"></span>
          <button class="btn" id="upBtn">＋ ${st("upload")}</button></div><div id="bgBox"></div></div>
        <div class="card"><h3>3 · ${st("captions")}</h3><div id="capBox"></div></div>
        <div class="card"><h3>4 · ${st("output")}</h3><div id="outBox"></div></div>
      </div>
      <div class="studio-preview"><div class="phone" id="phone"><div class="phone-bg" id="phoneBg"></div>
        <div class="cap" id="cap"></div></div><p class="muted small" style="text-align:center">${st("previewHint")}</p></div>
    </div>`;
  drawStory(); drawBackgrounds(); drawCaptions(); drawOutput(); drawPreview();
  document.getElementById("upBtn").addEventListener("click", uploadDialog);
  document.getElementById("aiStory").addEventListener("click", () => aiStoryDialog(async (item) => {
    studioState.items = (await api("/api/items?limit=200")).items; studioState.itemId = item.id; studioState.langFilter = item.language || ""; drawStory(); drawPreview();
  }));
  document.getElementById("addStory").addEventListener("click", () => addStoryDialog(async (item) => {
    studioState.items = (await api("/api/items?limit=200")).items; studioState.itemId = item.id; drawStory(); drawPreview();
  }));
  document.getElementById("phone").addEventListener("click", (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    setStyle({ position: Math.max(8, Math.min(92, Math.round(((e.clientY - r.top) / r.height) * 100))) });
    drawCaptions();
  });
}

function setStyle(patch) { Object.assign(studioState.style, patch); saveStyle(studioState.style); drawPreview(); }

function drawStory() {
  const s = studioState, box = document.getElementById("storyBox");
  const lf = s.langFilter || "";
  const list = s.items.filter((i) => !lf || (i.language || "en") === lf);
  const filter = `<div class="row" style="margin-bottom:10px">${[["", st("allLangs")], ["en", "English"], ["tr", "Türkçe"]].map(([v, l]) =>
    `<button class="btn small-btn ${lf === v ? "primary" : ""}" data-lf="${v}">${l}</button>`).join("")}</div>`;
  if (!list.length) {
    box.innerHTML = filter + `<p class="muted">${st("noStories")}</p>`;
    box.querySelectorAll("[data-lf]").forEach((b) => b.addEventListener("click", () => { s.langFilter = b.dataset.lf; drawStory(); }));
    return;
  }
  const cur = list.find((i) => i.id === s.itemId) || list[0];
  s.itemId = cur.id;
  box.innerHTML = filter + `<select id="story">${list.map((i) => `<option value="${i.id}" ${i.id === cur.id ? "selected" : ""}>${(i.language || "en").toUpperCase()} · ${esc(i.title)}</option>`).join("")}</select>
    <p class="muted small clip3" style="margin:10px 0 0">${esc(cur.text)}</p>
    <p class="muted small" style="margin:6px 0 0">${cur.chars} ${t("chars")} · <span class="pill">${esc(cur.rights_status)}</span></p>`;
  document.getElementById("story").addEventListener("change", (e) => { s.itemId = Number(e.target.value); drawStory(); drawPreview(); });
  box.querySelectorAll("[data-lf]").forEach((b) => b.addEventListener("click", async () => {
    s.langFilter = b.dataset.lf; s.items = (await api(`/api/items?limit=200${s.langFilter ? "&language=" + s.langFilter : ""}`)).items; drawStory(); drawPreview();
  }));
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
      ${s.clips.map((c) => tile(c.name, `<img loading="lazy" src="/api/backgrounds/${encodeURIComponent(c.name)}/thumb"><span>${esc(c.name)}</span>`,
        `${c.licence}${c.source ? " · " + c.source : ""}`, true)).join("")}
    </div>${s.clips.length ? "" : `<p class="muted small">${st("noClips")}</p>`}`;
  box.querySelectorAll("[data-bg]").forEach((n) => n.addEventListener("click", (e) => {
    if (e.target.closest("[data-delbg]")) return;
    s.background = n.dataset.bg; drawBackgrounds(); drawPreview();
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

function uploadDialog() {
  const m = modal(`<h1>${st("upload")}</h1><form id="upf">
    <label>Video (mp4, mov, mkv, webm)</label><input type="file" name="file" accept="video/*" required>
    <label>${st("licence")}</label><input name="licence" placeholder="Mixkit Free License / Coverr / own recording">
    <label>${st("sourceUrl")}</label><input name="source" placeholder="https://mixkit.co/...">
    <div class="progress" hidden><div></div></div>
    <div class="row" style="margin-top:14px"><button class="btn primary">${st("upload")}</button></div></form>`);
  m.querySelector("#upf").addEventListener("submit", (e) => {
    e.preventDefault();
    const fd = new FormData(e.target), bar = m.querySelector(".progress"), btn = m.querySelector("button.primary");
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
  box.querySelectorAll("[data-preset]").forEach((n) => n.addEventListener("click", () => { studioState.style = { ...PRESETS[n.dataset.preset] }; saveStyle(studioState.style); drawCaptions(); drawPreview(); }));
  box.querySelectorAll("[data-pos]").forEach((n) => n.addEventListener("click", () => { setStyle({ position: Number(n.dataset.pos) }); drawCaptions(); }));
}

function drawOutput() {
  const s = studioState, box = document.getElementById("outBox");
  box.innerHTML = `<label>${t("languages")}</label><div class="row">
      <label class="row"><input type="checkbox" data-lang="en" ${s.languages.includes("en") ? "checked" : ""} style="width:auto"> English</label>
      <label class="row"><input type="checkbox" data-lang="tr" ${s.languages.includes("tr") ? "checked" : ""} style="width:auto"> Türkçe</label></div>
    <label>${t("seconds")} <b class="val">${s.seconds}</b></label><input type="range" id="secs" min="15" max="170" step="5" value="${s.seconds}">
    <div class="row" style="margin-top:16px"><button class="btn primary big" id="produce">▶ ${st("produce")}</button></div>`;
  box.querySelectorAll("[data-lang]").forEach((n) => n.addEventListener("change", () => {
    s.languages = [...box.querySelectorAll("[data-lang]")].filter((x) => x.checked).map((x) => x.dataset.lang);
  }));
  document.getElementById("secs").addEventListener("input", (e) => { s.seconds = Number(e.target.value); e.target.previousElementSibling.querySelector(".val").textContent = s.seconds; });
  document.getElementById("produce").addEventListener("click", async (e) => {
    if (!s.itemId) return toast(st("noStories"), true);
    if (!s.languages.length) return toast(t("languages"), true);
    e.target.disabled = true;
    try {
      await api(`/api/items/${s.itemId}/make`, { method: "POST", body: { languages: s.languages, seconds: s.seconds, background: s.background, style: s.style } });
      toast(t("makeStarted")); location.hash = "#production";
    } catch (err) { toast(err.message, true); e.target.disabled = false; }
  });
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
  const scale = phone.clientWidth / 1080;
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
