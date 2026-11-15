// Schedule (Takvim) page, YouTube settings card and "send to YouTube" dialog.
"use strict";

const SC = {
  en: {
    schedule: "Schedule", scheduleSub: "Produce new videos and publish approved ones automatically, at the times you choose.",
    newSchedule: "New schedule", kindProduce: "Produce videos", kindPublish: "Publish approved videos", kindAuto: "Autopilot: make & publish", autoHelp: "Each run picks a random unused story (of the topic you choose), makes the video with your Studio style, voice and music, and — if it passes the quality check — publishes it to YouTube.", freq: "When", atTimes: "At set times", every: "Every", hours: "hours", activeFrom: "Active from", activeTo: "until", topic: "Topic", randomTopic: "Random topic", randomLang: "Random language", publishIt: "Publish to YouTube automatically", everyN: "every",  kind: "Type",
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
    publishedList: "Published / scheduled", watch: "Open",
    dailyLimit: "Uploads per day (0 = no limit)", playlistField: "Add every upload to playlist (link or id)", today: "today",
    quotaLine: "YouTube API quota today", quotaReset: "resets", reconnect: "Reconnect", reconnectNeeded: "Access was withdrawn — reconnect this channel to upload again.",
    makeDefault: "Make default", waitingYt: "Waiting for YouTube's daily limit", extrasNote: "Each upload also adds the subtitle file and, if set, the playlist entry. Channels connected before this version need one reconnect for those two.",
    publish: "Publish", platforms: "Where", ytOnly: "only for YouTube", instagram: "Instagram",
    igHelp: "Reels are published through the official Instagram API. This needs a professional account (Creator or Business) — switching is free in Instagram → Settings → Account type. A personal account can't publish through the API: use “Share manually” on each video instead.",
    igSteps: "1) At developers.facebook.com create an app (type: Business) and add the product “Instagram” → “API setup with Instagram login”. 2) Add your Instagram account there and press “Generate token”. 3) Paste the token below. The server renews it by itself before it expires (60 days).",
    igGuide: "Meta's guide", igToken: "Access token", igConnected: "Connected", igNone: "Not connected", igExpires: "token renewed automatically, valid until",
    igQueued: "Instagram: queued", igUploading: "Instagram: uploading", igOn: "On Instagram", igManual: "Shared on Instagram", igFailed: "Instagram failed",
    igScheduled: "Instagram at", igManualBtn: "Share on Instagram manually", igManualTitle: "Share on Instagram yourself",
    igManualHelp: "Your account isn't connected for automatic publishing (personal accounts can't use the Instagram API). Post it yourself in three steps:",
    igM1: "Download the video", igM2: "Copy the caption", igM3: "Open Instagram (web or phone), create a Reel, choose the video and paste the caption.",
    igOpen: "Open instagram.com", copied: "Copied", igMarkDone: "I've shared it", igNeedsConnect: "Connect an Instagram professional account in Settings to publish automatically.",
    pubPlatforms: "Publish to", creditTitle: "Description line",
    creditLabel: "Add “Made with CiciByte AI Media Factory — cicibyte.com” to YouTube descriptions and Instagram captions (in the video's language)",
  },
  tr: {
    schedule: "Takvim", scheduleSub: "Seçtiğin saatlerde otomatik video üret ve onaylı videoları YouTube'a gönder.",
    newSchedule: "Yeni zamanlama", kindProduce: "Video üret", kindPublish: "Onaylıları yayınla", kindAuto: "Otopilot: üret ve yayınla", autoHelp: "Her çalışmada (seçtiğin konudan) kullanılmamış rastgele bir hikâye seçer, Stüdyo stilin, sesin ve müziğinle videoyu üretir ve kalite kontrolünden geçerse YouTube'da yayınlar.", freq: "Ne zaman", atTimes: "Belirli saatlerde", every: "Her", hours: "saatte bir", activeFrom: "Etkin saatler", activeTo: "ile", topic: "Konu", randomTopic: "Rastgele konu", randomLang: "Rastgele dil", publishIt: "YouTube'da otomatik yayınla", everyN: "her",  kind: "Tür",
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
    publishedList: "Yayınlanan / zamanlanmış", watch: "Aç",
    dailyLimit: "Günlük yükleme (0 = sınırsız)", playlistField: "Her yüklemeyi bu oynatma listesine ekle (link ya da kimlik)", today: "bugün",
    quotaLine: "Bugünkü YouTube API kotası", quotaReset: "sıfırlanma", reconnect: "Yeniden bağlan", reconnectNeeded: "Erişim geri alınmış — yeniden yükleme yapabilmek için bu kanalı yeniden bağla.",
    makeDefault: "Varsayılan yap", waitingYt: "YouTube'un günlük sınırı bekleniyor", extrasNote: "Her yüklemede altyazı dosyası ve (seçildiyse) oynatma listesi de eklenir. Bu sürümden önce bağlanan kanallar bunlar için bir kez yeniden bağlanmalı.",
    publish: "Yayınla", platforms: "Nerede", ytOnly: "yalnızca YouTube için", instagram: "Instagram",
    igHelp: "Reels videoları resmî Instagram API'siyle yayınlanır. Bunun için profesyonel hesap (Creator ya da İşletme) gerekir — Instagram → Ayarlar → Hesap türü'nden ücretsiz geçebilirsin. Kişisel hesaplar API ile paylaşamaz: onlar için her videoda “Elle paylaş” kullan.",
    igSteps: "1) developers.facebook.com'da bir uygulama oluştur (tür: Business) ve “Instagram” → “Instagram girişiyle API kurulumu” ürününü ekle. 2) Instagram hesabını orada ekleyip “Generate token”a bas. 3) Anahtarı aşağıya yapıştır. Sunucu, süresi (60 gün) dolmadan kendisi yeniler.",
    igGuide: "Meta'nın rehberi", igToken: "Erişim anahtarı (token)", igConnected: "Bağlı", igNone: "Bağlı değil", igExpires: "anahtar kendiliğinden yenilenir, geçerlilik",
    igQueued: "Instagram: sırada", igUploading: "Instagram: yükleniyor", igOn: "Instagram'da", igManual: "Instagram'da paylaşıldı", igFailed: "Instagram başarısız",
    igScheduled: "Instagram", igManualBtn: "Instagram'da elle paylaş", igManualTitle: "Instagram'da kendin paylaş",
    igManualHelp: "Hesabın otomatik yayın için bağlı değil (kişisel hesaplar Instagram API'sini kullanamaz). Üç adımda kendin paylaş:",
    igM1: "Videoyu indir", igM2: "Açıklamayı kopyala", igM3: "Instagram'ı aç (web ya da telefon), yeni Reels oluştur, videoyu seç ve açıklamayı yapıştır.",
    igOpen: "instagram.com'u aç", copied: "Kopyalandı", igMarkDone: "Paylaştım", igNeedsConnect: "Otomatik yayın için Ayarlar'dan bir Instagram profesyonel hesabı bağla.",
    pubPlatforms: "Nerede yayınlansın", creditTitle: "Açıklama satırı",
    creditLabel: "YouTube açıklamalarına ve Instagram metinlerine “CiciByte AI Media Factory ile üretildi — cicibyte.com” satırını ekle (videonun dilinde)",
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
      <td><b>${esc(s.name)}</b><div class="muted small">${s.kind === "produce" ? sc("kindProduce") : s.kind === "publish" ? sc("kindPublish") : "🤖 " + sc("kindAuto")} ·
        ${s.kind === "produce" ? `${s.params.count}× · ${esc((s.params.languages || []).join("+"))}${s.params.auto_approve ? " · auto ✓" : ""}`
          : s.kind === "publish" ? `${s.params.count}× · ${esc((s.params.platforms || ["youtube"]).join(" + "))} · ${esc(sc(s.params.privacy))}`
          : `${esc(s.params.topic === "random" ? sc("randomTopic") : topicLabel(s.params.topic))} · ${esc(s.params.language === "random" ? sc("randomLang") : s.params.language)}${s.params.publish ? " · ▶ " + esc((s.params.platforms || ["youtube"]).join(" + ")) + " · " + esc(sc(s.params.privacy)) : ""}`}</div></td>
      <td class="small">${s.interval_min ? `${sc("everyN")} ${+(s.interval_min / 60).toFixed(2)} h${s.window ? " · " + esc(s.window.join("–")) : ""}` : esc(s.times.join(", "))}<div class="muted">${s.weekdays.length === 7 ? "—" : s.weekdays.map((d) => days[d]).join(" ")} · ${esc(s.timezone)}</div></td>
      <td class="small">${s.enabled ? when(s.next_run_at) : `<span class="muted">${sc("disabled")}</span>`}
        <div class="muted clip">${s.last_run_at ? when(s.last_run_at) + " · " + esc(s.last_result || "") : ""}</div></td>
      <td><div class="row"><button class="btn" data-run="${s.id}">${sc("runNow")}</button><button class="btn" data-edit="${s.id}">${sc("edit")}</button>
        <button class="btn" data-toggle="${s.id}">${s.enabled ? sc("enabled") + " ●" : sc("disabled") + " ○"}</button>
        <button class="btn danger" data-delsch="${s.id}">${t("delete")}</button></div></td></tr>`).join("");
  el.innerHTML = `<div class="row"><h1>${sc("schedule")}</h1><span class="spacer"></span><button class="btn primary" id="newSch">＋ ${sc("newSchedule")}</button></div>
    <p class="sub">${sc("scheduleSub")}</p>
    <div class="card">${list.items.length ? `<table><tr><th></th><th>${sc("times")}</th><th>${sc("nextRun")}</th><th></th></tr>${rows}</table>` : `<p class="muted">${t("noData")}</p>`}</div>
    ${await conceptsCard()}`;
  bindConceptsCard();
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

const platBoxes = (sel) => `<label>${sc("pubPlatforms")}</label><div class="row">
  <label class="row"><input type="checkbox" name="pl_youtube" ${sel.includes("youtube") ? "checked" : ""} style="width:auto"> ▶ YouTube</label>
  <label class="row"><input type="checkbox" name="pl_instagram" ${sel.includes("instagram") ? "checked" : ""} style="width:auto"> ◎ Instagram</label></div>`;
const platValues = (f) => ["youtube", "instagram"].filter((x) => f["pl_" + x] && f["pl_" + x].checked);

function scheduleDialog(s, sources) {
  const p = (s && s.params) || {};
  const kind = (s && s.kind) || "produce";
  const days = sc("dayNames");
  const wd = (s && s.weekdays) || [0, 1, 2, 3, 4, 5, 6];
  const m = modal(`<h1>${s ? esc(s.name) : sc("newSchedule")}</h1><form id="schf">
    <div class="grid g2"><div><label>${t("name")}</label><input name="name" required value="${esc((s && s.name) || "")}" placeholder="${kind === "produce" ? "Günlük korku" : "Akşam yayını"}"></div>
      <div><label>${sc("kind")}</label><select name="kind"><option value="produce" ${kind === "produce" ? "selected" : ""}>${sc("kindProduce")}</option><option value="publish" ${kind === "publish" ? "selected" : ""}>${sc("kindPublish")}</option><option value="autopilot" ${kind === "autopilot" ? "selected" : ""}>🤖 ${sc("kindAuto")}</option></select></div></div>
    <label>${sc("freq")}</label><div class="row">
      <label class="row"><input type="radio" name="freq" value="times" ${s && s.interval_min ? "" : "checked"} style="width:auto"> ${sc("atTimes")}</label>
      <label class="row"><input type="radio" name="freq" value="every" ${s && s.interval_min ? "checked" : ""} style="width:auto"> ${sc("every")}
        <input name="hours" type="number" min="0.25" max="168" step="0.25" value="${s && s.interval_min ? s.interval_min / 60 : 2}" style="width:80px"> ${sc("hours")}</label></div>
    <div class="grid g2"><div data-for="times"><label>${sc("times")}</label><input name="times" value="${esc(((s && s.times && s.times.length ? s.times : ["09:00"])).join(", "))}"></div>
      <div data-for="every"><label>${sc("activeFrom")}</label><div class="row" style="flex-wrap:nowrap"><input name="wfrom" type="time" value="${esc((s && s.window && s.window[0]) || "09:00")}"> ${sc("activeTo")} <input name="wto" type="time" value="${esc((s && s.window && s.window[1]) || "23:00")}"></div></div>
      <div><label>${sc("tz")}</label><input name="tz" value="${esc((s && s.timezone) || myTz())}"></div></div>
    <label>${sc("days")}</label><div class="row">${days.map((d, i) => `<label class="row"><input type="checkbox" name="d${i}" ${wd.includes(i) ? "checked" : ""} style="width:auto"> ${d}</label>`).join("")}</div>
    <div id="kp"></div>
    <div class="row" style="margin-top:16px"><button class="btn primary">${t("save")}</button></div></form>`);
  const f = m.querySelector("#schf"), kp = m.querySelector("#kp");
  const drawFreq = () => {
    const every = f.freq.value === "every";
    m.querySelectorAll("[data-for=times]").forEach((x) => { x.hidden = every; });
    m.querySelectorAll("[data-for=every]").forEach((x) => { x.hidden = !every; });
  };
  m.querySelectorAll("[name=freq]").forEach((x) => x.addEventListener("change", drawFreq));
  drawFreq();
  const drawKind = () => {
    if (f.kind.value === "autopilot") {
      kp.innerHTML = `<p class="muted small">${sc("autoHelp")}</p>${conceptSelect(p.concept_id)}
        <div class="grid g2"><div><label>${sc("topic")}</label><select name="topic"><option value="random">${sc("randomTopic")}</option>${Object.keys(TOPICS).filter((k) => k !== "other").map((k) => `<option value="${k}" ${p.topic === k ? "selected" : ""}>${esc(topicLabel(k))}</option>`).join("")}</select></div>
          <div><label>${t("languages")}</label><select name="alang"><option value="random">${sc("randomLang")}</option><option value="en" ${p.language === "en" ? "selected" : ""}>English</option><option value="tr" ${p.language === "tr" ? "selected" : ""}>Türkçe</option></select></div>
          <div><label>${t("seconds")}</label><input name="seconds" type="number" min="15" max="170" value="${p.seconds || 50}"></div>
          <div><label>${sc("privacy")}</label><select name="privacy">${["public", "unlisted", "private"].map((v) => `<option value="${v}" ${(p.privacy || "public") === v ? "selected" : ""}>${sc(v)}</option>`).join("")}</select></div></div>
        <label class="row" style="margin-top:12px"><input type="checkbox" name="publish" ${p.publish === false ? "" : "checked"} style="width:auto"> ${sc("publishIt")}</label>
        ${platBoxes(p.platforms || ["youtube"])}
        <label class="row"><input type="checkbox" name="studio" checked style="width:auto"> ${sc("useStudio")}</label>`;
    } else if (f.kind.value === "produce") {
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
        ${conceptSelect(p.concept_id)}${platBoxes(p.platforms || ["youtube"])}
        <label>${t("languages")}</label><select name="language"><option value="">${sc("anyLang")}</option><option value="en" ${p.language === "en" ? "selected" : ""}>English</option><option value="tr" ${p.language === "tr" ? "selected" : ""}>Türkçe</option></select>`;
    }
  };
  drawKind();
  f.kind.addEventListener("change", drawKind);
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const kindV = f.kind.value;
    let params;
    if (kindV === "autopilot") {
      params = { topic: f.topic.value, language: f.alang.value, seconds: Number(f.seconds.value), privacy: f.privacy.value,
        publish: f.publish.checked, platforms: platValues(f).length ? platValues(f) : ["youtube"], background: "random",
        concept_id: f.concept && f.concept.value ? Number(f.concept.value) : null,
        style: f.studio.checked ? loadStyle() : (p.style || loadStyle()), voice: f.studio.checked ? loadVoice() : (p.voice || loadVoice()), music: f.studio.checked ? loadMusic() : (p.music || loadMusic()) };
    } else if (kindV === "produce") {
      params = { count: Number(f.count.value), seconds: Number(f.seconds.value), languages: ["en", "tr"].filter((l) => f[l].checked),
        auto_approve: f.auto.checked, source_id: f.source.value ? Number(f.source.value) : null, background: p.background || "random",
        style: f.studio.checked ? loadStyle() : (p.style || loadStyle()), voice: f.studio.checked ? loadVoice() : (p.voice || loadVoice()), music: f.studio.checked ? loadMusic() : (p.music || loadMusic()) };
    } else {
      params = { count: Number(f.count.value), privacy: f.privacy.value, language: f.language.value || null,
        platforms: platValues(f).length ? platValues(f) : ["youtube"], concept_id: f.concept && f.concept.value ? Number(f.concept.value) : null };
    }
    const body = { name: f.name.value, kind: kindV, enabled: s ? s.enabled : true, timezone: f.tz.value.trim() || "UTC",
      times: f.freq.value === "times" ? f.times.value.split(/[,\s]+/).filter(Boolean) : [],
      interval_min: f.freq.value === "every" ? Math.round(Number(f.hours.value) * 60) : null,
      window: f.freq.value === "every" && f.wfrom.value && f.wto.value ? [f.wfrom.value, f.wto.value] : null,
      weekdays: [0, 1, 2, 3, 4, 5, 6].filter((i) => f["d" + i].checked), params };
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
  const chans = y.channels.map((c) => `<div class="card" style="margin:8px 0;padding:10px">
      <div class="row">${c.thumbnail ? `<img src="${esc(c.thumbnail)}" style="width:28px;height:28px;border-radius:50%">` : "▶"}
      <b>${esc(c.title)}</b>${c.is_default ? ' <span class="pill ok">default</span>' : ""}
      <span class="muted small">${c.uploads_today}${c.daily_limit ? "/" + c.daily_limit : ""} ${sc("today")}</span><span class="spacer"></span>
      ${c.is_default ? "" : `<button class="btn small-btn" data-ytdef="${c.id}">${sc("makeDefault")}</button>`}
      <button class="btn danger small-btn" data-ytdel="${c.id}">${sc("disconnect")}</button></div>
      ${c.needs_reconnect ? `<div class="row" style="margin-top:6px"><span class="pill warn" title="${esc(c.last_error || "")}">⚠ ${sc("reconnectNeeded")}</span>
        <button class="btn primary small-btn" data-ytre="1">${sc("reconnect")}</button></div>` : ""}
      <form class="grid g3" data-ytch="${c.id}" style="align-items:end;margin-top:6px">
        <div><label>${sc("dailyLimit")}</label><input name="daily_limit" type="number" min="0" max="50" value="${c.daily_limit}"></div>
        <div><label>${sc("playlistField")}</label><input name="playlist" value="${esc(c.playlist_id || "")}" placeholder="https://www.youtube.com/playlist?list=PL…"></div>
        <div><button class="btn">${t("save")}</button></div></form></div>`).join("");
  const q = y.quota;
  const quotaLine = q ? `<p class="muted small">${sc("quotaLine")}: <b>${q.units}</b> / ${q.limit} · ${sc("quotaReset")} ${when(q.resets_at)}</p>` : "";
  return `<div class="card" style="margin-bottom:16px" id="ytCard"><h3>${sc("youtube")}</h3>
    <p class="muted small">${sc("ytHelp")} <a href="#" id="ytGuide">${sc("ytGuide")} ↗</a></p>
    <form id="ytc" class="grid g3" style="align-items:end">
      <div><label>${sc("clientId")}</label><input name="client_id" required value="${esc(y.client_id || "")}" placeholder="…apps.googleusercontent.com"></div>
      <div><label>${sc("clientSecret")}</label><input name="client_secret" type="password" required placeholder="${y.client_id ? "••••••••" : ""}"></div>
      <div><button class="btn">${t("save")}</button></div></form>
    ${chans ? `<label>${sc("channels")}</label>${chans}<p class="muted small">${sc("extrasNote")}</p>${quotaLine}` : ""}
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
  document.querySelectorAll("[data-ytch]").forEach((cf) => cf.addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await api(`/api/youtube/channels/${cf.dataset.ytch}`, { method: "PUT", body: { daily_limit: Number(cf.daily_limit.value || 0), playlist: cf.playlist.value.trim() } }); toast(t("saved")); render(); }
    catch (err) { toast(err.message, true); }
  }));
  on("[data-ytdef]", "click", async (e) => {
    const card = e.target.closest(".card"), cf = card.querySelector("[data-ytch]");
    try { await api(`/api/youtube/channels/${e.target.dataset.ytdef}`, { method: "PUT", body: { daily_limit: Number(cf.daily_limit.value || 0), playlist: cf.playlist.value.trim(), is_default: true } }); render(); }
    catch (err) { toast(err.message, true); }
  });
  on("[data-ytre]", "click", () => { const b = document.getElementById("ytConnect"); b && b.click(); });
  on("[data-ytdel]", "click", async (e) => { if (!confirm("?")) return; await api(`/api/youtube/channels/${e.target.dataset.ytdel}`, { method: "DELETE" }).catch((err) => toast(err.message, true)); render(); });
  const btn = document.getElementById("ytConnect");
  btn && btn.addEventListener("click", async () => {
    try {
      const was = (await api("/api/youtube")).channels, before = was.length, beforeBroken = was.some((c) => c.needs_reconnect);
      const r = await api("/api/youtube/auth", { method: "POST", body: { redirect_uri: location.origin + "/api/youtube/callback" } });
      openExternal(r.url); toast(sc("connectWait"));
      let n = 0;
      const timer = setInterval(async () => {
        n += 1;
        if (n > 100 || route() !== "settings") return clearInterval(timer);
        const y = await api("/api/youtube").catch(() => null);
        const fixed = beforeBroken && y && !y.channels.some((c) => c.needs_reconnect);
        if (y && (y.channels.length > before || fixed)) { clearInterval(timer); toast("YouTube ✓"); render(); }
      }, 3000);
    } catch (err) { toast(err.message, true); }
  });
}

// ---------- Instagram in Settings ----------
let IG_ACCOUNT = null;
async function loadInstagram() {
  try { IG_ACCOUNT = (await api("/api/instagram")).account; } catch { IG_ACCOUNT = null; }
  return IG_ACCOUNT;
}

async function instagramCard() {
  const acc = await loadInstagram();
  return `<div class="card" style="margin-bottom:16px" id="igCard"><h3>◎ ${sc("instagram")}</h3>
    <p class="muted small">${sc("igHelp")}</p>
    <p class="muted small">${sc("igSteps")} <a href="#" id="igGuide">${sc("igGuide")} ↗</a></p>
    ${acc ? `<div class="row" style="margin:8px 0"><span class="pill ok">${sc("igConnected")}</span> <b>@${esc(acc.username)}</b>
        <span class="muted small">${esc(acc.account_type)} · ${sc("igExpires")} ${when(acc.expires_at)}</span><span class="spacer"></span>
        <button class="btn danger small-btn" id="igDel">${sc("disconnect")}</button></div>`
      : `<p class="muted small">${sc("igNone")}</p>`}
    <form id="igf" class="grid g3" style="align-items:end">
      <div style="grid-column:span 2"><label>${sc("igToken")}</label><input name="token" type="password" autocomplete="off" required placeholder="IGAA…"></div>
      <div><button class="btn primary">${acc ? t("save") : "◎ " + sc("connect")}</button></div></form></div>`;
}

function bindInstagramCard() {
  const f = document.getElementById("igf");
  if (!f) return;
  document.getElementById("igGuide").addEventListener("click", (e) => { e.preventDefault(); openExternal("https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started"); });
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    try { const r = await api("/api/instagram/token", { method: "PUT", body: { access_token: f.token.value.trim() } }); toast("Instagram ✓ @" + r.account.username); render(); }
    catch (err) { toast(err.message, true); }
  });
  const del = document.getElementById("igDel");
  del && del.addEventListener("click", async () => { if (!confirm("?")) return; await api("/api/instagram", { method: "DELETE" }).catch((err) => toast(err.message, true)); render(); });
}

async function creditCard() {
  let s;
  try { s = await api("/api/publish-settings"); } catch { return ""; }
  return `<div class="card" style="margin-bottom:16px"><h3>${sc("creditTitle")}</h3>
    <label class="row" style="font-weight:400"><input type="checkbox" id="creditOn" ${s.credit_line ? "checked" : ""} style="width:auto"> ${sc("creditLabel")}</label></div>`;
}

function bindCreditCard() {
  const box = document.getElementById("creditOn");
  box && box.addEventListener("change", async () => {
    try { await api("/api/publish-settings", { method: "PUT", body: { credit_line: box.checked } }); toast(t("saved")); }
    catch (err) { toast(err.message, true); box.checked = !box.checked; }
  });
}

// ---------- Ready videos: publish to YouTube / Instagram ----------
function ytBadge(j) {
  const y = j.youtube, g = j.instagram;
  let out = "";
  if (y && y.url) out += `<a class="pill ok" href="#" data-ext="${esc(y.url)}">${y.state === "scheduled" ? sc("scheduledYt") + " · " + when(y.publish_at) : sc("onYt")} ↗</a>`;
  else if (y && y.state === "waiting") out += `<span class="pill warn" title="${esc(y.reason || "")}">${sc("waitingYt")} · ${when(y.retry_at)}</span>`;
  else if (y) out += `<span class="pill warn">${sc("queuedYt")}${y.publish_at ? " · " + when(y.publish_at) : ""}</span>`;
  if (g) {
    if (g.state === "published") out += `<a class="pill ok" href="#" data-ext="${esc(g.url)}">${sc("igOn")} ↗</a>`;
    else if (g.state === "manual") out += `<span class="pill ok">${sc("igManual")}</span>`;
    else if (g.state === "failed") out += `<span class="pill warn" title="${esc(g.error || "")}">⚠ ${sc("igFailed")}</span>`;
    else out += `<span class="pill warn">${g.state === "uploading" ? sc("igUploading") : g.publish_at ? sc("igScheduled") + " · " + when(g.publish_at) : sc("igQueued")}</span>`;
  }
  return out;
}

// What can still be done with this video, per platform.
const ytOpen = (j) => !(j.youtube && (j.youtube.id || ["queued", "waiting"].includes(j.youtube.state)));
const igOpen = (j) => !j.instagram || j.instagram.state === "failed";

function publishButtons(j) {
  let out = "";
  if (ytOpen(j) || (igOpen(j) && IG_ACCOUNT)) out += `<button class="btn primary" data-pub="${j.id}">▶ ${sc("publish")}</button>`;
  if (igOpen(j) && !IG_ACCOUNT) out += `<button class="btn" data-igman="${j.id}" title="${esc(sc("igNeedsConnect"))}">◎ ${sc("igManualBtn")}</button>`;
  return out;
}

function publishDialog(jobId, j) {
  j = j || {};
  const soon = new Date(Date.now() + 3 * 3600 * 1000);
  soon.setMinutes(0, 0, 0);
  const local = new Date(soon.getTime() - soon.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  const canYt = ytOpen(j), canIg = igOpen(j) && !!IG_ACCOUNT;
  const box = (name, label, ok) => ok ? `<label class="row"><input type="checkbox" name="pl_${name}" checked style="width:auto"> ${label}</label>` : "";
  const m = modal(`<h1>${sc("publish")}</h1><form id="pubf">
    <label>${sc("pubPlatforms")}</label><div class="row">${box("youtube", "▶ YouTube", canYt)}${box("instagram", "◎ Instagram" + (IG_ACCOUNT ? " @" + esc(IG_ACCOUNT.username) : ""), canIg)}</div>
    ${!IG_ACCOUNT && igOpen(j) ? `<p class="muted small">◎ ${sc("igNeedsConnect")}</p>` : ""}
    <label>${sc("privacy")} <span class="muted small">(${sc("ytOnly")})</span></label><select name="privacy"><option value="public">${sc("public")}</option><option value="unlisted">${sc("unlisted")}</option><option value="private">${sc("private")}</option></select>
    <label class="row" style="margin-top:12px"><input type="radio" name="mode" value="now" checked style="width:auto"> ${sc("now")}</label>
    <label class="row"><input type="radio" name="mode" value="later" style="width:auto"> ${sc("later")}</label>
    <input type="datetime-local" name="at" value="${local}">
    <div class="row" style="margin-top:16px"><button class="btn primary">${sc("publish")}</button></div></form>`);
  m.querySelector("#pubf").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target, later = f.mode.value === "later";
    const platforms = platValues(f);
    if (!platforms.length) return toast(sc("pubPlatforms") + "?", true);
    const body = { privacy: f.privacy.value, publish_at: later ? new Date(f.at.value).toISOString() : null, platforms };
    try { await api(`/api/jobs/${jobId}/publish`, { method: "POST", body }); m.remove(); toast(platforms.join(" + ") + " ✓"); render(); }
    catch (err) { toast(err.message, true); }
  });
}

async function manualInstagram(jobId) {
  let pack;
  try { pack = await api(`/api/jobs/${jobId}/instagram-pack`); } catch (err) { return toast(err.message, true); }
  const m = modal(`<h1>◎ ${sc("igManualTitle")}</h1><p class="muted small">${sc("igManualHelp")}</p>
    <ol style="line-height:1.9">
      <li><button class="btn" id="igDl">⬇ ${sc("igM1")}</button></li>
      <li><button class="btn" id="igCopy">⧉ ${sc("igM2")}</button><textarea readonly rows="6" style="width:100%;margin-top:6px">${esc(pack.caption)}</textarea></li>
      <li>${sc("igM3")} <button class="btn" id="igWeb">${sc("igOpen")} ↗</button></li></ol>
    <p class="muted small">${sc("igHelp")}</p>
    <div class="row" style="margin-top:12px"><button class="btn primary" id="igDone">✓ ${sc("igMarkDone")}</button></div>`);
  m.querySelector("#igDl").addEventListener("click", () => openExternal(location.origin + pack.video));
  m.querySelector("#igWeb").addEventListener("click", () => openExternal("https://www.instagram.com/"));
  m.querySelector("#igCopy").addEventListener("click", async () => {
    const ta = m.querySelector("textarea");
    try { await navigator.clipboard.writeText(pack.caption); } catch { ta.select(); document.execCommand("copy"); }
    toast(sc("copied"));
  });
  m.querySelector("#igDone").addEventListener("click", async () => {
    try { await api(`/api/jobs/${jobId}/instagram-manual`, { method: "POST" }); m.remove(); render(); } catch (err) { toast(err.message, true); }
  });
}
