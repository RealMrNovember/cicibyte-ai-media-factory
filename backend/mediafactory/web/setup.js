// Easy Setup (#setup): language → models download → choose an AI → models → try → done.
"use strict";

const SU = {
  en: {
    title: "Easy Setup", next: "Continue", back: "Back", skip: "Skip", retry: "Try again",
    s0: "Welcome", s1: "Preparing", s2: "Your AI", s3: "Models", s4: "Try it", s5: "Done",
    welcome: "Media Factory makes short videos on this computer. It needs an AI to write the scripts: one running on this computer, your own AI server, or an AI service you have an account with. This takes a few minutes.",
    chooseLang: "Language of the app", start: "Start",
    prepHelp: "Downloading the voices (Turkish, English) and the caption model — about 600 MB, once. You can go on while it downloads.",
    prepDone: "Ready", prepFailed: "Download failed", prepLater: "It will download with the first video instead.",
    tabLocal: "On this computer", tabServer: "My AI server", tabService: "AI service",
    scanning: "Looking for AI on this computer…", scanAgain: "Look again", found: "Found",
    noneFound: "No AI found on this computer. Install one of these, download a model in it, then look again:",
    modelsN: "models", noModels: "it has no models yet — download one in it first",
    serverHelp: "The address of your OpenAI-compatible AI server (Ollama, LM Studio, vLLM, a router…). Example: http://192.168.1.20:11434",
    address: "Address", keyOptional: "API key (if it needs one)", check: "Check connection",
    serviceHelp: "Choose your AI service and paste your API key. The key is stored encrypted on this computer.",
    service: "Service", apiKey: "API key", getKey: "Get a key", checking: "Checking…",
    ok: "Connected", models: "models",
    r_bad_key: "The API key was not accepted.", r_no_model: "That model was not found for this key.", r_slow: "The AI took too long — choose a smaller or faster model.",
    r_unreachable: "Nothing answered at this address. Is the AI running? Is the address right?", r_error: "Could not connect.",
    scriptModel: "Model for scripts", classifyModel: "Model for sorting stories (can be smaller)",
    modePrimary: "Make it the main AI (keep the current ones as backup)", modeOnly: "Use only this one",
    save: "Save and continue", tryHelp: "A short test in Turkish and English. Local models can take a minute the first time.",
    tryRun: "Run the test", tryOk: "Works", seconds: "s", tryFail: "The test did not work",
    doneHelp: "All set. Make your first video in the Studio, or connect YouTube, Instagram or TikTok in Settings.",
    studio: "Open the Studio", settings: "Settings", finish: "Finish",
    reconfigure: "Run Easy Setup again", aiCard: "🤖 Easy Setup", aiCardHelp: "Connect the AI that writes your scripts: on this computer, your own server, or an AI service.",
    notConfigured: "No AI is connected yet.", connectAi: "Connect your AI",
  },
  tr: {
    title: "Kolay Kurulum", next: "Devam", back: "Geri", skip: "Atla", retry: "Tekrar dene",
    s0: "Hoş geldin", s1: "Hazırlık", s2: "Yapay zekân", s3: "Modeller", s4: "Dene", s5: "Bitti",
    welcome: "Media Factory kısa videoları bu bilgisayarda üretir. Senaryoları yazması için bir yapay zekâya ihtiyacı var: bu bilgisayarda çalışan, kendi yapay zekâ sunucun ya da hesabın olan bir yapay zekâ servisi. Birkaç dakika sürer.",
    chooseLang: "Uygulama dili", start: "Başla",
    prepHelp: "Sesler (Türkçe, İngilizce) ve altyazı modeli indiriliyor — yaklaşık 600 MB, bir kez. İnerken devam edebilirsin.",
    prepDone: "Hazır", prepFailed: "İndirme başarısız", prepLater: "İlk videoyla birlikte inecek.",
    tabLocal: "Bu bilgisayarda", tabServer: "Kendi sunucum", tabService: "Yapay zekâ servisi",
    scanning: "Bu bilgisayarda yapay zekâ aranıyor…", scanAgain: "Tekrar ara", found: "Bulundu",
    noneFound: "Bu bilgisayarda yapay zekâ bulunamadı. Bunlardan birini kur, içinden bir model indir, sonra tekrar ara:",
    modelsN: "model", noModels: "henüz modeli yok — önce içinden bir model indir",
    serverHelp: "OpenAI uyumlu yapay zekâ sunucunun adresi (Ollama, LM Studio, vLLM, bir yönlendirici…). Örnek: http://192.168.1.20:11434",
    address: "Adres", keyOptional: "API anahtarı (gerekiyorsa)", check: "Bağlantıyı dene",
    serviceHelp: "Yapay zekâ servisini seç ve API anahtarını yapıştır. Anahtar bu bilgisayarda şifreli saklanır.",
    service: "Servis", apiKey: "API anahtarı", getKey: "Anahtar al", checking: "Deneniyor…",
    ok: "Bağlandı", models: "model",
    r_bad_key: "API anahtarı kabul edilmedi.", r_no_model: "Bu anahtarla o model bulunamadı.", r_slow: "Yapay zekâ çok yavaş yanıt verdi — daha küçük ya da hızlı bir model seç.",
    r_unreachable: "Bu adreste yanıt veren yok. Yapay zekâ çalışıyor mu? Adres doğru mu?", r_error: "Bağlanılamadı.",
    scriptModel: "Senaryo modeli", classifyModel: "Hikâye ayıklama modeli (daha küçük olabilir)",
    modePrimary: "Ana yapay zekâ yap (mevcutlar yedek kalsın)", modeOnly: "Yalnızca bunu kullan",
    save: "Kaydet ve devam et", tryHelp: "Türkçe ve İngilizce kısa bir deneme. Yerel modeller ilk seferde bir dakika sürebilir.",
    tryRun: "Denemeyi başlat", tryOk: "Çalışıyor", seconds: "sn", tryFail: "Deneme çalışmadı",
    doneHelp: "Her şey hazır. İlk videonu Stüdyo'da yap ya da Ayarlar'dan YouTube, Instagram veya TikTok'u bağla.",
    studio: "Stüdyo'yu aç", settings: "Ayarlar", finish: "Bitir",
    reconfigure: "Kolay Kurulum'u yeniden aç", aiCard: "🤖 Kolay Kurulum", aiCardHelp: "Senaryoları yazan yapay zekâyı bağla: bu bilgisayarda, kendi sunucunda ya da bir yapay zekâ servisinde.",
    notConfigured: "Henüz bağlı bir yapay zekâ yok.", connectAi: "Yapay zekânı bağla",
  },
};
const su = (k) => (SU[lang] && SU[lang][k]) || SU.en[k];

const W = { step: 0, info: null, tab: "local", target: null, models: [], assetsTimer: null };

async function setup(el) {
  clearInterval(W.assetsTimer);
  if (!W.info) W.info = await api("/api/ai-setup");
  const steps = [0, 1, 2, 3, 4, 5].map((i) => `<span class="pill ${i === W.step ? "ok" : i < W.step ? "" : "muted"}">${i + 1}. ${su("s" + i)}</span>`).join(" ");
  el.innerHTML = `<h1>${su("title")}</h1><div class="row" style="gap:6px;flex-wrap:wrap;margin-bottom:16px">${steps}</div><div class="card" id="wiz"></div>`;
  const box = document.getElementById("wiz");
  [stepWelcome, stepPrepare, stepAi, stepModels, stepTry, stepDone][W.step](box);
}
const go = (n) => { W.step = n; render(); };

function stepWelcome(box) {
  box.innerHTML = `<p>${su("welcome")}</p><label>${su("chooseLang")}</label>
    <div class="row"><button class="btn ${lang === "tr" ? "primary" : ""}" data-l="tr">Türkçe</button><button class="btn ${lang === "en" ? "primary" : ""}" data-l="en">English</button></div>
    <div class="row" style="margin-top:16px"><button class="btn primary" id="wNext">${su("start")} →</button></div>`;
  box.querySelectorAll("[data-l]").forEach((b) => b.addEventListener("click", () => { lang = b.dataset.l; localStorage.setItem("mf_lang", lang); render(); }));
  box.querySelector("#wNext").addEventListener("click", async () => { api("/api/ai-setup/assets", { method: "POST" }).catch(() => {}); go(1); });
}

function stepPrepare(box) {
  const draw = (s) => {
    const pct = s.total ? Math.round((100 * s.done) / s.total) : 0;
    const msg = s.state === "done" ? `✓ ${su("prepDone")}` : s.state === "failed" ? `⚠ ${su("prepFailed")}: ${esc(s.error || "")} — ${su("prepLater")}` : `${pct}% ${esc(s.current || "")}`;
    box.innerHTML = `<p>${su("prepHelp")}</p><div style="background:#222;border-radius:6px;height:10px;overflow:hidden"><div style="width:${s.state === "done" ? 100 : pct}%;height:10px;background:#6fbf8e"></div></div>
      <p class="muted small">${msg}</p><div class="row"><button class="btn" id="wBack">← ${su("back")}</button>
      ${s.state === "failed" ? `<button class="btn" id="wRetry">↻ ${su("retry")}</button>` : ""}<span class="spacer"></span><button class="btn primary" id="wNext">${su("next")} →</button></div>`;
    box.querySelector("#wBack").addEventListener("click", () => go(0));
    box.querySelector("#wNext").addEventListener("click", () => go(2));
    const r = box.querySelector("#wRetry");
    r && r.addEventListener("click", async () => { await api("/api/ai-setup/assets", { method: "POST" }).catch(() => {}); poll(); });
  };
  const poll = async () => {
    try { const s = await api("/api/ai-setup/assets"); draw(s); if (s.state !== "running") clearInterval(W.assetsTimer); } catch { clearInterval(W.assetsTimer); }
  };
  poll();
  W.assetsTimer = setInterval(() => { if (route() !== "setup" || W.step !== 1) return clearInterval(W.assetsTimer); poll(); }, 1500);
}

function reasonText(r) { return su("r_" + (r.reason || "error")) + (r.reason === "error" && r.error ? " " + esc(r.error) : ""); }

function stepAi(box) {
  const tabs = [["local", su("tabLocal")], ["server", su("tabServer")], ["service", su("tabService")]]
    .filter(([k]) => k !== "local" && k !== "server" ? true : W.info.local_mode)
    .map(([k, label]) => `<button class="btn ${W.tab === k ? "primary" : ""}" data-tab="${k}">${label}</button>`).join("");
  if (!W.info.local_mode && W.tab !== "service") W.tab = "service";
  box.innerHTML = `<div class="row" style="margin-bottom:12px">${tabs}</div><div id="tabBody"></div>
    <div class="row" style="margin-top:16px"><button class="btn" id="wBack">← ${su("back")}</button><span class="spacer"></span>
    <button class="btn primary" id="wNext" ${W.target && W.models.length ? "" : "disabled"}>${su("next")} →</button></div>`;
  box.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => { W.tab = b.dataset.tab; W.target = null; W.models = []; stepAi(box); }));
  box.querySelector("#wBack").addEventListener("click", () => go(1));
  box.querySelector("#wNext").addEventListener("click", () => go(3));
  const body = box.querySelector("#tabBody");
  const ready = () => { const n = box.querySelector("#wNext"); n.disabled = !(W.target && W.models.length); };
  if (W.tab === "local") {
    body.innerHTML = `<p class="muted">${su("scanning")}</p>`;
    api("/api/ai-setup/scan").then((r) => {
      const cards = r.found.map((f, i) => `<label class="card row" style="margin:6px 0;cursor:pointer"><input type="radio" name="loc" value="${i}" style="width:auto" ${f.models.length ? "" : "disabled"}>
        <b>${esc(f.name)}</b><span class="muted small">${esc(f.base_url)} · ${f.models.length ? f.models.length + " " + su("modelsN") : su("noModels")}</span></label>`).join("");
      const dl = Object.entries(W.info.downloads).map(([k, u]) => `<button class="btn" data-dl="${esc(u)}">⬇ ${k === "ollama" ? "Ollama" : "LM Studio"}</button>`).join("");
      body.innerHTML = (cards || `<p>${su("noneFound")}</p><div class="row">${dl}</div>`) + `<div class="row" style="margin-top:8px"><button class="btn" id="rescan">↻ ${su("scanAgain")}</button></div>`;
      body.querySelector("#rescan").addEventListener("click", () => stepAi(box));
      body.querySelectorAll("[data-dl]").forEach((b) => b.addEventListener("click", () => openExternal(b.dataset.dl)));
      body.querySelectorAll("[name=loc]").forEach((rb) => rb.addEventListener("change", () => {
        const f = r.found[Number(rb.value)];
        W.target = { base_url: f.base_url, name: f.name + (lang === "tr" ? " (bu bilgisayar)" : " (this computer)") };
        W.models = f.models; ready();
      }));
    }).catch((err) => { body.innerHTML = `<p class="muted">${esc(err.message)}</p>`; });
  } else if (W.tab === "server") {
    body.innerHTML = `<p class="muted small">${su("serverHelp")}</p><form id="srvAi" class="grid g3" style="align-items:end">
      <div><label>${su("address")}</label><input name="url" required placeholder="http://192.168.1.20:11434"></div>
      <div><label>${su("keyOptional")}</label><input name="key" type="password" autocomplete="off"></div>
      <div><button class="btn primary">${su("check")}</button></div></form><p id="chk" class="small"></p>`;
    body.querySelector("#srvAi").addEventListener("submit", async (e) => {
      e.preventDefault();
      const f = e.target, out = body.querySelector("#chk");
      out.textContent = su("checking");
      const r = await api("/api/ai-setup/check", { method: "POST", body: { base_url: f.url.value.trim(), api_key: f.key.value.trim() || null } }).catch((err) => ({ ok: false, error: err.message }));
      if (!r.ok) { out.innerHTML = "⚠ " + reasonText(r); W.target = null; W.models = []; return ready(); }
      out.innerHTML = `✓ ${su("ok")} · ${r.models.length} ${su("models")}`;
      W.target = { base_url: r.base_url, api_key: f.key.value.trim() || null }; W.models = r.models; ready();
    });
  } else {
    const opts = W.info.presets.map((p) => `<option value="${p.id}">${esc(p.name)}</option>`).join("");
    body.innerHTML = `<p class="muted small">${su("serviceHelp")}</p><form id="svc" class="grid g3" style="align-items:end">
      <div><label>${su("service")}</label><select name="preset">${opts}</select></div>
      <div><label>${su("apiKey")} <a href="#" id="getKey">${su("getKey")} ↗</a></label><input name="key" type="password" required autocomplete="off"></div>
      <div><button class="btn primary">${su("check")}</button></div></form><p id="chk" class="small"></p>`;
    const form = body.querySelector("#svc");
    body.querySelector("#getKey").addEventListener("click", (e) => { e.preventDefault(); const p = W.info.presets.find((x) => x.id === form.preset.value); openExternal(p.key_url); });
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const out = body.querySelector("#chk"), p = W.info.presets.find((x) => x.id === form.preset.value);
      out.textContent = su("checking");
      const r = await api("/api/ai-setup/check", { method: "POST", body: { preset: p.id, api_key: form.key.value.trim(), model: p.models[0] } }).catch((err) => ({ ok: false, error: err.message }));
      if (!r.ok) { out.innerHTML = "⚠ " + reasonText(r); W.target = null; W.models = []; return ready(); }
      const listed = new Set(r.models);
      const preferred = p.models.filter((m) => listed.has(m));
      W.models = [...preferred, ...r.models.filter((m) => !preferred.includes(m))];
      if (!W.models.length) W.models = p.models;
      out.innerHTML = `✓ ${su("ok")} · ${r.models.length} ${su("models")}`;
      W.target = { preset: p.id, api_key: form.key.value.trim() }; ready();
    });
  }
}

function stepModels(box) {
  const options = (sel) => W.models.map((m) => `<option ${m === sel ? "selected" : ""}>${esc(m)}</option>`).join("");
  box.innerHTML = `<form id="mf" class="grid g2">
      <div><label>${su("scriptModel")}</label><select name="script">${options(W.models[0])}</select></div>
      <div><label>${su("classifyModel")}</label><select name="classify">${options(W.models[0])}</select></div>
      ${W.info.configured ? `<div style="grid-column:1/-1"><label class="row"><input type="radio" name="mode" value="primary" checked style="width:auto"> ${su("modePrimary")}</label>
        <label class="row"><input type="radio" name="mode" value="only" style="width:auto"> ${su("modeOnly")}</label></div>` : ""}
    </form><div class="row" style="margin-top:16px"><button class="btn" id="wBack">← ${su("back")}</button><span class="spacer"></span><button class="btn primary" id="wSave">${su("save")} →</button></div>`;
  box.querySelector("#wBack").addEventListener("click", () => go(2));
  box.querySelector("#wSave").addEventListener("click", async () => {
    const f = box.querySelector("#mf");
    const body = { ...W.target, script_model: f.script.value, classify_model: f.classify.value, mode: f.mode ? f.mode.value : "only" };
    try { await api("/api/ai-setup/apply", { method: "POST", body }); W.info = null; go(4); } catch (err) { toast(err.message, true); }
  });
}

function stepTry(box) {
  box.innerHTML = `<p class="muted">${su("tryHelp")}</p><div id="tryOut"></div>
    <div class="row" style="margin-top:16px"><button class="btn" id="wBack">← ${su("back")}</button><button class="btn primary" id="wRun">▶ ${su("tryRun")}</button>
    <span class="spacer"></span><button class="btn" id="wNext">${su("next")} →</button></div>`;
  box.querySelector("#wBack").addEventListener("click", () => go(3));
  box.querySelector("#wNext").addEventListener("click", () => go(5));
  box.querySelector("#wRun").addEventListener("click", async (e) => {
    const out = box.querySelector("#tryOut");
    e.target.disabled = true; out.innerHTML = `<p class="muted">${su("checking")}</p>`;
    const r = await api("/api/ai-setup/try", { method: "POST" }).catch((err) => ({ ok: false, error: err.message }));
    e.target.disabled = false;
    out.innerHTML = r.ok
      ? `<p>✓ <b>${su("tryOk")}</b> · ${r.seconds} ${su("seconds")}</p><p class="small">🇹🇷 ${esc(r.sample.tr || "")}</p><p class="small">🇬🇧 ${esc(r.sample.en || "")}</p>`
      : `<p>⚠ <b>${su("tryFail")}</b></p><p class="muted small">${esc(r.error || "")}</p>`;
  });
}

function stepDone(box) {
  api("/api/ai-setup/done", { method: "POST" }).catch(() => {});
  box.innerHTML = `<p>${su("doneHelp")}</p><div class="row"><a class="btn primary" href="#studio">${su("studio")}</a><a class="btn" href="#settings">${su("settings")}</a></div>`;
  W.step = 0; W.info = null; W.target = null; W.models = [];
}

// Settings card + overview hint
function setupCard() {
  return `<div class="card" style="margin-bottom:16px"><h3>${su("aiCard")}</h3><p class="muted small">${su("aiCardHelp")}</p>
    <a class="btn primary" href="#setup">${su("reconfigure")}</a></div>`;
}
