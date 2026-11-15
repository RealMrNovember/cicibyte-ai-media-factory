// CiciByte AI Media Factory panel — no build step. Powered by CiciByte Technology.
"use strict";

const I18N = {
  en: {
    overview: "Overview", sources: "Sources", inbox: "Inbox", production: "Production", ready: "Ready videos",
    offTitle: "This computer can't reach your Media Factory server",
    offWhy: "Everything — AI keys, YouTube and Instagram, sources, schedules, videos — lives on the server, not on this computer. Once this computer reaches the same server you see it all as it is: no import needed. (Export/import is for moving to another server.)",
    offSteps: "If your server is on Tailscale: 1) install Tailscale on this computer, 2) sign in with the same account as your server, 3) press “Try again”. Otherwise enter the server's address below.",
    offGet: "Download Tailscale", offRetry: "Try again", offAddr: "Address tried",
    settings: "Settings", notifLabel: "Windows notifications (video ready, published, failed, new version)", backup: "Backup & move", backupHelp: "Export all settings — AI providers and keys, task routes, sources, schedules, YouTube and Reddit — to a file, and import it on another computer or server. Import adds and updates; it never deletes. Keys are only included if you set a password (they are encrypted with it). Videos, clips and music are not included.", expPassword: "Password for the keys (optional)", expPasswordPh: "leave empty to export without keys", export: "Export settings", impFile: "Settings file", impPassword: "Password (if the file has keys)", import: "Import", exportedWithKeys: "Exported with encrypted keys", exportedNoKeys: "Exported without keys", imported: "Imported", schedulesN: "schedules", appUpdate: "A new version of the app is available:", appUpdateNow: "Update now", appUpdating: "Downloading…", appRestarting: "Installing — the app will reopen in a moment", appDownloadOpened: "The download page is open in your browser: install the new version over this one", updates: "Updates", updHelp: "The server checks GitHub every 30 minutes and installs new versions by itself. It waits while a video is being made and goes back automatically if a new version does not start.", updAuto: "Automatic", updVersion: "Running", updLatest: "Latest on GitHub", updState: "Status", updChecked: "Last check", updLast: "last update", updLog: "Update log", updNow: "Check & update now", updPending: "Update requested…", updRequested: "Update requested — the panel reloads when the server is back", updMissing: "Automatic updates are not installed on this server yet. Run once on the server:", upd_up_to_date: "Up to date", upd_available: "Update available", upd_updating: "Updating…", upd_updated: "Updated", upd_deferred: "Waiting for running jobs", upd_rolled_back: "Rolled back", upd_failed: "Failed", upd_error: "Can't reach GitHub", disabledSrc: "Paused", srcOn: "Source on — it will be collected again", srcOff: "Source paused — it won't be collected", cover: "Cover", qcTitle: "Quality check", qc_resolution: "Resolution", qc_duration: "Length", qc_audio: "Audio", qc_loudness: "Loudness", qc_peak: "Peak level", qc_silence: "Long silence", qc_black: "Black screen", qc_captions: "Captions", qc_originality: "Originality (copied from source)", qc_content: "Sensitive content (YouTube/Instagram rules)", qc_rights: "Rights status", qc_measure: "Measurement", catalog: "Source catalog", catalogHelp: "Ready-made sources in English and Turkish. Filter by language and type, add one or all.", addShown: "Add all shown", allLangs: "All languages", allTypes: "All types", added: "Added", sourcesAdded: "sources added", mySources: "My sources", server: "Server", serverHelp: "Production runs on this server. Address of your Media Factory server.", connected: "Connected", offline: "Cannot reach the server — set its address in Settings.", logout: "Log out", login: "Log in", email: "E-mail", password: "Password",
    welcome: "Your self-hosted AI media factory.", items: "Items", queued: "In production", readyN: "Ready",
    approved: "Approved", failed: "Failed", add: "Add", name: "Name", adapter: "Adapter", runNow: "Collect now",
    lastRun: "Last run", status: "Status", error: "Error", make: "Make video", makeTitle: "Make a Short",
    languages: "Languages", seconds: "Target seconds", start: "Start", cancel: "Cancel", retry: "Retry",
    approve: "Approve", reject: "Reject", download: "Download", noData: "Nothing here yet.", search: "Search…",
    rights: "Rights", chars: "chars", open: "Open", close: "Close", save: "Save", providers: "AI providers",
    routes: "Task routes", baseUrl: "Base URL", apiKey: "API key", test: "Test", model: "Model",
    reddit: "Reddit API credentials", clientId: "Client id", clientSecret: "Client secret", enabled: "Enabled",
    subreddit: "Subreddit", url: "Feed / page URL", interval: "Every (minutes)", delete: "Delete",
    doctorFrom: "rewritten from", doctorNotes: "Notes",
    script: "Script", stages: "Stages", support: "Support", poweredBy: "Powered by",
    makeStarted: "Production started", saved: "Saved", sourceAdded: "Source added",
    readyHint: "Rendered videos waiting for your approval.",
  },
  tr: {
    overview: "Genel Bakış", sources: "Kaynaklar", inbox: "Gelen Kutusu", production: "Üretim", ready: "Hazır Videolar",
    offTitle: "Bu bilgisayar Media Factory sunucuna ulaşamıyor",
    offWhy: "Her şey — AI anahtarları, YouTube ve Instagram, kaynaklar, takvimler, videolar — bu bilgisayarda değil, sunucuda duruyor. Bu bilgisayar aynı sunucuya ulaşınca hepsini olduğu gibi görürsün: içe aktarmaya gerek yok. (Dışa/içe aktarma başka bir sunucuya taşımak içindir.)",
    offSteps: "Sunucun Tailscale üzerindeyse: 1) bu bilgisayara Tailscale kur, 2) sunucunla aynı hesapla giriş yap, 3) “Tekrar dene”ye bas. Değilse sunucunun adresini aşağıya yaz.",
    offGet: "Tailscale'i indir", offRetry: "Tekrar dene", offAddr: "Denenen adres",
    settings: "Ayarlar", notifLabel: "Windows bildirimleri (video hazır, yayınlandı, başarısız, yeni sürüm)", backup: "Yedekle ve taşı", backupHelp: "Bütün ayarları — AI sağlayıcıları ve anahtarları, görev rotaları, kaynaklar, takvimler, YouTube ve Reddit — bir dosyaya aktar, başka bir bilgisayarda ya da sunucuda içe al. İçe aktarma ekler ve günceller, hiçbir şeyi silmez. Anahtarlar yalnızca parola verirsen dahil edilir ve o parolayla şifrelenir. Videolar, klipler ve müzikler dahil değildir.", expPassword: "Anahtarlar için parola (isteğe bağlı)", expPasswordPh: "boş bırakırsan anahtarsız aktarılır", export: "Ayarları dışa aktar", impFile: "Ayar dosyası", impPassword: "Parola (dosyada anahtar varsa)", import: "İçe aktar", exportedWithKeys: "Şifreli anahtarlarla dışa aktarıldı", exportedNoKeys: "Anahtarsız dışa aktarıldı", imported: "İçe aktarıldı", schedulesN: "takvim", appUpdate: "Uygulamanın yeni sürümü hazır:", appUpdateNow: "Şimdi güncelle", appUpdating: "İndiriliyor…", appRestarting: "Kuruluyor — uygulama birazdan yeniden açılacak", appDownloadOpened: "İndirme sayfası tarayıcıda açıldı: yeni sürümü bunun üzerine kur", updates: "Güncellemeler", updHelp: "Sunucu 30 dakikada bir GitHub'ı kontrol eder ve yeni sürümleri kendisi kurar. Video üretilirken bekler; yeni sürüm açılmazsa otomatik olarak eskisine döner.", updAuto: "Otomatik", updVersion: "Çalışan sürüm", updLatest: "GitHub'daki son sürüm", updState: "Durum", updChecked: "Son kontrol", updLast: "son güncelleme", updLog: "Güncelleme kaydı", updNow: "Şimdi kontrol et ve güncelle", updPending: "Güncelleme istendi…", updRequested: "Güncelleme istendi — sunucu geri gelince panel yenilenecek", updMissing: "Bu sunucuda otomatik güncelleme henüz kurulu değil. Sunucuda bir kez çalıştır:", upd_up_to_date: "Güncel", upd_available: "Yeni sürüm var", upd_updating: "Güncelleniyor…", upd_updated: "Güncellendi", upd_deferred: "Çalışan işler bekleniyor", upd_rolled_back: "Geri alındı", upd_failed: "Başarısız", upd_error: "GitHub'a ulaşılamıyor", disabledSrc: "Durduruldu", srcOn: "Kaynak açıldı — yeniden toplanacak", srcOff: "Kaynak durduruldu — toplanmayacak", cover: "Kapak", qcTitle: "Kalite kontrolü", qc_resolution: "Çözünürlük", qc_duration: "Süre", qc_audio: "Ses", qc_loudness: "Ses yüksekliği", qc_peak: "Tepe seviyesi", qc_silence: "Uzun sessizlik", qc_black: "Siyah ekran", qc_captions: "Altyazı", qc_originality: "Özgünlük (kaynaktan kopya)", qc_content: "Hassas içerik (YouTube/Instagram kuralları)", qc_rights: "Hak durumu", qc_measure: "Ölçüm", catalog: "Kaynak kataloğu", catalogHelp: "Türkçe ve İngilizce hazır kaynaklar. Dile ve türe göre filtrele; tek tek ya da hepsini ekle.", addShown: "Görünenlerin hepsini ekle", allLangs: "Tüm diller", allTypes: "Tüm türler", added: "Eklendi", sourcesAdded: "kaynak eklendi", mySources: "Kaynaklarım", server: "Sunucu", serverHelp: "Üretim bu sunucuda çalışır. Media Factory sunucunuzun adresi.", connected: "Bağlandı", offline: "Sunucuya ulaşılamıyor — adresini Ayarlar'dan girin.", logout: "Çıkış", login: "Giriş", email: "E-posta", password: "Parola",
    welcome: "Kendi sunucunda çalışan yapay zekâ medya fabrikan.", items: "Öğe", queued: "Üretimde", readyN: "Hazır",
    approved: "Onaylı", failed: "Hatalı", add: "Ekle", name: "Ad", adapter: "Adaptör", runNow: "Şimdi topla",
    lastRun: "Son çalışma", status: "Durum", error: "Hata", make: "Video üret", makeTitle: "Shorts üret",
    languages: "Diller", seconds: "Hedef süre (sn)", start: "Başlat", cancel: "İptal", retry: "Yeniden dene",
    approve: "Onayla", reject: "Reddet", download: "İndir", noData: "Henüz bir şey yok.", search: "Ara…",
    rights: "Hak", chars: "karakter", open: "Aç", close: "Kapat", save: "Kaydet", providers: "AI sağlayıcıları",
    routes: "Görev rotaları", baseUrl: "Taban adres", apiKey: "API anahtarı", test: "Test et", model: "Model",
    reddit: "Reddit API kimlik bilgileri", clientId: "Client id", clientSecret: "Client secret", enabled: "Etkin",
    subreddit: "Subreddit", url: "Besleme / sayfa adresi", interval: "Sıklık (dakika)", delete: "Sil",
    doctorFrom: "ilk taslak", doctorNotes: "Notlar",
    script: "Senaryo", stages: "Aşamalar", support: "Destek ol", poweredBy: "Powered by",
    makeStarted: "Üretim başladı", saved: "Kaydedildi", sourceAdded: "Kaynak eklendi",
    readyHint: "Render edilmiş, onayını bekleyen videolar.",
  },
};
const urlLang = new URLSearchParams(location.search).get("lang");
if (urlLang) { try { localStorage.setItem("mf_lang", urlLang); } catch { /* private mode */ } }
let lang = urlLang || localStorage.getItem("mf_lang") || (navigator.language || "en").slice(0, 2);
if (!I18N[lang]) lang = "en";
const t = (k) => I18N[lang][k] || k;
const $app = document.getElementById("app");
let me = null;
let pollTimer = null;

// ---------- helpers ----------
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
let desktop = null; // {server_url} when running inside the desktop app
let offline = false;
async function api(path, opts = {}) {
  const headers = { ...(opts.body && !(opts.body instanceof FormData) ? { "Content-Type": "application/json" } : {}) };
  if (opts.method && opts.method !== "GET") headers["X-MF-Client"] = "panel";
  const res = await fetch(path, {
    ...opts, headers, credentials: "same-origin",
    body: opts.body && !(opts.body instanceof FormData) ? JSON.stringify(opts.body) : opts.body,
  });
  if (res.status === 502 && res.headers.get("X-MF-Desktop")) { offline = true; throw new Error(t("offline")); }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new Error((data && data.detail && (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail))) || res.statusText);
  return data;
}
function toast(msg, bad = false) {
  const el = document.createElement("div");
  el.className = "toast" + (bad ? " bad" : "");
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4200);
}
function when(iso) { return iso ? new Date(iso).toLocaleString(lang === "tr" ? "tr-TR" : "en-GB") : "—"; }
function pill(status) {
  const cls = { approved: "ok", needs_review: "ok", published: "ok", scheduled: "ok", uploading: "warn", failed: "bad", rejected: "bad", retry_wait: "warn", discovered: "warn" }[status] || "";
  return `<span class="pill ${cls}">${esc(status)}</span>`;
}
function on(sel, ev, fn) { document.querySelectorAll(sel).forEach((el) => el.addEventListener(ev, fn)); }

// ---------- layout ----------
const ROUTES = ["overview", "live", "studio", "sources", "inbox", "production", "ready", "schedule", "settings"];
function route() { const r = (location.hash || "#overview").slice(1).split("/")[0]; return ROUTES.includes(r) ? r : "overview"; }

function shell(inner) {
  const nav = ROUTES.map((r) => `<a href="#${r}" class="${route() === r ? "on" : ""}">${r === "studio" ? st(r) : r === "schedule" ? sc(r) : r === "live" ? "● " + lv(r) : t(r)}</a>`).join("");
  return `${titlebar()}<div class="shell${isDesktopWin() ? " has-titlebar" : ""}">
    <aside class="side">
      <div class="brand">CiciByte AI Media Factory<small>${desktop ? esc(desktop.server_url) : ""}</small><a href="#live" id="liveMini" class="live-mini"></a></div>
      <nav class="nav">${nav}</nav>
      <div class="grow"></div>
      <div class="foot">
        <a href="#" id="lang">${lang === "tr" ? "English" : "Türkçe"}</a><br>
        ${t("poweredBy")} <a href="https://cicibyte.com" target="_blank" rel="noopener">CiciByte Technology</a><br>
        <a href="https://buymeacoffee.com/mikeross" target="_blank" rel="noopener">☕ ${t("support")}</a>
      </div>
    </aside>
    <main class="main">${offline ? `<div class="card banner">${t("offline")} <a href="#settings">${t("settings")} →</a></div>` : ""}${desktop && desktop.update ? `<div class="card banner row">⬆ ${t("appUpdate")} <b>v${esc(desktop.update.version)}</b><span class="spacer"></span><button class="btn primary" id="appUpdate">${t("appUpdateNow")}</button></div>` : ""}<div id="main">${inner}</div></main>
  </div>`;
}

async function render() {
  clearInterval(pollTimer);
  if (typeof previewTimer !== "undefined") clearInterval(previewTimer);
  if (desktop === null) { try { desktop = await (await fetch("/desktop/config")).json(); } catch { desktop = false; } }
  offline = false;
  try { me = await api("/api/auth/me"); } catch { me = null; }
  $app.innerHTML = shell(`<p class="muted">…</p>`);
  bindShell();
  const page = { overview, live, studio, sources, inbox, production, ready, schedule, settings }[route()];
  try { await page(document.getElementById("main")); } catch (err) {
    if (offline && route() !== "settings") { $app.innerHTML = shell(`<h1>${t(route())}</h1><p class="muted">${t("offline")}</p>`); bindShell(); }
    else toast(err.message, true);
  }
}
function isDesktopWin() { return !!(desktop && window.pywebview && window.pywebview.api && window.pywebview.api.minimize); }

function titlebar() {
  if (!isDesktopWin()) return "";
  return `<div class="titlebar pywebview-drag-region" id="titlebar">
      <div class="tb-left pywebview-drag-region"><span class="tb-logo">▶</span><span class="pywebview-drag-region">CiciByte AI Media Factory</span></div>
      <a href="#live" class="tb-status idle" id="tbStatus"><span class="tb-dot"></span><span class="tb-body" id="tbText">…</span><span class="tb-bar"><i id="tbBar"></i></span></a>
      <div class="tb-buttons"><button data-win="minimize" title="Minimize">&#xE921;</button><button data-win="maximize" title="Maximize">&#xE922;</button><button data-win="close" class="tb-close" title="Close">&#xE8BB;</button></div>
    </div>
    <div class="rz rz-n" data-rz="n"></div><div class="rz rz-s" data-rz="s"></div><div class="rz rz-e" data-rz="e"></div><div class="rz rz-w" data-rz="w"></div>
    <div class="rz rz-ne" data-rz="ne"></div><div class="rz rz-nw" data-rz="nw"></div><div class="rz rz-se" data-rz="se"></div><div class="rz rz-sw" data-rz="sw"></div>`;
}

function bindTitlebar() {
  if (!isDesktopWin()) return;
  const apiw = window.pywebview.api;
  document.querySelectorAll("[data-win]").forEach((b) => b.addEventListener("click", (e) => {
    e.stopPropagation();
    const a = b.dataset.win;
    if (a === "minimize") apiw.minimize();
    else if (a === "maximize") apiw.toggle_maximize();
    else apiw.close();
  }));
  const tb = document.getElementById("titlebar");
  tb.addEventListener("dblclick", (e) => { if (!e.target.closest("button,a")) apiw.toggle_maximize(); });
  // Resizable edges: drag a border; the opposite side stays where it is.
  document.querySelectorAll("[data-rz]").forEach((h) => h.addEventListener("mousedown", async (e) => {
    e.preventDefault();
    const edge = h.dataset.rz, [w0, h0] = await apiw.size(), x0 = e.screenX, y0 = e.screenY;
    const anchor = (edge.includes("n") ? "s" : "n") + (edge.includes("w") ? "e" : "w");
    let pending = false, last = null;
    const move = (ev) => {
      const dx = ev.screenX - x0, dy = ev.screenY - y0;
      const w = edge.includes("e") ? w0 + dx : edge.includes("w") ? w0 - dx : w0;
      const hh = edge.includes("s") ? h0 + dy : edge.includes("n") ? h0 - dy : h0;
      last = [w, hh];
      if (pending) return;
      pending = true;
      requestAnimationFrame(() => { pending = false; apiw.resize(last[0], last[1], anchor); });
    };
    const up = () => { window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", up); };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
  }));
}

const TB_STEPS = [["script", "✍️"], ["voice", "🎙️"], ["captions", "💬"], ["render", "🎬"], ["cover image", "🖼️"]];
const TB_LABEL = {
  en: { script: "Script", writing: "Script", voice: "Voice", captions: "Captions", render: "Render", "cover image": "Cover & QC", uploading: "YouTube", null: "Starting" },
  tr: { script: "Senaryo", writing: "Senaryo", voice: "Ses", captions: "Altyazı", render: "Render", "cover image": "Kapak & QC", uploading: "YouTube", null: "Başlıyor" },
};
function tbMmss(s) { s = Math.max(0, Math.round(s)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; }

async function refreshTitlebar() {
  const st = document.getElementById("tbStatus");
  if (!st) return;
  const body = document.getElementById("tbText");
  try {
    const a = await api("/api/activity");
    const r = a.running[0];
    const L = TB_LABEL[lang] || TB_LABEL.en;
    if (r) {
      const step = r.step === "writing" ? "script" : r.step;
      const idx = TB_STEPS.findIndex(([k]) => k === step);
      const icon = r.step === "uploading" ? "⬆️" : (TB_STEPS[idx] || ["", "⚙️"])[1];
      const segs = TB_STEPS.map(([k], i) => `<i class="${i < idx ? "done" : i === idx ? "now" : ""}" title="${esc(L[k] || k)}"></i>`).join("");
      const more = a.counts.running - 1 + a.counts.queued;
      body.innerHTML = `<span class="tb-step">${icon} ${esc(L[r.step] || r.step || L.null)}</span>
        <span class="tb-title">${esc(r.title)}</span>
        <span class="tb-segs">${segs}</span>
        <span class="tb-pct">${Math.round(r.progress * 100)}%</span><span class="tb-time">${tbMmss(r.elapsed_s)}</span>
        ${more > 0 ? `<span class="tb-more">+${more}</span>` : ""}`;
    } else {
      body.innerHTML = `<span class="tb-idle">${esc((a.summary[lang] || a.summary.en).replace(/^●\s*/, ""))}</span>`;
    }
    st.className = "tb-status " + (r ? "busy" : a.counts.queued ? "queued" : "idle");
    document.getElementById("tbBar").style.width = r ? `${Math.round(r.progress * 100)}%` : "0";
  } catch {
    body.textContent = t("offline");
    st.className = "tb-status offline";
  }
}
setInterval(refreshTitlebar, 3000);

function bindAppUpdate() {
  const b = document.getElementById("appUpdate");
  b && b.addEventListener("click", async () => {
    b.disabled = true; b.textContent = t("appUpdating");
    let r;
    try { r = await fetch("/desktop/update", { method: "POST", headers: { "X-MF-Client": "panel" } }); }
    catch { return toast(t("appRestarting")); }  // the app closes itself to install: a dropped connection is expected
    const d = await r.json().catch(() => ({}));
    if (!r.ok) { b.disabled = false; b.textContent = t("appUpdateNow"); return toast(d.detail || r.statusText, true); }
    if (d.manual) { b.disabled = false; b.textContent = t("appUpdateNow"); return toast(t("appDownloadOpened")); }
    toast(t("appRestarting"));
  });
}

function bindShell() {
  bindAppUpdate();
  bindTitlebar();
  refreshTitlebar();
  if (typeof refreshLiveMini === "function") refreshLiveMini();
  on("#lang", "click", (e) => { e.preventDefault(); lang = lang === "tr" ? "en" : "tr"; localStorage.setItem("mf_lang", lang); render(); });
}
window.addEventListener("hashchange", render);
window.addEventListener("pywebviewready", () => { if (desktop && !document.getElementById("titlebar")) render(); });

// ---------- pages ----------
async function overview(el) {
  const [items, jobs] = await Promise.all([api("/api/items?limit=200"), api("/api/jobs?limit=200")]);
  const count = (s) => jobs.items.filter((j) => j.status === s).length;
  const running = jobs.items.filter((j) => !["needs_review", "approved", "rejected", "failed", "published", "scheduled", "script_draft"].includes(j.status)).length;
  el.innerHTML = `<h1>${t("overview")}</h1><p class="sub">${t("welcome")}</p>
    <div class="grid g4">
      <div class="card stat"><b>${items.items.length}</b><span>${t("items")}</span></div>
      <div class="card stat"><b>${running}</b><span>${t("queued")}</span></div>
      <div class="card stat"><b>${count("needs_review")}</b><span>${t("readyN")}</span></div>
      <div class="card stat"><b>${count("approved")}</b><span>${t("approved")}</span></div>
      <div class="card stat"><b>${count("failed")}</b><span>${t("failed")}</span></div>
    </div>
    <h1 style="margin-top:28px;font-size:18px">${t("production")}</h1>${jobsTable(jobs.items.slice(0, 8))}`;
  bindJobs(el);
}

async function sources(el) {
  const data = await api("/api/sources");
  const rows = data.items.map((s) => `<tr>
      <td><b>${esc(s.name)}</b><div class="muted small">${esc(s.adapter)} · ${esc(s.params.subreddit || s.params.url || "")}</div></td>
      <td><label class="switch" title="${s.enabled ? t("enabled") : t("disabledSrc")}"><input type="checkbox" data-toggle-src="${s.id}" ${s.enabled ? "checked" : ""}><span></span></label></td>
      <td class="small">${when(s.last_run_at)}<div class="muted">${s.items_total} ${t("items").toLowerCase()}</div></td>
      <td class="small">${s.last_error ? `<span class="pill bad">${esc(s.last_error).slice(0, 90)}</span>` : "—"}</td>
      <td><div class="row"><button class="btn" data-run="${s.id}">${t("runNow")}</button>
      <button class="btn danger" data-del="${s.id}">${t("delete")}</button></div></td></tr>`).join("");
  el.innerHTML = `<h1>${t("sources")}</h1><p class="sub">Reddit · RSS · Web</p>
    <div class="card" style="margin-bottom:16px" id="catalog"></div>
    <h3 style="margin:22px 0 10px">${t("mySources")}</h3>
    <div class="card" style="margin-bottom:16px"><form id="add" class="grid g4" style="align-items:end">
      <div><label>${t("name")}</label><input name="name" required placeholder="nosleep"></div>
      <div><label>${t("adapter")}</label><select name="adapter"><option value="reddit_rss">Reddit (RSS)</option><option value="reddit">Reddit (API)</option><option value="rss">RSS / Atom</option><option value="web">Web page</option></select></div>
      <div><label>${t("subreddit")} / ${t("url")}</label><input name="target" required placeholder="nosleep"></div>
      <div><label>${t("interval")}</label><input name="interval" type="number" min="10" value="60"></div>
      <div><button class="btn primary">${t("add")}</button></div></form></div>
    <div class="card">${data.items.length ? `<table><tr><th>${t("name")}</th><th>${t("status")}</th><th>${t("lastRun")}</th><th>${t("error")}</th><th></th></tr>${rows}</table>` : `<p class="muted">${t("noData")}</p>`}</div>`;
  drawCatalog(document.getElementById("catalog"));
  document.getElementById("add").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const adapter = f.get("adapter");
    const params = adapter.startsWith("reddit") ? { subreddit: f.get("target"), sort: "top", time: "week" } : { url: f.get("target") };
    try {
      await api("/api/sources", { method: "POST", body: { name: f.get("name"), adapter, params, poll_interval_min: Number(f.get("interval")) } });
      toast(t("sourceAdded")); render();
    } catch (err) { toast(err.message, true); }
  });
  on("[data-toggle-src]", "change", async (e) => {
    const box = e.target;
    try { await api(`/api/sources/${box.dataset.toggleSrc}`, { method: "PATCH", body: { enabled: box.checked } }); toast(box.checked ? t("srcOn") : t("srcOff")); }
    catch (err) { box.checked = !box.checked; toast(err.message, true); }
  });
  on("[data-run]", "click", async (e) => {
    e.target.disabled = true;
    try { const r = await api(`/api/sources/${e.target.dataset.run}/run`, { method: "POST" }); toast(r.error ? r.error : `+${r.new} / =${r.duplicates}`, !!r.error); render(); }
    catch (err) { toast(err.message, true); e.target.disabled = false; }
  });
  on("[data-del]", "click", async (e) => {
    if (!confirm("?")) return;
    try { await api(`/api/sources/${e.target.dataset.del}`, { method: "DELETE" }); render(); } catch (err) { toast(err.message, true); }
  });
}

let catFilter = { lang: "", cat: "" };
async function drawCatalog(box) {
  const c = await api("/api/sources/catalog");
  const cats = c.categories;
  const shown = c.items.filter((i) => (!catFilter.lang || i.language === catFilter.lang) && (!catFilter.cat || i.category === catFilter.cat));
  const missing = shown.filter((i) => !i.source_id);
  const chip = (attr, v, label, on) => `<button class="btn small-btn ${on ? "primary" : ""}" ${attr}="${v}">${label}</button>`;
  box.innerHTML = `<div class="row"><h3 style="margin:0">${t("catalog")}</h3><span class="spacer"></span>
      <button class="btn primary" id="addShown" ${missing.length ? "" : "disabled"}>＋ ${t("addShown")} (${missing.length})</button></div>
    <p class="muted small">${t("catalogHelp")}</p>
    <div class="row" style="margin:6px 0">${chip("data-clang", "", t("allLangs"), !catFilter.lang)}${chip("data-clang", "en", "English", catFilter.lang === "en")}${chip("data-clang", "tr", "Türkçe", catFilter.lang === "tr")}</div>
    <div class="row" style="margin:6px 0 14px">${chip("data-ccat", "", t("allTypes"), !catFilter.cat)}${Object.entries(cats).map(([k, v]) => chip("data-ccat", k, esc(v[lang] || v.en), catFilter.cat === k)).join("")}</div>
    <div class="cat-grid">${shown.map((i) => `<div class="cat-item">
        <div class="row"><b>${esc(i.name)}</b><span class="spacer"></span><span class="pill">${i.language.toUpperCase()}</span></div>
        <div class="muted small">${esc((cats[i.category] || {})[lang] || i.category)} · ${i.adapter === "reddit_rss" ? "Reddit" : "RSS"}</div>
        <p class="small" style="margin:6px 0 10px">${esc(i.about[lang] || i.about.en)}</p>
        ${i.source_id ? `<span class="pill ok">✓ ${t("added")}</span>` : `<button class="btn small-btn" data-cadd="${i.key}">＋ ${t("add")}</button>`}
      </div>`).join("")}</div>`;
  const add = async (keys) => {
    try { const r = await api("/api/sources/catalog/add", { method: "POST", body: { keys } }); toast(`+${r.added.length} ${t("sourcesAdded")}`); render(); }
    catch (err) { toast(err.message, true); }
  };
  box.querySelectorAll("[data-clang]").forEach((b) => b.addEventListener("click", () => { catFilter.lang = b.dataset.clang; drawCatalog(box); }));
  box.querySelectorAll("[data-ccat]").forEach((b) => b.addEventListener("click", () => { catFilter.cat = b.dataset.ccat; drawCatalog(box); }));
  box.querySelectorAll("[data-cadd]").forEach((b) => b.addEventListener("click", () => add([b.dataset.cadd])));
  box.querySelector("#addShown").addEventListener("click", () => add(missing.map((i) => i.key)));
}

async function inbox(el) {
  const hp = new URLSearchParams(location.hash.split("?")[1] || "");
  const q = hp.get("q") || "", il = hp.get("lang") || "";
  const data = await api(`/api/items?limit=150${q ? "&q=" + encodeURIComponent(q) : ""}${il ? "&language=" + il : ""}`);
  const rows = data.items.map((i) => `<tr>
      <td><span class="pill">${(i.language || "en").toUpperCase()}</span> <b class="clip">${esc(i.title)}</b><div class="muted small clip">${esc(i.text)}</div></td>
      <td><span class="pill">${esc(i.rights_status)}</span></td>
      <td>${pill(i.processing_status)}</td>
      <td class="small muted">${i.chars} ${t("chars")}<br>${when(i.fetched_at)}</td>
      <td><div class="row"><button class="btn primary" data-make="${i.id}">${t("make")}</button><button class="btn" data-open="${i.id}">${t("open")}</button></div></td></tr>`).join("");
  el.innerHTML = `<div class="row"><h1>${t("inbox")}</h1><span class="spacer"></span><input id="q" style="max-width:260px" placeholder="${t("search")}" value="${esc(q)}"><button class="btn" id="aiStory">✨ ${st("aiStory")}</button><button class="btn primary" id="addStory">＋ ${st("addStory")}</button></div>
    <div class="row" style="margin:4px 0 14px">${[["", t("allLangs")], ["en", "English"], ["tr", "Türkçe"]].map(([v, l]) => `<a class="btn small-btn ${il === v ? "primary" : ""}" href="#inbox?lang=${v}${q ? "&q=" + encodeURIComponent(q) : ""}">${l}</a>`).join("")}
      <span class="muted small" style="margin-left:8px">${data.items.length} ${t("items").toLowerCase()}</span></div>
    <div class="card">${data.items.length ? `<table><tr><th></th><th>${t("rights")}</th><th>${t("status")}</th><th></th><th></th></tr>${rows}</table>` : `<p class="muted">${t("noData")}</p>`}</div>`;
  document.getElementById("addStory").addEventListener("click", () => addStoryDialog(() => render()));
  document.getElementById("aiStory").addEventListener("click", () => aiStoryDialog(() => render()));
  document.getElementById("q").addEventListener("change", (e) => { location.hash = "#inbox?q=" + encodeURIComponent(e.target.value) + (il ? "&lang=" + il : ""); });
  on("[data-make]", "click", (e) => { studioState = null; location.hash = `#studio/${e.target.dataset.make}`; });
  on("[data-open]", "click", async (e) => {
    const d = await api(`/api/items/${e.target.dataset.open}`);
    modal(`<h1>${esc(d.item.title)}</h1><p class="muted small">${esc(d.item.canonical_url || "")}</p><pre>${esc(d.item.text)}</pre>`);
  });
}

function modal(html) {
  const m = document.createElement("div");
  m.className = "modal";
  m.innerHTML = `<div class="card">${html}<div class="row" style="margin-top:14px"><span class="spacer"></span><button class="btn" data-close>${t("close")}</button></div></div>`;
  m.addEventListener("click", (e) => { if (e.target === m || e.target.hasAttribute("data-close")) m.remove(); });
  document.body.appendChild(m);
  return m;
}

function qcBadge(j) {
  if (!j.qc) return "";
  const bad = j.qc.checks.filter((c) => !c.ok).length;
  return `<a href="#" class="pill ${bad ? "warn" : "ok"}" data-qc="${j.id}" onclick="event.preventDefault()">${bad ? `⚠ QC · ${bad}` : "✓ QC"}</a>`;
}

function jobsTable(items) {
  if (!items.length) return `<div class="card"><p class="muted">${t("noData")}</p></div>`;
  const rows = items.map((j) => `<tr>
      <td><b>#${j.id}</b> <span class="muted">${esc(j.language || "")}</span><div class="clip">${esc(j.title || "")}</div></td>
      <td>${pill(j.status)}</td><td class="small muted">${when(j.updated_at)}</td>
      <td><div class="row"><button class="btn" data-job="${j.id}">${t("open")}</button>
      ${j.status === "script_draft" ? `<button class="btn primary" data-edit-script="${j.id}">✎ ${st("reviewScript")}</button>` : ""}
      ${j.status === "failed" ? `<button class="btn" data-retry="${j.id}">${t("retry")}</button>` : ""}
      ${["discovered", "retry_wait"].includes(j.status) ? `<button class="btn danger" data-cancel="${j.id}">${t("cancel")}</button>` : ""}</div></td></tr>`).join("");
  return `<div class="card"><table><tr><th></th><th>${t("status")}</th><th></th><th></th></tr>${rows}</table></div>`;
}
function doctorLine(d) {
  if (!d || d.score == null) return "";
  const first = d.revised ? ` · ${t("doctorFrom")} ${d.first_score}/10` : "";
  const notes = (d.problems || []).length ? `<br>${t("doctorNotes")}: ${d.problems.map(esc).join(" · ")}` : "";
  return `<p class="muted small">🩺 Script Doctor: <b>${d.score}/10</b>${first}${notes}</p>`;
}
function bindJobs(el) {
  on("[data-job]", "click", async (e) => {
    const j = await api(`/api/jobs/${e.target.dataset.job}`);
    const stages = (j.stages || []).map((s) => `<div class="card" style="margin:8px 0"><b>${esc(s.stage)}</b> ${pill(s.state)} <span class="muted small">×${s.attempts}</span>
      ${s.error ? `<pre>${esc(s.error)}</pre>` : ""}${s.log ? `<pre>${esc(s.log)}</pre>` : ""}</div>`).join("");
    modal(`<h1>#${j.id} ${esc(j.title || "")}</h1>${pill(j.status)}
      ${j.has_video ? `<video controls src="/api/jobs/${j.id}/video" style="width:100%;max-height:60vh;margin-top:12px;background:#000;border-radius:10px"></video>` : ""}
      ${j.script ? `<h3>${t("script")}</h3>${doctorLine(j.script.doctor)}<pre>${esc(j.script.narration)}</pre>` : ""}<h3>${t("stages")}</h3>${stages}`);
  });
  on("[data-edit-script]", "click", (e) => scriptEditor(e.target.dataset.editScript));
  on("[data-retry]", "click", async (e) => { try { await api(`/api/jobs/${e.target.dataset.retry}/retry`, { method: "POST" }); render(); } catch (err) { toast(err.message, true); } });
  on("[data-cancel]", "click", async (e) => { try { await api(`/api/jobs/${e.target.dataset.cancel}/cancel`, { method: "POST" }); render(); } catch (err) { toast(err.message, true); } });
}

async function production(el) {
  const data = await api("/api/jobs?limit=100");
  const drafts = data.items.filter((j) => j.status === "script_draft").length;
  el.innerHTML = `<h1>${t("production")}</h1><p class="sub">script → voice → captions → render</p>
    ${drafts ? `<div class="card banner">✎ ${drafts} ${st("draftsWaiting")}</div>` : ""}${jobsTable(data.items)}`;
  bindJobs(el);
  if (data.items.some((j) => !["needs_review", "approved", "rejected", "failed", "published", "scheduled", "script_draft"].includes(j.status))) {
    pollTimer = setInterval(() => { if (route() === "production" && !document.querySelector(".modal")) render(); }, 5000);
  }
}

async function ready(el) {
  const [data, approved, pub] = await Promise.all([api("/api/jobs?status=needs_review&limit=100"), api("/api/jobs?status=approved&limit=100"),
    Promise.all(["uploading", "scheduled", "published"].map((x) => api(`/api/jobs?status=${x}&limit=100`)))]);
  const published = pub.flatMap((r) => r.items);
  await loadInstagram();
  const byJob = Object.fromEntries([...data.items, ...approved.items, ...published].map((j) => [String(j.id), j]));
  const card = (j, actions) => `<div class="card video-card"><video controls preload="none" poster="/api/jobs/${j.id}/poster" src="/api/jobs/${j.id}/video"></video>
      <h3>${esc(j.title || "")}</h3><div class="muted small">#${j.id} · ${esc(j.language)} · ${j.duration_s ?? "?"}s</div>
      <div class="row" style="margin-top:6px;gap:6px">${qcBadge(j)}${ytBadge(j)}</div>
      <div class="row" style="margin-top:10px">${actions}<a class="btn" href="/api/jobs/${j.id}/video" download>${t("download")}</a>${j.has_thumbnail ? `<a class="btn" href="/api/jobs/${j.id}/thumbnail" download>${t("cover")}</a>` : ""}</div></div>`;
  const ytBtn = (j) => publishButtons(j);
  el.innerHTML = `<h1>${t("ready")}</h1><p class="sub">${t("readyHint")}</p>
    <div class="grid videos">${data.items.map((j) => card(j, `<button class="btn primary" data-dec="approve" data-id="${j.id}">${t("approve")}</button><button class="btn danger" data-dec="reject" data-id="${j.id}">${t("reject")}</button><button class="btn" data-edit-script="${j.id}">✎ ${st("editRerender")}</button>`)).join("") || `<p class="muted">${t("noData")}</p>`}</div>
    ${approved.items.length ? `<h1 style="margin-top:28px;font-size:18px">${t("approved")}</h1><div class="grid videos">${approved.items.map((j) => card(j, ytBtn(j) + `<button class="btn" data-edit-script="${j.id}">✎ ${st("editRerender")}</button>`)).join("")}</div>` : ""}
    ${published.length ? `<h1 style="margin-top:28px;font-size:18px">${sc("publishedList")}</h1><div class="grid videos">${published.map((j) => card(j, publishButtons(j))).join("")}</div>` : ""}`;
  on("[data-dec]", "click", async (e) => {
    try { await api(`/api/jobs/${e.target.dataset.id}/decision`, { method: "POST", body: { decision: e.target.dataset.dec } }); render(); }
    catch (err) { toast(err.message, true); }
  });
  on("[data-pub]", "click", (e) => publishDialog(e.target.dataset.pub, byJob[e.target.dataset.pub]));
  on("[data-igman]", "click", (e) => manualInstagram(e.target.dataset.igman));
  on("[data-qc]", "click", (e) => {
    const j = [...data.items, ...approved.items, ...published].find((x) => String(x.id) === e.currentTarget.dataset.qc);
    if (!j || !j.qc) return;
    modal(`<h1>${t("qcTitle")} · #${j.id}</h1><table>${j.qc.checks.map((c) => `<tr><td>${c.ok ? "✓" : "⚠"}</td><td><b>${esc(t("qc_" + c.name))}</b></td><td class="muted">${esc(c.value)}</td></tr>`).join("")}</table>`);
  });
  on("[data-edit-script]", "click", (e) => scriptEditor(e.target.dataset.editScript));
  on("[data-ext]", "click", (e) => { e.preventDefault(); openExternal(e.target.dataset.ext); });
  if (published.some((j) => j.status === "uploading")) {
    pollTimer = setInterval(() => { if (route() === "ready" && !document.querySelector(".modal")) render(); }, 6000);
  }
}

function offlineCard() {
  if (!desktop) return "";
  return `<div class="card" style="margin-bottom:16px;border-color:#E0A800"><h3>⚠ ${t("offTitle")}</h3>
    <p>${t("offWhy")}</p><p>${t("offSteps")}</p>
    <p class="muted small">${t("offAddr")}: <code>${esc(desktop.server_url)}</code></p>
    <div class="row"><button class="btn primary" id="offRetry">↻ ${t("offRetry")}</button><button class="btn" id="offGet">⬇ ${t("offGet")}</button></div></div>`;
}
function bindOfflineCard() {
  const r = document.getElementById("offRetry"), g = document.getElementById("offGet");
  r && r.addEventListener("click", () => { desktop = null; render(); });
  g && g.addEventListener("click", () => openExternal("https://tailscale.com/download/windows"));
}
function serverCard() {
  if (!desktop) return "";
  return `<div class="card" style="margin-bottom:16px"><h3>${t("server")}</h3><p class="muted small">${t("serverHelp")}</p>
    <form id="srv" class="row"><input name="url" value="${esc(desktop.server_url)}" placeholder="http://mediafactory:8080" style="flex:1;min-width:220px">
    <button class="btn primary">${t("save")}</button></form>
    <label class="row small" style="margin-top:12px;gap:8px"><span class="switch"><input type="checkbox" id="notifToggle" ${desktop.notifications === false ? "" : "checked"}><span></span></span> ${t("notifLabel")}</label>
    <p class="muted small" style="margin:6px 0 0">v${esc(desktop.app_version || "")}</p></div>`;
}
function bindServerCard() {
  const f = document.getElementById("srv");
  if (!f) return;
  const nt = document.getElementById("notifToggle");
  nt && nt.addEventListener("change", async () => {
    await fetch("/desktop/config", { method: "POST", headers: { "Content-Type": "application/json", "X-MF-Client": "panel" },
      body: JSON.stringify({ notifications: nt.checked }) });
    desktop.notifications = nt.checked; toast(t("saved"));
  });
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const r = await fetch("/desktop/config", { method: "POST", headers: { "Content-Type": "application/json", "X-MF-Client": "panel" },
      body: JSON.stringify({ server_url: new FormData(f).get("url") }) });
    const d = await r.json();
    if (!r.ok) return toast(d.detail || "error", true);
    desktop = d; toast(d.reachable ? t("connected") : t("offline"), !d.reachable); render();
  });
}
async function updatesCard() {
  let s;
  try { s = await api("/api/system"); } catch { return ""; }
  const u = s.update;
  const short = (x) => (x ? esc(String(x).slice(0, 7)) : "—");
  const state = u ? (t("upd_" + u.state) !== "upd_" + u.state ? t("upd_" + u.state) : esc(u.state)) : "";
  const body = u
    ? `<table><tr><td class="muted">${t("updVersion")}</td><td><b>v${esc(s.version)}</b> · <a href="${esc(s.repository)}/commit/${esc(u.current || "")}" data-ext="${esc(s.repository)}/commit/${esc(u.current || "")}">${short(u.current)}</a></td></tr>
        <tr><td class="muted">${t("updLatest")}</td><td>${short(u.latest)} <span class="muted">(${esc(u.branch || "main")})</span></td></tr>
        <tr><td class="muted">${t("updState")}</td><td><span class="pill ${["updated", "up_to_date"].includes(u.state) ? "ok" : ["failed", "error", "rolled_back"].includes(u.state) ? "bad" : "warn"}">${state}</span> <span class="muted small">${esc(u.message || "")}</span></td></tr>
        <tr><td class="muted">${t("updChecked")}</td><td>${when(u.checked_at)}${u.last_update_at ? ` · ${t("updLast")}: ${when(u.last_update_at)}` : ""}</td></tr></table>
      ${s.log ? `<details style="margin-top:8px"><summary class="muted small">${t("updLog")}</summary><pre>${esc(s.log)}</pre></details>` : ""}`
    : `<p class="muted small">${t("updMissing")}</p><pre>sudo bash deploy/update/install-autoupdate.sh</pre>`;
  return `<div class="card" style="margin-bottom:16px"><div class="row"><h3 style="margin:0">${t("updates")}</h3><span class="spacer"></span>
      <label class="row small" style="margin:0;gap:8px">${t("updAuto")} <span class="switch"><input type="checkbox" id="updAuto" ${s.auto ? "checked" : ""}><span></span></span></label></div>
    <p class="muted small">${t("updHelp")}</p>${body}
    <div class="row" style="margin-top:12px"><button class="btn primary" id="updNow" ${s.pending ? "disabled" : ""}>⟳ ${s.pending ? t("updPending") : t("updNow")}</button></div></div>`;
}

function bindUpdatesCard() {
  const auto = document.getElementById("updAuto");
  if (!auto) return;
  auto.addEventListener("change", async () => {
    try { await api("/api/system/update-config", { method: "PUT", body: { auto: auto.checked } }); toast(t("saved")); }
    catch (err) { auto.checked = !auto.checked; toast(err.message, true); }
  });
  document.getElementById("updNow").addEventListener("click", async (e) => {
    e.target.disabled = true;
    try {
      await api("/api/system/update", { method: "POST", body: {} });
      toast(t("updRequested"));
      // The server restarts while updating: keep asking until it is back, then reload the panel.
      let n = 0;
      const timer = setInterval(async () => {
        n += 1;
        try {
          const s = await api("/api/system");
          if (!s.pending && s.update && !["updating"].includes(s.update.state)) { clearInterval(timer); location.reload(); }
        } catch { /* restarting */ }
        if (n > 120) clearInterval(timer);
      }, 5000);
    } catch (err) { toast(err.message, true); e.target.disabled = false; }
  });
  on("[data-ext]", "click", (ev) => { ev.preventDefault(); openExternal(ev.currentTarget.dataset.ext); });
}

function backupCard() {
  return `<div class="card" style="margin-bottom:16px"><h3>${t("backup")}</h3><p class="muted small">${t("backupHelp")}</p>
    <div class="grid g2">
      <form id="expf"><label>${t("expPassword")}</label><input name="password" type="password" minlength="6" autocomplete="new-password" placeholder="${esc(t("expPasswordPh"))}">
        <div class="row" style="margin-top:10px"><button class="btn primary">⬇ ${t("export")}</button></div></form>
      <form id="impf"><label>${t("impFile")}</label><input type="file" name="file" accept=".json,application/json" required>
        <label>${t("impPassword")}</label><input name="password" type="password" autocomplete="off">
        <div class="row" style="margin-top:10px"><button class="btn">⬆ ${t("import")}</button></div></form>
    </div></div>`;
}

function bindBackupCard() {
  const ef = document.getElementById("expf"), inf = document.getElementById("impf");
  if (!ef) return;
  ef.addEventListener("submit", async (e) => {
    e.preventDefault();
    const pw = ef.password.value;
    const r = await fetch("/api/settings/export", { method: "POST", headers: { "Content-Type": "application/json", "X-MF-Client": "panel" },
      body: JSON.stringify({ password: pw || null }) });
    if (!r.ok) return toast((await r.json().catch(() => ({}))).detail || r.statusText, true);
    const name = (r.headers.get("Content-Disposition") || "").match(/filename="([^"]+)"/);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(await r.blob()); a.download = name ? name[1] : "mediafactory-settings.json";
    document.body.appendChild(a); a.click(); a.remove();
    toast(pw ? t("exportedWithKeys") : t("exportedNoKeys"));
  });
  inf.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(inf);
    try {
      const r = await api("/api/settings/import", { method: "POST", body: fd });
      toast(`${t("imported")}: ${r.providers} AI · ${r.routes} ${t("routes").toLowerCase()} · ${r.sources} ${t("sources").toLowerCase()} · ${r.schedules} ${t("schedulesN")} · ${r.channels} YouTube`);
      render();
    } catch (err) { toast(err.message, true); }
  });
}

async function settings(el) {
  let prov, routes, creds;
  try {
    [prov, routes, creds] = await Promise.all([api("/api/providers"), api("/api/task-routes"), api("/api/source-credentials")]);
  } catch (err) {
    el.innerHTML = `<h1>${t("settings")}</h1>${offlineCard()}${serverCard()}`;
    bindOfflineCard();
    return bindServerCard();
  }
  const pRows = prov.items.map((p) => `<tr><td><b>${esc(p.name)}</b><div class="muted small">${esc(p.base_url)}</div></td>
      <td>${p.locality}</td><td>${p.has_api_key ? "🔑" : "—"}</td><td><button class="btn" data-test="${p.id}">${t("test")}</button></td></tr>`).join("");
  const rRows = routes.items.map((r) => `<tr><td><b>${esc(r.task)}</b></td><td class="small">${r.steps.map((s) => esc(s.model)).join(" → ")}</td><td class="small muted">${r.rounds}× / ${r.retry_delay_s}s</td></tr>`).join("");
  const [yt, ig, upd, cr, sk] = await Promise.all([youtubeCard(), instagramCard(), updatesCard(), creditCard(), stockKeyCard()]);
  el.innerHTML = `<h1>${t("settings")}</h1><p class="sub">AI · YouTube · Instagram · Reddit</p>${serverCard()}${upd}${yt}${ig}${cr}${sk}${backupCard()}
    <div class="card" style="margin-bottom:16px"><h3>${t("providers")}</h3>
      ${pRows ? `<table>${pRows}</table>` : `<p class="muted">${t("noData")}</p>`}
      <form id="prov" class="grid g4" style="align-items:end;margin-top:12px">
        <div><label>${t("name")}</label><input name="name" required placeholder="router"></div>
        <div><label>${t("baseUrl")}</label><input name="base_url" required placeholder="http://ai-router:20128/v1"></div>
        <div><label>${t("apiKey")}</label><input name="api_key" type="password" autocomplete="off"></div>
        <div><button class="btn primary">${t("add")}</button></div></form></div>
    <div class="card" style="margin-bottom:16px"><h3>${t("routes")}</h3>${rRows ? `<table>${rRows}</table>` : `<p class="muted">${t("noData")}</p>`}
      <form id="route" class="grid g4" style="align-items:end;margin-top:12px">
        <div><label>Task</label><select name="task"><option>script</option><option>classify</option></select></div>
        <div><label>Provider</label><select name="pid">${prov.items.map((p) => `<option value="${p.id}">${esc(p.name)}</option>`).join("")}</select></div>
        <div><label>${t("model")}</label><input name="model" required placeholder="mf-senaryo"></div>
        <div><button class="btn primary">${t("save")}</button></div></form></div>
    <div class="card"><h3>${t("reddit")}</h3><p class="muted small">${creds.reddit.configured ? "✓ " + esc(creds.reddit.client_id) : "—"}</p>
      <form id="cred" class="grid g4" style="align-items:end">
        <div><label>${t("clientId")}</label><input name="client_id" required></div>
        <div><label>${t("clientSecret")}</label><input name="client_secret" type="password" required autocomplete="off"></div>
        <div><button class="btn primary">${t("save")}</button></div></form></div>`;
  bindServerCard();
  bindYoutubeCard();
  bindInstagramCard();
  bindCreditCard();
  bindStockKeyCard();
  bindUpdatesCard();
  bindBackupCard();
  on("[data-test]", "click", async (e) => { const r = await api(`/api/providers/${e.target.dataset.test}/test`, { method: "POST" }); toast(r.ok ? `OK · ${r.models.length} models` : r.error, !r.ok); });
  document.getElementById("prov").addEventListener("submit", async (e) => {
    e.preventDefault(); const f = new FormData(e.target);
    try { await api("/api/providers", { method: "POST", body: { name: f.get("name"), base_url: f.get("base_url"), api_key: f.get("api_key") || null } }); toast(t("saved")); render(); } catch (err) { toast(err.message, true); }
  });
  document.getElementById("route").addEventListener("submit", async (e) => {
    e.preventDefault(); const f = new FormData(e.target);
    try { await api(`/api/task-routes/${f.get("task")}`, { method: "PUT", body: { steps: [{ provider_id: Number(f.get("pid")), model: f.get("model") }] } }); toast(t("saved")); render(); } catch (err) { toast(err.message, true); }
  });
  document.getElementById("cred").addEventListener("submit", async (e) => {
    e.preventDefault(); const f = new FormData(e.target);
    try { await api("/api/source-credentials/reddit", { method: "PUT", body: { client_id: f.get("client_id"), client_secret: f.get("client_secret") } }); toast(t("saved")); render(); } catch (err) { toast(err.message, true); }
  });
}

render();
