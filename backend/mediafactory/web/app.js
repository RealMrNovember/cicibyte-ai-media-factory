// CiciByte AI Media Factory panel — no build step. Powered by CiciByte Technology.
"use strict";

const I18N = {
  en: {
    overview: "Overview", sources: "Sources", inbox: "Inbox", production: "Production", ready: "Ready videos",
    settings: "Settings", server: "Server", serverHelp: "Production runs on this server. Address of your Media Factory server.", connected: "Connected", offline: "Cannot reach the server — set its address in Settings.", logout: "Log out", login: "Log in", email: "E-mail", password: "Password",
    welcome: "Your self-hosted AI media factory.", items: "Items", queued: "In production", readyN: "Ready",
    approved: "Approved", failed: "Failed", add: "Add", name: "Name", adapter: "Adapter", runNow: "Collect now",
    lastRun: "Last run", status: "Status", error: "Error", make: "Make video", makeTitle: "Make a Short",
    languages: "Languages", seconds: "Target seconds", start: "Start", cancel: "Cancel", retry: "Retry",
    approve: "Approve", reject: "Reject", download: "Download", noData: "Nothing here yet.", search: "Search…",
    rights: "Rights", chars: "chars", open: "Open", close: "Close", save: "Save", providers: "AI providers",
    routes: "Task routes", baseUrl: "Base URL", apiKey: "API key", test: "Test", model: "Model",
    reddit: "Reddit API credentials", clientId: "Client id", clientSecret: "Client secret", enabled: "Enabled",
    subreddit: "Subreddit", url: "Feed / page URL", interval: "Every (minutes)", delete: "Delete",
    script: "Script", stages: "Stages", support: "Support", poweredBy: "Powered by",
    makeStarted: "Production started", saved: "Saved", sourceAdded: "Source added",
    readyHint: "Rendered videos waiting for your approval.",
  },
  tr: {
    overview: "Genel Bakış", sources: "Kaynaklar", inbox: "Gelen Kutusu", production: "Üretim", ready: "Hazır Videolar",
    settings: "Ayarlar", server: "Sunucu", serverHelp: "Üretim bu sunucuda çalışır. Media Factory sunucunuzun adresi.", connected: "Bağlandı", offline: "Sunucuya ulaşılamıyor — adresini Ayarlar'dan girin.", logout: "Çıkış", login: "Giriş", email: "E-posta", password: "Parola",
    welcome: "Kendi sunucunda çalışan yapay zekâ medya fabrikan.", items: "Öğe", queued: "Üretimde", readyN: "Hazır",
    approved: "Onaylı", failed: "Hatalı", add: "Ekle", name: "Ad", adapter: "Adaptör", runNow: "Şimdi topla",
    lastRun: "Son çalışma", status: "Durum", error: "Hata", make: "Video üret", makeTitle: "Shorts üret",
    languages: "Diller", seconds: "Hedef süre (sn)", start: "Başlat", cancel: "İptal", retry: "Yeniden dene",
    approve: "Onayla", reject: "Reddet", download: "İndir", noData: "Henüz bir şey yok.", search: "Ara…",
    rights: "Hak", chars: "karakter", open: "Aç", close: "Kapat", save: "Kaydet", providers: "AI sağlayıcıları",
    routes: "Görev rotaları", baseUrl: "Taban adres", apiKey: "API anahtarı", test: "Test et", model: "Model",
    reddit: "Reddit API kimlik bilgileri", clientId: "Client id", clientSecret: "Client secret", enabled: "Etkin",
    subreddit: "Subreddit", url: "Besleme / sayfa adresi", interval: "Sıklık (dakika)", delete: "Sil",
    script: "Senaryo", stages: "Aşamalar", support: "Destek ol", poweredBy: "Powered by",
    makeStarted: "Üretim başladı", saved: "Kaydedildi", sourceAdded: "Kaynak eklendi",
    readyHint: "Render edilmiş, onayını bekleyen videolar.",
  },
};
let lang = localStorage.getItem("mf_lang") || (navigator.language || "en").slice(0, 2);
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
  const cls = { approved: "ok", needs_review: "ok", published: "ok", failed: "bad", rejected: "bad", retry_wait: "warn", discovered: "warn" }[status] || "";
  return `<span class="pill ${cls}">${esc(status)}</span>`;
}
function on(sel, ev, fn) { document.querySelectorAll(sel).forEach((el) => el.addEventListener(ev, fn)); }

// ---------- layout ----------
const ROUTES = ["overview", "studio", "sources", "inbox", "production", "ready", "settings"];
function route() { const r = (location.hash || "#overview").slice(1).split("/")[0]; return ROUTES.includes(r) ? r : "overview"; }

function shell(inner) {
  const nav = ROUTES.map((r) => `<a href="#${r}" class="${route() === r ? "on" : ""}">${r === "studio" ? st(r) : t(r)}</a>`).join("");
  return `<div class="shell">
    <aside class="side">
      <div class="brand">CiciByte AI Media Factory<small>${desktop ? esc(desktop.server_url) : ""}</small></div>
      <nav class="nav">${nav}</nav>
      <div class="grow"></div>
      <div class="foot">
        <a href="#" id="lang">${lang === "tr" ? "English" : "Türkçe"}</a><br>
        ${t("poweredBy")} <a href="https://cicibyte.com" target="_blank" rel="noopener">CiciByte Technology</a><br>
        <a href="https://buymeacoffee.com/mikeross" target="_blank" rel="noopener">☕ ${t("support")}</a>
      </div>
    </aside>
    <main class="main">${offline ? `<div class="card banner">${t("offline")} <a href="#settings">${t("settings")} →</a></div>` : ""}<div id="main">${inner}</div></main>
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
  const page = { overview, studio, sources, inbox, production, ready, settings }[route()];
  try { await page(document.getElementById("main")); } catch (err) {
    if (offline && route() !== "settings") { $app.innerHTML = shell(`<h1>${t(route())}</h1><p class="muted">${t("offline")}</p>`); bindShell(); }
    else toast(err.message, true);
  }
}
function bindShell() {
  on("#lang", "click", (e) => { e.preventDefault(); lang = lang === "tr" ? "en" : "tr"; localStorage.setItem("mf_lang", lang); render(); });
}
window.addEventListener("hashchange", render);

// ---------- pages ----------
async function overview(el) {
  const [items, jobs] = await Promise.all([api("/api/items?limit=200"), api("/api/jobs?limit=200")]);
  const count = (s) => jobs.items.filter((j) => j.status === s).length;
  const running = jobs.items.filter((j) => !["needs_review", "approved", "rejected", "failed", "published"].includes(j.status)).length;
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
      <td>${s.enabled ? `<span class="pill ok">${t("enabled")}</span>` : `<span class="pill">off</span>`}</td>
      <td class="small">${when(s.last_run_at)}<div class="muted">${s.items_total} ${t("items").toLowerCase()}</div></td>
      <td class="small">${s.last_error ? `<span class="pill bad">${esc(s.last_error).slice(0, 90)}</span>` : "—"}</td>
      <td><div class="row"><button class="btn" data-run="${s.id}">${t("runNow")}</button>
      <button class="btn danger" data-del="${s.id}">${t("delete")}</button></div></td></tr>`).join("");
  el.innerHTML = `<h1>${t("sources")}</h1><p class="sub">Reddit · RSS · Web</p>
    <div class="card" style="margin-bottom:16px"><form id="add" class="grid g4" style="align-items:end">
      <div><label>${t("name")}</label><input name="name" required placeholder="nosleep"></div>
      <div><label>${t("adapter")}</label><select name="adapter"><option value="reddit_rss">Reddit (RSS)</option><option value="reddit">Reddit (API)</option><option value="rss">RSS / Atom</option><option value="web">Web page</option></select></div>
      <div><label>${t("subreddit")} / ${t("url")}</label><input name="target" required placeholder="nosleep"></div>
      <div><label>${t("interval")}</label><input name="interval" type="number" min="10" value="60"></div>
      <div><button class="btn primary">${t("add")}</button></div></form></div>
    <div class="card">${data.items.length ? `<table><tr><th>${t("name")}</th><th>${t("status")}</th><th>${t("lastRun")}</th><th>${t("error")}</th><th></th></tr>${rows}</table>` : `<p class="muted">${t("noData")}</p>`}</div>`;
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

async function inbox(el) {
  const q = new URLSearchParams(location.hash.split("?")[1] || "").get("q") || "";
  const data = await api(`/api/items?limit=100${q ? "&q=" + encodeURIComponent(q) : ""}`);
  const rows = data.items.map((i) => `<tr>
      <td><b class="clip">${esc(i.title)}</b><div class="muted small clip">${esc(i.text)}</div></td>
      <td><span class="pill">${esc(i.rights_status)}</span></td>
      <td>${pill(i.processing_status)}</td>
      <td class="small muted">${i.chars} ${t("chars")}<br>${when(i.fetched_at)}</td>
      <td><div class="row"><button class="btn primary" data-make="${i.id}">${t("make")}</button><button class="btn" data-open="${i.id}">${t("open")}</button></div></td></tr>`).join("");
  el.innerHTML = `<div class="row"><h1>${t("inbox")}</h1><span class="spacer"></span><input id="q" style="max-width:260px" placeholder="${t("search")}" value="${esc(q)}"></div>
    <p class="sub">${data.items.length} ${t("items").toLowerCase()}</p>
    <div class="card">${data.items.length ? `<table><tr><th></th><th>${t("rights")}</th><th>${t("status")}</th><th></th><th></th></tr>${rows}</table>` : `<p class="muted">${t("noData")}</p>`}</div>`;
  document.getElementById("q").addEventListener("change", (e) => { location.hash = "#inbox?q=" + encodeURIComponent(e.target.value); });
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

function jobsTable(items) {
  if (!items.length) return `<div class="card"><p class="muted">${t("noData")}</p></div>`;
  const rows = items.map((j) => `<tr>
      <td><b>#${j.id}</b> <span class="muted">${esc(j.language || "")}</span><div class="clip">${esc(j.title || "")}</div></td>
      <td>${pill(j.status)}</td><td class="small muted">${when(j.updated_at)}</td>
      <td><div class="row"><button class="btn" data-job="${j.id}">${t("open")}</button>
      ${j.status === "failed" ? `<button class="btn" data-retry="${j.id}">${t("retry")}</button>` : ""}
      ${["discovered", "retry_wait"].includes(j.status) ? `<button class="btn danger" data-cancel="${j.id}">${t("cancel")}</button>` : ""}</div></td></tr>`).join("");
  return `<div class="card"><table><tr><th></th><th>${t("status")}</th><th></th><th></th></tr>${rows}</table></div>`;
}
function bindJobs(el) {
  on("[data-job]", "click", async (e) => {
    const j = await api(`/api/jobs/${e.target.dataset.job}`);
    const stages = (j.stages || []).map((s) => `<div class="card" style="margin:8px 0"><b>${esc(s.stage)}</b> ${pill(s.state)} <span class="muted small">×${s.attempts}</span>
      ${s.error ? `<pre>${esc(s.error)}</pre>` : ""}${s.log ? `<pre>${esc(s.log)}</pre>` : ""}</div>`).join("");
    modal(`<h1>#${j.id} ${esc(j.title || "")}</h1>${pill(j.status)}
      ${j.has_video ? `<video controls src="/api/jobs/${j.id}/video" style="width:100%;max-height:60vh;margin-top:12px;background:#000;border-radius:10px"></video>` : ""}
      ${j.script ? `<h3>${t("script")}</h3><pre>${esc(j.script.narration)}</pre>` : ""}<h3>${t("stages")}</h3>${stages}`);
  });
  on("[data-retry]", "click", async (e) => { try { await api(`/api/jobs/${e.target.dataset.retry}/retry`, { method: "POST" }); render(); } catch (err) { toast(err.message, true); } });
  on("[data-cancel]", "click", async (e) => { try { await api(`/api/jobs/${e.target.dataset.cancel}/cancel`, { method: "POST" }); render(); } catch (err) { toast(err.message, true); } });
}

async function production(el) {
  const data = await api("/api/jobs?limit=100");
  el.innerHTML = `<h1>${t("production")}</h1><p class="sub">script → voice → captions → render</p>${jobsTable(data.items)}`;
  bindJobs(el);
  if (data.items.some((j) => !["needs_review", "approved", "rejected", "failed", "published"].includes(j.status))) {
    pollTimer = setInterval(() => { if (route() === "production" && !document.querySelector(".modal")) render(); }, 5000);
  }
}

async function ready(el) {
  const data = await api("/api/jobs?status=needs_review&limit=100");
  const approved = await api("/api/jobs?status=approved&limit=100");
  const card = (j, actions) => `<div class="card video-card"><video controls preload="metadata" src="/api/jobs/${j.id}/video"></video>
      <h3>${esc(j.title || "")}</h3><div class="muted small">#${j.id} · ${esc(j.language)} · ${j.duration_s ?? "?"}s</div>
      <div class="row" style="margin-top:10px">${actions}<a class="btn" href="/api/jobs/${j.id}/video" download>${t("download")}</a></div></div>`;
  el.innerHTML = `<h1>${t("ready")}</h1><p class="sub">${t("readyHint")}</p>
    <div class="grid g3">${data.items.map((j) => card(j, `<button class="btn primary" data-dec="approve" data-id="${j.id}">${t("approve")}</button><button class="btn danger" data-dec="reject" data-id="${j.id}">${t("reject")}</button>`)).join("") || `<p class="muted">${t("noData")}</p>`}</div>
    ${approved.items.length ? `<h1 style="margin-top:28px;font-size:18px">${t("approved")}</h1><div class="grid g3">${approved.items.map((j) => card(j, "")).join("")}</div>` : ""}`;
  on("[data-dec]", "click", async (e) => {
    try { await api(`/api/jobs/${e.target.dataset.id}/decision`, { method: "POST", body: { decision: e.target.dataset.dec } }); render(); }
    catch (err) { toast(err.message, true); }
  });
}

function serverCard() {
  if (!desktop) return "";
  return `<div class="card" style="margin-bottom:16px"><h3>${t("server")}</h3><p class="muted small">${t("serverHelp")}</p>
    <form id="srv" class="row"><input name="url" value="${esc(desktop.server_url)}" placeholder="http://mediafactory:8080" style="flex:1;min-width:220px">
    <button class="btn primary">${t("save")}</button></form></div>`;
}
function bindServerCard() {
  const f = document.getElementById("srv");
  if (!f) return;
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const r = await fetch("/desktop/config", { method: "POST", headers: { "Content-Type": "application/json", "X-MF-Client": "panel" },
      body: JSON.stringify({ server_url: new FormData(f).get("url") }) });
    const d = await r.json();
    if (!r.ok) return toast(d.detail || "error", true);
    desktop = d; toast(d.reachable ? t("connected") : t("offline"), !d.reachable); render();
  });
}
async function settings(el) {
  let prov, routes, creds;
  try {
    [prov, routes, creds] = await Promise.all([api("/api/providers"), api("/api/task-routes"), api("/api/source-credentials")]);
  } catch (err) {
    el.innerHTML = `<h1>${t("settings")}</h1>${serverCard()}<p class="muted">${esc(err.message)}</p>`;
    return bindServerCard();
  }
  const pRows = prov.items.map((p) => `<tr><td><b>${esc(p.name)}</b><div class="muted small">${esc(p.base_url)}</div></td>
      <td>${p.locality}</td><td>${p.has_api_key ? "🔑" : "—"}</td><td><button class="btn" data-test="${p.id}">${t("test")}</button></td></tr>`).join("");
  const rRows = routes.items.map((r) => `<tr><td><b>${esc(r.task)}</b></td><td class="small">${r.steps.map((s) => esc(s.model)).join(" → ")}</td><td class="small muted">${r.rounds}× / ${r.retry_delay_s}s</td></tr>`).join("");
  el.innerHTML = `<h1>${t("settings")}</h1><p class="sub">AI · Reddit</p>${serverCard()}
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
