// Channels & concepts (on the Schedule page): one recipe per channel + a stock of ready videos.
"use strict";

const CC = {
  en: {
    concepts: "Channels & concepts",
    conceptsHelp: "A concept is one recipe for a channel: language, topic, length, voice, caption style, music and where it is published. Autopilot and publishing schedules can follow a concept. With a stock target the server keeps that many of its videos ready (waiting for review or approved) and makes new ones when the stock runs low.",
    newConcept: "New concept", stockTarget: "Stock target (ready videos)", stockOff: "0 = off", stockNow: "in stock",
    autoApproveC: "Approve its videos automatically when they pass the quality check", channel: "YouTube channel",
    defaultChannel: "Default channel", makeOne: "Make one now", made: "Video started", saveStudio: "Use my current Studio caption style, voice and music",
    keepRecipe: "Keep the saved style, voice and music", followConcept: "Follow a concept", noConcept: "— none (use the settings below) —",
    conceptNote: "When a concept is chosen, its language, topic, voice, look, channel, platforms and visibility are used.",
  },
  tr: {
    concepts: "Kanallar ve konseptler",
    conceptsHelp: "Konsept, bir kanalın tarifidir: dil, konu, süre, ses, altyazı stili, müzik ve nerede yayınlanacağı. Otopilot ve yayın zamanlamaları bir konsepti izleyebilir. Stok hedefi verirsen sunucu o konseptten o kadar videoyu hazırda (inceleme bekleyen ya da onaylı) tutar; stok azalınca yenilerini üretir.",
    newConcept: "Yeni konsept", stockTarget: "Stok hedefi (hazır video)", stockOff: "0 = kapalı", stockNow: "stokta",
    autoApproveC: "Kalite kontrolünden geçen videolarını otomatik onayla", channel: "YouTube kanalı",
    defaultChannel: "Varsayılan kanal", makeOne: "Şimdi bir tane üret", made: "Video başladı", saveStudio: "Stüdyo'daki mevcut altyazı stilimi, sesimi ve müziğimi kullan",
    keepRecipe: "Kayıtlı stil, ses ve müziği koru", followConcept: "Konsepti izle", noConcept: "— yok (aşağıdaki ayarları kullan) —",
    conceptNote: "Konsept seçilirse onun dili, konusu, sesi, görünümü, kanalı, platformları ve görünürlüğü kullanılır.",
  },
};
const cc = (k) => (CC[lang] && CC[lang][k]) || sc(k);
let CONCEPTS = [];

async function loadConcepts() {
  try { CONCEPTS = (await api("/api/concepts")).items; } catch { CONCEPTS = []; }
  return CONCEPTS;
}

function conceptSelect(selected) {
  return `<label>${cc("followConcept")}</label><select name="concept"><option value="">${cc("noConcept")}</option>
    ${CONCEPTS.map((c) => `<option value="${c.id}" ${selected === c.id ? "selected" : ""}>${esc(c.name)}</option>`).join("")}</select>
    <p class="muted small">${cc("conceptNote")}</p>`;
}

async function conceptsCard() {
  const [items, yt] = await Promise.all([loadConcepts(), api("/api/youtube").catch(() => ({ channels: [] }))]);
  const chanName = (id) => (yt.channels.find((c) => c.id === id) || {}).title || cc("defaultChannel");
  const rows = items.map((c) => `<tr>
      <td><b>${esc(c.name)}</b><div class="muted small">${esc(c.language)} · ${esc(c.topic === "random" ? sc("randomTopic") : topicLabel(c.topic))} · ${c.seconds}s · ${esc(c.platforms.join(" + "))}</div></td>
      <td class="small">▶ ${esc(chanName(c.youtube_channel_id))}<div class="muted">${esc(sc(c.privacy))}</div></td>
      <td class="small">${c.ready_buffer ? `<b>${c.stock}</b> / ${c.ready_buffer} ${cc("stockNow")}${c.auto_approve ? " · auto ✓" : ""}` : `<span class="muted">—</span>`}</td>
      <td><div class="row"><button class="btn" data-cmake="${c.id}">＋ ${cc("makeOne")}</button><button class="btn" data-cedit="${c.id}">${sc("edit")}</button>
        <button class="btn danger" data-cdel="${c.id}">${t("delete")}</button></div></td></tr>`).join("");
  return `<div class="card" style="margin-top:16px" id="conceptCard"><div class="row"><h3>${cc("concepts")}</h3><span class="spacer"></span>
      <button class="btn" id="newConcept">＋ ${cc("newConcept")}</button></div>
    <p class="muted small">${cc("conceptsHelp")}</p>
    ${rows ? `<table>${rows}</table>` : `<p class="muted">${t("noData")}</p>`}</div>`;
}

function bindConceptsCard() {
  const btn = document.getElementById("newConcept");
  if (!btn) return;
  const byId = Object.fromEntries(CONCEPTS.map((c) => [c.id, c]));
  btn.addEventListener("click", () => conceptDialog(null));
  on("[data-cedit]", "click", (e) => conceptDialog(byId[e.target.dataset.cedit]));
  on("[data-cdel]", "click", async (e) => { if (!confirm("?")) return; try { await api(`/api/concepts/${e.target.dataset.cdel}`, { method: "DELETE" }); render(); } catch (err) { toast(err.message, true); } });
  on("[data-cmake]", "click", async (e) => {
    try { const r = await api(`/api/concepts/${e.target.dataset.cmake}/produce`, { method: "POST" }); toast(`${cc("made")}: #${r.job_id} ${r.title || ""}`); render(); }
    catch (err) { toast(err.message, true); }
  });
}

async function conceptDialog(c) {
  const yt = await api("/api/youtube").catch(() => ({ channels: [] }));
  const v = c || { language: "tr", topic: "random", seconds: 50, platforms: ["youtube"], privacy: "public", ready_buffer: 0, auto_approve: false, enabled: true };
  const m = modal(`<h1>${c ? esc(c.name) : cc("newConcept")}</h1><form id="cf">
    <div class="grid g2"><div><label>${t("name")}</label><input name="name" required maxlength="120" value="${esc(v.name || "")}" placeholder="Gece Hikâyeleri TR"></div>
      <div><label>${t("languages")}</label><select name="language"><option value="tr" ${v.language === "tr" ? "selected" : ""}>Türkçe</option><option value="en" ${v.language === "en" ? "selected" : ""}>English</option></select></div>
      <div><label>${sc("topic")}</label><select name="topic"><option value="random">${sc("randomTopic")}</option>${Object.keys(TOPICS).filter((k) => k !== "other").map((k) => `<option value="${k}" ${v.topic === k ? "selected" : ""}>${esc(topicLabel(k))}</option>`).join("")}</select></div>
      <div><label>${t("seconds")}</label><input name="seconds" type="number" min="15" max="170" value="${v.seconds}"></div>
      <div><label>${cc("channel")}</label><select name="channel"><option value="">${cc("defaultChannel")}</option>${yt.channels.map((ch) => `<option value="${ch.id}" ${v.youtube_channel_id === ch.id ? "selected" : ""}>${esc(ch.title)}</option>`).join("")}</select></div>
      <div><label>${sc("privacy")}</label><select name="privacy">${["public", "unlisted", "private"].map((x) => `<option value="${x}" ${v.privacy === x ? "selected" : ""}>${sc(x)}</option>`).join("")}</select></div></div>
    ${platBoxes(v.platforms)}
    <div class="grid g2"><div><label>${cc("stockTarget")}</label><input name="buffer" type="number" min="0" max="20" value="${v.ready_buffer}"><div class="muted small">${cc("stockOff")}</div></div></div>
    <label class="row" style="margin-top:8px"><input type="checkbox" name="auto" ${v.auto_approve ? "checked" : ""} style="width:auto"> ${cc("autoApproveC")}</label>
    <label class="row"><input type="checkbox" name="studio" ${c ? "" : "checked"} style="width:auto"> ${cc("saveStudio")}</label>
    ${c ? `<p class="muted small">${cc("keepRecipe")}: ☐</p>` : ""}
    <div class="row" style="margin-top:16px"><button class="btn primary">${t("save")}</button></div></form>`);
  m.querySelector("#cf").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target, fromStudio = f.studio.checked;
    const platforms = platValues(f);
    const body = { name: f.name.value.trim(), enabled: v.enabled !== false, language: f.language.value, topic: f.topic.value,
      seconds: Number(f.seconds.value), youtube_channel_id: f.channel.value ? Number(f.channel.value) : null,
      platforms: platforms.length ? platforms : ["youtube"], privacy: f.privacy.value, ready_buffer: Number(f.buffer.value || 0),
      auto_approve: f.auto.checked, background: v.background || "random",
      style: fromStudio || !c ? loadStyle() : c.style, voice: fromStudio || !c ? loadVoice() : c.voice, music: fromStudio || !c ? loadMusic() : c.music };
    try { await api(c ? `/api/concepts/${c.id}` : "/api/concepts", { method: c ? "PUT" : "POST", body }); m.remove(); toast(t("saved")); render(); }
    catch (err) { toast(err.message, true); }
  });
}
