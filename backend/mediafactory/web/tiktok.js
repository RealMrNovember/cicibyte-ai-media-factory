// TikTok: Settings card, badges on ready videos, and the draft / manual-share dialog.
"use strict";

const TT = {
  en: {
    title: "TikTok",
    help: "Videos are sent with the official TikTok Content Posting API using your own TikTok developer app. By default each video arrives as a draft in your TikTok inbox: open TikTok, add music or effects if you like, and post it. Direct posting (straight to your profile) needs TikTok to review your app first — until then such posts are only visible to you.",
    steps: "1) At developers.tiktok.com create an app and add the products “Login Kit” and “Content Posting API”. 2) In Login Kit choose the Desktop platform and add this redirect URI:",
    steps2: "3) Copy the app's Client key and Client secret below, then press “Connect TikTok”. Connecting works from the desktop app (TikTok accepts only its local address).",
    guide: "TikTok developer guide", clientKey: "Client key", clientSecret: "Client secret",
    connect: "Connect TikTok", reconnect: "Reconnect", wantDirect: "also ask for direct posting (only after TikTok approved your app)",
    desktopOnly: "Open the desktop app to connect TikTok: TikTok only accepts the app's local address.",
    connected: "Connected", needsReconnect: "Access ended — reconnect TikTok.", none: "No TikTok account connected.",
    mode: "How to post", modeDraft: "Draft in my TikTok inbox (I post it from the app)", modeDirect: "Post directly to my profile",
    privacy: "Who can see direct posts", choose: "— choose —", consent: "By posting directly you agree to TikTok's Music Usage Confirmation. Videos are labelled as AI-generated.",
    privacyLabels: { PUBLIC_TO_EVERYONE: "Everyone", MUTUAL_FOLLOW_FRIENDS: "Friends", FOLLOWER_OF_CREATOR: "Followers", SELF_ONLY: "Only me" },
    queued: "TikTok: queued", uploading: "TikTok: uploading", inbox: "TikTok draft waiting", on: "On TikTok", manual: "Shared on TikTok", failed: "TikTok failed", at: "TikTok",
    finish: "Finish TikTok draft", manualBtn: "Share on TikTok manually", needsConnect: "Connect TikTok in Settings to send videos automatically.",
    draftTitle: "Post your TikTok draft", draftHelp: "The video is in your TikTok inbox (notifications). Finish it in three steps:",
    d1: "Copy the caption", d2: "Open TikTok on your phone → Inbox → the draft notification", d3: "Paste the caption, check visibility and post.",
    manualTitle: "Share on TikTok yourself", manualHelp: "TikTok isn't connected. Post it yourself in three steps:",
    m1: "Download the video", m2: "Copy the caption", m3: "Open TikTok (web or phone), upload the video and paste the caption.",
    open: "Open tiktok.com", done: "I've posted it",
  },
  tr: {
    title: "TikTok",
    help: "Videolar resmî TikTok Content Posting API ile, senin kendi TikTok geliştirici uygulaman üzerinden gönderilir. Varsayılan olarak her video TikTok gelen kutuna taslak olarak düşer: TikTok'u aç, istersen müzik ya da efekt ekle ve paylaş. Doğrudan paylaşım (direkt profile) için TikTok'un uygulamanı incelemesi (audit) gerekir — o zamana kadar bu paylaşımları yalnızca sen görürsün.",
    steps: "1) developers.tiktok.com'da bir uygulama oluştur ve “Login Kit” ile “Content Posting API” ürünlerini ekle. 2) Login Kit'te Desktop platformunu seç ve şu yönlendirme adresini (redirect URI) ekle:",
    steps2: "3) Uygulamanın Client key ve Client secret değerlerini aşağıya yapıştır, sonra “TikTok'u bağla”ya bas. Bağlantı masaüstü uygulamasından yapılır (TikTok yalnızca uygulamanın yerel adresini kabul ediyor).",
    guide: "TikTok geliştirici rehberi", clientKey: "Client key", clientSecret: "Client secret",
    connect: "TikTok'u bağla", reconnect: "Yeniden bağlan", wantDirect: "doğrudan paylaşım iznini de iste (TikTok uygulamanı onayladıktan sonra)",
    desktopOnly: "TikTok'u bağlamak için masaüstü uygulamasını aç: TikTok yalnızca uygulamanın yerel adresini kabul ediyor.",
    connected: "Bağlı", needsReconnect: "Erişim sona erdi — TikTok'u yeniden bağla.", none: "Bağlı TikTok hesabı yok.",
    mode: "Nasıl paylaşılsın", modeDraft: "TikTok gelen kutuma taslak (uygulamadan ben paylaşırım)", modeDirect: "Doğrudan profilime paylaş",
    privacy: "Doğrudan paylaşımları kim görsün", choose: "— seç —", consent: "Doğrudan paylaşarak TikTok'un Müzik Kullanım Onayı'nı kabul etmiş olursun. Videolar yapay zekâyla üretildi olarak etiketlenir.",
    privacyLabels: { PUBLIC_TO_EVERYONE: "Herkes", MUTUAL_FOLLOW_FRIENDS: "Arkadaşlar", FOLLOWER_OF_CREATOR: "Takipçiler", SELF_ONLY: "Yalnızca ben" },
    queued: "TikTok: sırada", uploading: "TikTok: yükleniyor", inbox: "TikTok taslağı bekliyor", on: "TikTok'ta", manual: "TikTok'ta paylaşıldı", failed: "TikTok başarısız", at: "TikTok",
    finish: "TikTok taslağını tamamla", manualBtn: "TikTok'ta elle paylaş", needsConnect: "Otomatik göndermek için Ayarlar'dan TikTok'u bağla.",
    draftTitle: "TikTok taslağını paylaş", draftHelp: "Video TikTok gelen kutunda (bildirimler). Üç adımda tamamla:",
    d1: "Açıklamayı kopyala", d2: "Telefonda TikTok'u aç → Gelen kutusu → taslak bildirimi", d3: "Açıklamayı yapıştır, görünürlüğü kontrol et ve paylaş.",
    manualTitle: "TikTok'ta kendin paylaş", manualHelp: "TikTok bağlı değil. Üç adımda kendin paylaş:",
    m1: "Videoyu indir", m2: "Açıklamayı kopyala", m3: "TikTok'u aç (web ya da telefon), videoyu yükle ve açıklamayı yapıştır.",
    open: "tiktok.com'u aç", done: "Paylaştım",
  },
};
const tx = (k) => (TT[lang] && TT[lang][k]) || TT.en[k];

let TT_ACCOUNT = null;
async function loadTiktok() {
  try { TT_ACCOUNT = (await api("/api/tiktok")).account; } catch { TT_ACCOUNT = null; }
  return TT_ACCOUNT;
}
const isDesktop = () => ["127.0.0.1", "localhost"].includes(location.hostname);

async function tiktokCard() {
  let s;
  try { s = await api("/api/tiktok"); } catch { return ""; }
  TT_ACCOUNT = s.account;
  const a = s.account, labels = tx("privacyLabels");
  const accountRow = a ? `<div class="row" style="margin:8px 0"><span class="pill ${a.needs_reconnect ? "warn" : "ok"}">${a.needs_reconnect ? "⚠ " + tx("needsReconnect") : tx("connected")}</span>
      <b>${esc(a.display_name || "")}</b><span class="muted small">${a.mode === "direct" ? tx("modeDirect") + " · " + esc(labels[a.privacy_level] || a.privacy_level || "") : tx("modeDraft")}</span>
      <span class="spacer"></span><button class="btn danger small-btn" id="ttDel">${sc("disconnect")}</button></div>
    <form id="ttMode" class="grid g3" style="align-items:end">
      <div><label>${tx("mode")}</label><select name="mode"><option value="draft" ${a.mode !== "direct" ? "selected" : ""}>${tx("modeDraft")}</option>
        <option value="direct" ${a.mode === "direct" ? "selected" : ""} ${a.can_direct ? "" : "disabled"}>${tx("modeDirect")}</option></select></div>
      <div id="ttPriv" style="${a.mode === "direct" ? "" : "display:none"}"><label>${tx("privacy")}</label><select name="privacy"><option value="">${tx("choose")}</option></select></div>
      <div><button class="btn primary">${t("save")}</button></div>
      <p class="muted small" style="grid-column:1/-1;${a.mode === "direct" ? "" : "display:none"}" id="ttConsent">${tx("consent")}</p></form>`
    : `<p class="muted small">${tx("none")}</p>`;
  return `<div class="card" style="margin-bottom:16px" id="ttCard"><h3>♪ ${tx("title")}</h3>
    <p class="muted small">${tx("help")}</p>
    <p class="muted small">${tx("steps")} <code>${esc(s.redirect)}</code> ${tx("steps2")} <a href="#" id="ttGuide">${tx("guide")} ↗</a></p>
    ${accountRow}
    <form id="ttApp" class="grid g3" style="align-items:end;margin-top:8px">
      <div><label>${tx("clientKey")}</label><input name="client_key" required value="${esc(s.client_key || "")}" autocomplete="off"></div>
      <div><label>${tx("clientSecret")}</label><input name="client_secret" type="password" required autocomplete="off" placeholder="${s.client_key ? "••••••••" : ""}"></div>
      <div><button class="btn">${t("save")}</button></div></form>
    ${s.client_key ? `<div class="row" style="margin-top:10px">${isDesktop()
      ? `<label class="row small" style="font-weight:400"><input type="checkbox" id="ttDirect" style="width:auto" ${a && a.can_direct ? "checked" : ""}> ${tx("wantDirect")}</label>
         <span class="spacer"></span><button class="btn primary" id="ttConnect">♪ ${a ? tx("reconnect") : tx("connect")}</button>`
      : `<p class="muted small">${tx("desktopOnly")}</p>`}</div>` : ""}</div>`;
}

async function fillPrivacy(sel, current) {
  try {
    const c = await api("/api/tiktok/creator"), labels = tx("privacyLabels");
    sel.innerHTML = `<option value="">${tx("choose")}</option>` + (c.privacy_level_options || []).map((o) =>
      `<option value="${esc(o)}" ${o === current ? "selected" : ""}>${esc(labels[o] || o)}</option>`).join("");
  } catch (err) { toast(err.message, true); }
}

function bindTiktokCard() {
  const card = document.getElementById("ttCard");
  if (!card) return;
  document.getElementById("ttGuide").addEventListener("click", (e) => { e.preventDefault(); openExternal("https://developers.tiktok.com/doc/content-posting-api-get-started"); });
  document.getElementById("ttApp").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    try { await api("/api/tiktok/app", { method: "PUT", body: { client_key: f.client_key.value.trim(), client_secret: f.client_secret.value.trim() } }); toast(t("saved")); render(); }
    catch (err) { toast(err.message, true); }
  });
  const del = document.getElementById("ttDel");
  del && del.addEventListener("click", async () => { if (!confirm("?")) return; await api("/api/tiktok", { method: "DELETE" }).catch((err) => toast(err.message, true)); render(); });
  const mf = document.getElementById("ttMode");
  if (mf) {
    const priv = document.getElementById("ttPriv"), consent = document.getElementById("ttConsent");
    const show = () => {
      const direct = mf.mode.value === "direct";
      priv.style.display = consent.style.display = direct ? "" : "none";
      if (direct && mf.privacy.options.length <= 1) fillPrivacy(mf.privacy, TT_ACCOUNT && TT_ACCOUNT.privacy_level);
    };
    mf.mode.addEventListener("change", show);
    show();
    mf.addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = { mode: mf.mode.value, privacy_level: mf.mode.value === "direct" ? mf.privacy.value || null : null };
      try { await api("/api/tiktok/mode", { method: "PUT", body }); toast(t("saved")); render(); } catch (err) { toast(err.message, true); }
    });
  }
  const btn = document.getElementById("ttConnect");
  btn && btn.addEventListener("click", async () => {
    try {
      const before = JSON.stringify((await api("/api/tiktok")).account);
      const direct = !!(document.getElementById("ttDirect") || {}).checked;
      const r = await api("/api/tiktok/auth", { method: "POST", body: { redirect_uri: location.origin + "/api/tiktok/callback", direct } });
      openExternal(r.url); toast(sc("connectWait"));
      let n = 0;
      const timer = setInterval(async () => {
        n += 1;
        if (n > 100 || route() !== "settings") return clearInterval(timer);
        const s = await api("/api/tiktok").catch(() => null);
        if (s && s.account && JSON.stringify(s.account) !== before) { clearInterval(timer); toast("TikTok ✓"); render(); }
      }, 3000);
    } catch (err) { toast(err.message, true); }
  });
}

// ---------- on ready videos ----------
function ttBadge(j) {
  const k = j.tiktok;
  if (!k) return "";
  if (k.state === "published") return `<a class="pill ok" href="#" data-ext="${esc(k.url)}">♪ ${tx("on")} ↗</a>`;
  if (k.state === "manual") return `<span class="pill ok">♪ ${tx("manual")}</span>`;
  if (k.state === "inbox") return `<span class="pill warn">♪ ${tx("inbox")}</span>`;
  if (k.state === "failed") return `<span class="pill warn" title="${esc(k.error || "")}">⚠ ${tx("failed")}</span>`;
  return `<span class="pill warn">♪ ${k.state === "uploading" ? tx("uploading") : k.publish_at ? tx("at") + " · " + when(k.publish_at) : tx("queued")}</span>`;
}
const ttOpen = (j) => !j.tiktok || j.tiktok.state === "failed";

function ttButtons(j) {
  if (j.tiktok && j.tiktok.state === "inbox") return `<button class="btn" data-ttman="${j.id}" data-draft="1">♪ ${tx("finish")}</button>`;
  if (ttOpen(j) && !TT_ACCOUNT) return `<button class="btn" data-ttman="${j.id}" title="${esc(tx("needsConnect"))}">♪ ${tx("manualBtn")}</button>`;
  return "";
}

async function manualTiktok(jobId, draft) {
  let pack;
  try { pack = await api(`/api/jobs/${jobId}/tiktok-pack`); } catch (err) { return toast(err.message, true); }
  const copy = `<button class="btn" id="ttCopy">⧉ ${tx(draft ? "d1" : "m2")}</button><textarea readonly rows="6" style="width:100%;margin-top:6px">${esc(pack.caption)}</textarea>`;
  const steps = draft
    ? `<li>${copy}</li><li>${tx("d2")}</li><li>${tx("d3")}</li>`
    : `<li><button class="btn" id="ttDl">⬇ ${tx("m1")}</button></li><li>${copy}</li><li>${tx("m3")} <button class="btn" id="ttWeb">${tx("open")} ↗</button></li>`;
  const m = modal(`<h1>♪ ${tx(draft ? "draftTitle" : "manualTitle")}</h1><p class="muted small">${tx(draft ? "draftHelp" : "manualHelp")}</p>
    <ol style="line-height:1.9">${steps}</ol>
    <div class="row" style="margin-top:12px"><button class="btn primary" id="ttDone">✓ ${tx("done")}</button></div>`);
  const dl = m.querySelector("#ttDl"), web = m.querySelector("#ttWeb");
  dl && dl.addEventListener("click", () => openExternal(location.origin + pack.video));
  web && web.addEventListener("click", () => openExternal("https://www.tiktok.com/upload"));
  m.querySelector("#ttCopy").addEventListener("click", async () => {
    const ta = m.querySelector("textarea");
    try { await navigator.clipboard.writeText(pack.caption); } catch { ta.select(); document.execCommand("copy"); }
    toast(sc("copied"));
  });
  m.querySelector("#ttDone").addEventListener("click", async () => {
    try { await api(`/api/jobs/${jobId}/tiktok-manual`, { method: "POST" }); m.remove(); render(); } catch (err) { toast(err.message, true); }
  });
}
