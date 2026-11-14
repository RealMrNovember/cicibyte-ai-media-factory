// Schedule (Takvim) page, YouTube settings card and "send to YouTube" dialog.
"use strict";

const SC = {
  en: {
    schedule: "Schedule", scheduleSub: "Produce new videos and publish approved ones automatically, at the times you choose.",
    newSchedule: "New schedule", kindProduce: "Produce videos", kindPublish: "Publish to YouTube", kind: "Type",
    times: "Times (e.g. 09:00, 18:30)", days: "Days", tz: "Time zone", count: "How many each time",
    perSlot: "Videos per time slot", autoApprove: "Approve automatically (skip my review)", useStudio: "Use my current Studio caption style, voice and music",
    source: "From source", anySource: "Any source", privacy: "Visibility", public: "Public", unlisted: "Unlisted", private: "Private",
    nextRun: "Next run", lastRun: "Last run", runNow: "Run now", enabled: "On", disabled: "Off", edit: "Edit",
    dayNames: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], anyLang: "Any language",
    youtube: "YouTube", ytHelp: "Use your own Google OAuth client (type: Desktop app) with YouTube Data API v3 enabled.",
    ytGuide: "How to get one", clientId: "Client ID", clientSecret: "Client secret", connect: "Connect a channel",
    connectWait: "Finish signing in in your browser — this page updates by itself.", channels: "Connected channels",
    disconnect: "Disconnect", sendYt: "Send to YouTube", now: "Upload now", later: "Schedule for", when: "Publish at",
    queuedYt: "Queued for YouTube", onYt: "On YouTube", scheduledYt: "Scheduled", noChannel: "Connect a YouTube channel in Settings first.",
    publishedList: "On YouTube / scheduled", watch: "Open",
  },
  tr: {
    schedule: "Takvim", scheduleSub: "Seçtiğin saatlerde otomatik video üret ve onaylı videoları YouTube'a gönder.",
    newSchedule: "Yeni zamanlama", kindProduce: "Video üret", kindPublish: "YouTube'a gönder", kind: "Tür",
    times: "Saatler (ör. 09:00, 18:30)", days: "Günler", tz: "Saat dilimi", count: "Her seferinde kaç tane",
    perSlot: "Her saatte kaç video", autoApprove: "Otomatik onayla (benim incelememi atla)", useStudio: "Stüdyo'daki mevcut altyazı stilimi, sesimi ve müziğimi kullan",
    source: "Kaynak", anySource: "Tüm kaynaklar", privacy: "Görünürlük", public: "Herkese açık", unlisted: "Liste dışı", private: "Gizli",
    nextRun: "Sonraki", lastRun: "Son", runNow: "Şimdi çalıştır", enabled: "Açık", disabled: "Kapalı", edit: "Düzenle",
    dayNames: ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"], anyLang: "Her dil",
    youtube: "YouTube", ytHelp: "Kendi Google OAuth istemcini kullan (tür: Masaüstü uygulaması), YouTube Data API v3 etkin olmalı.",
    ytGuide: "Nasıl alınır", clientId: "Client ID", clientSecret: "Client secret", connect: "Kanal bağla",
    connectWait: "Tarayıcıda girişi tamamla — bu sayfa kendiliğinden güncellenir.", channels: "Bağlı kanallar",
    disconnect: "Bağlantıyı kes", sendYt: "YouTube'a gönder", now: "Hemen yükle", later: "Zamanla", when: "Yayın zamanı",
    queuedYt: "YouTube sırasında", onYt: "YouTube'da", scheduledYt: "Zamanlandı", noChannel: "Önce Ayarlar'dan bir YouTube kanalı bağla.",
    publishedList: "YouTube'da / zamanlanmış", watch: "Aç",
  },
};
const sc = (k) => (SC[lang] && SC[lang][k]) || st(k);
const myTz = () => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"; } catch { return "UTC"; } };

function openExternal(url) {
  if (window.pywebview && window.pywebview.api && window.pywebview.api.open_url) window.pywebview.api.open_url(url);
  else window.open(url, "_blank", "noopener");
}

async function schedule(el) {
  const [list, sources] = await Promise.all([api("/api/schedules"), api("/api/sources")]);
  const days = sc("dayNames");
  const rows = list.items.map((s) => `<tr>
      <td><b>${esc(s.name)}</b><div class="muted small">${s.kind === "produce" ? sc("kindProduce") : sc("kindPublish")} ·
        ${s.kind === "produce" ? `${s.params.count}× · ${esc((s.params.languages || []).join("+"))}${s.params.auto_approve ? " · auto ✓" : ""}` : `${s.params.count}× · ${esc(sc(s.params.privacy))}`}</div></td>
      <td class="small">${esc(s.times.join(", "))}<div class="muted">${s.weekdays.length === 7 ? "—" : s.weekdays.map((d) => days[d]).join(" ")} · ${esc(s.timezone)}</div></td>
      <td class="small">${s.enabled ? when(s.next_run_at) : `<span class="muted">${sc("disabled")}</span>`}
        <div class="muted clip">${s.last_run_at ? when(s.last_run_at) + " · " + esc(s.last_result || "") : ""}</div></td>
      <td><div class="row"><button class="btn" data-run="${s.id}">${sc("runNow")}</button><button class="btn" data-edit="${s.id}">${sc("edit")}</button>
        <button class="btn" data-toggle="${s.id}">${s.enabled ? sc("enabled") + " ●" : sc("disabled") + " ○"}</button>
        <button class="btn danger" data-delsch="${s.id}">${t("delete")}</button></div></td></tr>`).join("");
  el.innerHTML = `<div class="row"><h1>${sc("schedule")}</h1><span class="spacer"></span><button class="btn primary" id="newSch">＋ ${sc("newSchedule")}</button></div>
    <p class="sub">${sc("scheduleSub")}</p>
    <div class="card">${list.items.length ? `<table><tr><th></th><th>${sc("times")}</th><th>${sc("nextRun")}</th><th></th></tr>${rows}</table>` : `<p class="muted">${t("noData")}</p>`}</div>`;
  const byId = Object.fromEntries(list.items.map((s) => [s.id, s]));
  document.getElementById("newSch").addEventListener("click", () => scheduleDialog(null, sources.items));
  on("[data-edit]", "click", (e) => scheduleDialog(byId[e.target.dataset.edit], sources.items));
  on("[data-run]", "click", async (e) => { try { const r = await api(`/api/schedules/${e.target.dataset.run}/run`, { method: "POST" }); toast(r.last_result || "OK"); render(); } catch (err) { toast(err.message, true); } });
  on("[data-toggle]", "click", async (e) => {
    const s = byId[e.target.dataset.toggle];
    try { await api(`/api/schedules/${s.id}`, { method: "PUT", body: { ...s, enabled: !s.enabled } }); render(); } catch (err) { toast(err.message, true); }
  });
  on("[data-delsch]", "click", async (e) => { if (!confirm("?")) return; try { await api(`/api/schedules/${e.target.dataset.delsch}`, { method: "DELETE" }); render(); } catch (err) { toast(err.message, true); } });
}

function scheduleDialog(s, sources) {
  const p = (s && s.params) || {};
  const kind = (s && s.kind) || "produce";
  const days = sc("dayNames");
  const wd = (s && s.weekdays) || [0, 1, 2, 3, 4, 5, 6];
  const m = modal(`<h1>${s ? esc(s.name) : sc("newSchedule")}</h1><form id="schf">
    <div class="grid g2"><div><label>${t("name")}</label><input name="name" required value="${esc((s && s.name) || "")}" placeholder="${kind === "produce" ? "Günlük korku" : "Akşam yayını"}"></div>
      <div><label>${sc("kind")}</label><select name="kind"><option value="produce" ${kind === "produce" ? "selected" : ""}>${sc("kindProduce")}</option><option value="publish" ${kind === "publish" ? "selected" : ""}>${sc("kindPublish")}</option></select></div></div>
    <div class="grid g2"><div><label>${sc("times")}</label><input name="times" required value="${esc(((s && s.times) || ["09:00"]).join(", "))}"></div>
      <div><label>${sc("tz")}</label><input name="tz" value="${esc((s && s.timezone) || myTz())}"></div></div>
    <label>${sc("days")}</label><div class="row">${days.map((d, i) => `<label class="row"><input type="checkbox" name="d${i}" ${wd.includes(i) ? "checked" : ""} style="width:auto"> ${d}</label>`).join("")}</div>
    <div id="kp"></div>
    <div class="row" style="margin-top:16px"><button class="btn primary">${t("save")}</button></div></form>`);
  const f = m.querySelector("#schf"), kp = m.querySelector("#kp");
  const drawKind = () => {
    if (f.kind.value === "produce") {
      kp.innerHTML = `<div class="grid g2"><div><label>${sc("count")}</label><input name="count" type="number" min="1" max="20" value="${p.count || 1}"></div>
        <div><label>${t("seconds")}</label><input name="seconds" type="number" min="15" max="170" value="${p.seconds || 50}"></div></div>
        <label>${t("languages")}</label><div class="row"><label class="row"><input type="checkbox" name="en" ${(p.languages || ["en"]).includes("en") ? "checked" : ""} style="width:auto"> English</label>
        <label class="row"><input type="checkbox" name="tr" ${(p.languages || []).includes("tr") ? "checked" : ""} style="width:auto"> Türkçe</label></div>
        <label>${sc("source")}</label><select name="source"><option value="">${sc("anySource")}</option>${sources.map((x) => `<option value="${x.id}" ${p.source_id === x.id ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select>
        <label class="row" style="margin-top:12px"><input type="checkbox" name="studio" ${s ? "" : "checked"} style="width:auto"> ${sc("useStudio")}</label>
        <label class="row"><input type="checkbox" name="auto" ${p.auto_approve ? "checked" : ""} style="width:auto"> ${sc("autoApprove")}</label>`;
    } else {
      kp.innerHTML = `<div class="grid g2"><div><label>${sc("perSlot")}</label><input name="count" type="number" min="1" max="10" value="${p.count || 1}"></div>
        <div><label>${sc("privacy")}</label><select name="privacy">${["public", "unlisted", "private"].map((v) => `<option value="${v}" ${p.privacy === v ? "selected" : ""}>${sc(v)}</option>`).join("")}</select></div></div>
        <label>${t("languages")}</label><select name="language"><option value="">${sc("anyLang")}</option><option value="en" ${p.language === "en" ? "selected" : ""}>English</option><option value="tr" ${p.language === "tr" ? "selected" : ""}>Türkçe</option></select>`;
    }
  };
  drawKind();
  f.kind.addEventListener("change", drawKind);
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const kindV = f.kind.value;
    let params;
    if (kindV === "produce") {
      params = { count: Number(f.count.value), seconds: Number(f.seconds.value), languages: ["en", "tr"].filter((l) => f[l].checked),
        auto_approve: f.auto.checked, source_id: f.source.value ? Number(f.source.value) : null, background: p.background || "random",
        style: f.studio.checked ? loadStyle() : (p.style || loadStyle()), voice: f.studio.checked ? loadVoice() : (p.voice || loadVoice()), music: f.studio.checked ? loadMusic() : (p.music || loadMusic()) };
    } else {
      params = { count: Number(f.count.value), privacy: f.privacy.value, language: f.language.value || null };
    }
    const body = { name: f.name.value, kind: kindV, enabled: s ? s.enabled : true, timezone: f.tz.value.trim() || "UTC",
      times: f.times.value.split(/[,\s]+/).filter(Boolean), weekdays: [0, 1, 2, 3, 4, 5, 6].filter((i) => f["d" + i].checked), params };
    try {
      await api(s ? `/api/schedules/${s.id}` : "/api/schedules", { method: s ? "PUT" : "POST", body });
      m.remove(); toast(t("saved")); render();
    } catch (err) { toast(err.message, true); }
  });
}

// ---------- YouTube in Settings ----------
async function youtubeCard() {
  let y;
  try { y = await api("/api/youtube"); } catch { return ""; }
  const chans = y.channels.map((c) => `<div class="row" style="margin:6px 0">${c.thumbnail ? `<img src="${esc(c.thumbnail)}" style="width:28px;height:28px;border-radius:50%">` : "▶"}
      <b>${esc(c.title)}</b>${c.is_default ? ' <span class="pill ok">default</span>' : ""}<span class="spacer"></span>
      <button class="btn danger small-btn" data-ytdel="${c.id}">${sc("disconnect")}</button></div>`).join("");
  return `<div class="card" style="margin-bottom:16px" id="ytCard"><h3>${sc("youtube")}</h3>
    <p class="muted small">${sc("ytHelp")} <a href="#" id="ytGuide">${sc("ytGuide")} ↗</a></p>
    <form id="ytc" class="grid g3" style="align-items:end">
      <div><label>${sc("clientId")}</label><input name="client_id" required value="${esc(y.client_id || "")}" placeholder="…apps.googleusercontent.com"></div>
      <div><label>${sc("clientSecret")}</label><input name="client_secret" type="password" required placeholder="${y.client_id ? "••••••••" : ""}"></div>
      <div><button class="btn">${t("save")}</button></div></form>
    ${chans ? `<label>${sc("channels")}</label>${chans}` : ""}
    <div class="row" style="margin-top:12px"><button class="btn primary" id="ytConnect" ${y.client_id ? "" : "disabled"}>▶ ${sc("connect")}</button></div></div>`;
}

function bindYoutubeCard() {
  const f = document.getElementById("ytc");
  if (!f) return;
  document.getElementById("ytGuide").addEventListener("click", (e) => { e.preventDefault(); openExternal("https://developers.google.com/youtube/v3/guides/auth/installed-apps"); });
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await api("/api/youtube/client", { method: "PUT", body: { client_id: f.client_id.value.trim(), client_secret: f.client_secret.value.trim() } }); toast(t("saved")); render(); }
    catch (err) { toast(err.message, true); }
  });
  on("[data-ytdel]", "click", async (e) => { if (!confirm("?")) return; await api(`/api/youtube/channels/${e.target.dataset.ytdel}`, { method: "DELETE" }).catch((err) => toast(err.message, true)); render(); });
  const btn = document.getElementById("ytConnect");
  btn && btn.addEventListener("click", async () => {
    try {
      const before = (await api("/api/youtube")).channels.length;
      const r = await api("/api/youtube/auth", { method: "POST", body: { redirect_uri: location.origin + "/api/youtube/callback" } });
      openExternal(r.url); toast(sc("connectWait"));
      let n = 0;
      const timer = setInterval(async () => {
        n += 1;
        if (n > 100 || route() !== "settings") return clearInterval(timer);
        const y = await api("/api/youtube").catch(() => null);
        if (y && y.channels.length > before) { clearInterval(timer); toast("YouTube ✓"); render(); }
      }, 3000);
    } catch (err) { toast(err.message, true); }
  });
}

// ---------- Ready videos: send to YouTube ----------
function ytBadge(j) {
  const y = j.youtube;
  if (!y) return "";
  if (y.url) return `<a class="pill ok" href="#" data-ext="${esc(y.url)}">${y.state === "scheduled" ? sc("scheduledYt") + " · " + when(y.publish_at) : sc("onYt")} ↗</a>`;
  return `<span class="pill warn">${sc("queuedYt")}${y.publish_at ? " · " + when(y.publish_at) : ""}</span>`;
}

function publishDialog(jobId) {
  const soon = new Date(Date.now() + 3 * 3600 * 1000);
  soon.setMinutes(0, 0, 0);
  const local = new Date(soon.getTime() - soon.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  const m = modal(`<h1>${sc("sendYt")}</h1><form id="pubf">
    <label>${sc("privacy")}</label><select name="privacy"><option value="public">${sc("public")}</option><option value="unlisted">${sc("unlisted")}</option><option value="private">${sc("private")}</option></select>
    <label class="row" style="margin-top:12px"><input type="radio" name="mode" value="now" checked style="width:auto"> ${sc("now")}</label>
    <label class="row"><input type="radio" name="mode" value="later" style="width:auto"> ${sc("later")}</label>
    <input type="datetime-local" name="at" value="${local}">
    <div class="row" style="margin-top:16px"><button class="btn primary">${sc("sendYt")}</button></div></form>`);
  m.querySelector("#pubf").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target, later = f.mode.value === "later";
    const body = { privacy: f.privacy.value, publish_at: later ? new Date(f.at.value).toISOString() : null };
    try { await api(`/api/jobs/${jobId}/publish`, { method: "POST", body }); m.remove(); toast(sc("queuedYt")); render(); }
    catch (err) { toast(err.message, true); }
  });
}
