// Live: what is being produced right now, the queue, schedules, sources and the worker.
"use strict";

const LV = {
  en: {
    live: "Live", liveSub: "Follow production as it happens. Updates every few seconds.", nowMaking: "Being made now",
    nothingRunning: "Nothing is being produced right now.", queue: "Waiting in the queue", noQueue: "The queue is empty.",
    activeSchedules: "Active schedules", noSchedules: "No active schedules.", inMin: "in", agoMin: "ago", elapsed: "elapsed",
    worker: "Worker", alive: "running", down: "not responding", sources: "Sources", lastCollect: "last collect",
    errors: "with errors", openJob: "Details", step_script: "Writing the script", step_writing: "Writing the script",
    step_voice: "Recording the voice", step_captions: "Timing the captions", step_render: "Rendering the video",
    "step_cover image": "Cover & quality check", step_uploading: "Uploading to YouTube", step_null: "Starting",
  },
  tr: {
    live: "Canlı", liveSub: "Üretimi anında takip et. Birkaç saniyede bir güncellenir.", nowMaking: "Şu an üretilen",
    nothingRunning: "Şu anda üretilen bir şey yok.", queue: "Kuyrukta bekleyen", noQueue: "Kuyruk boş.",
    activeSchedules: "Aktif zamanlamalar", noSchedules: "Aktif zamanlama yok.", inMin: "sonra", agoMin: "önce", elapsed: "geçti",
    worker: "İşçi", alive: "çalışıyor", down: "yanıt vermiyor", sources: "Kaynaklar", lastCollect: "son toplama",
    errors: "hatalı", openJob: "Ayrıntı", step_script: "Senaryo yazılıyor", step_writing: "Senaryo yazılıyor",
    step_voice: "Ses kaydediliyor", step_captions: "Altyazı zamanlanıyor", step_render: "Video render ediliyor",
    "step_cover image": "Kapak ve kalite kontrolü", step_uploading: "YouTube'a yükleniyor", step_null: "Başlıyor",
  },
};
const lv = (k) => (LV[lang] && LV[lang][k]) || k;

function mmss(s) { s = Math.max(0, Math.round(s)); const m = Math.floor(s / 60); return `${m}:${String(s % 60).padStart(2, "0")}`; }
function relTime(iso) {
  if (!iso) return "—";
  const d = (new Date(iso).getTime() - Date.now()) / 1000, a = Math.abs(d);
  const txt = a < 60 ? `${Math.round(a)} sn` : a < 3600 ? `${Math.round(a / 60)} dk` : `${Math.floor(a / 3600)} sa ${Math.round((a % 3600) / 60)} dk`;
  const en = txt.replace(" sn", " s").replace(" dk", " min").replace(" sa", " h");
  return lang === "tr" ? `${txt} ${d >= 0 ? lv("inMin") : lv("agoMin")}` : (d >= 0 ? `in ${en}` : `${en} ago`);
}

async function live(el) {
  const draw = async () => {
    if (route() !== "live") return clearInterval(pollTimer);
    let a;
    try { a = await api("/api/activity"); } catch (err) { return; }
    const logOpen = {};
    el.querySelectorAll("details[data-run]").forEach((d) => { logOpen[d.dataset.run] = d.open; });
    const running = a.running.map((r) => `<div class="card live-run">
        <div class="row"><b>#${r.job_id} · ${esc(r.title)}</b><span class="pill">${esc((r.language || "").toUpperCase())}</span><span class="spacer"></span>
          <span class="muted small">${mmss(r.elapsed_s)} ${lv("elapsed")}</span><button class="btn small-btn" data-job="${r.job_id}">${lv("openJob")}</button></div>
        <div class="live-step"><span class="dot-live"></span>${esc(lv("step_" + r.step))}</div>
        <div class="progress live-bar"><div style="width:${Math.round(r.progress * 100)}%"></div></div>
        <details data-run="${r.run_id}" ${logOpen[r.run_id] === false ? "" : "open"}><summary class="muted small">log</summary><pre class="live-log">${esc(r.log || "…")}</pre></details>
      </div>`).join("") || `<div class="card"><p class="muted" style="margin:0">${lv("nothingRunning")}</p></div>`;
    const queue = a.queued.length ? `<table>${a.queued.map((q) => `<tr><td><b>#${q.job_id}</b> ${esc(q.title)}</td><td class="small muted">${esc(q.stage)}</td><td>${pill(q.state)}</td><td class="small muted">${q.state === "retry_wait" ? relTime(q.run_after) : ""}</td></tr>`).join("")}</table>` : `<p class="muted" style="margin:0">${lv("noQueue")}</p>`;
    const sch = a.schedules.length ? `<table>${a.schedules.map((s) => `<tr><td><b>${esc(s.name)}</b><div class="muted small">${s.kind === "autopilot" ? "🤖 " : ""}${esc(s.kind)}${s.interval_min ? ` · ${+(s.interval_min / 60).toFixed(2)} h` : ""}</div></td>
        <td class="small">${s.next_run_at ? relTime(s.next_run_at) : "—"}</td><td class="small muted clip">${esc(s.last_result || "")}</td></tr>`).join("")}</table>` : `<p class="muted" style="margin:0">${lv("noSchedules")}</p>`;
    el.innerHTML = `<h1>${lv("live")}</h1><p class="sub">${lv("liveSub")}</p>
      <div class="row" style="margin-bottom:14px;gap:8px">
        <span class="pill ${a.worker.alive ? "ok" : "bad"}">${lv("worker")}: ${a.worker.alive ? lv("alive") : lv("down")}</span>
        <span class="pill">${lv("sources")}: ${a.sources.enabled} · ${lv("lastCollect")} ${relTime(a.sources.last_run_at)}${a.sources.with_errors ? ` · ${a.sources.with_errors} ${lv("errors")}` : ""}</span>
        <span class="pill">${esc(a.summary[lang] || a.summary.en)}</span></div>
      <h3>${lv("nowMaking")}</h3><div class="grid" style="gap:12px;margin-bottom:18px">${running}</div>
      <div class="grid g2" style="align-items:start"><div class="card"><h3>${lv("queue")} (${a.counts.queued})</h3>${queue}</div>
        <div class="card"><h3>${lv("activeSchedules")}</h3>${sch}</div></div>`;
    el.querySelectorAll(".live-log").forEach((pre) => { pre.scrollTop = pre.scrollHeight; });
    bindJobs(el);
  };
  await draw();
  pollTimer = setInterval(draw, 3000);
}

// Thin live summary under the brand in the sidebar (also for people using a browser).
async function refreshLiveMini() {
  const box = document.getElementById("liveMini");
  if (!box) return;
  try {
    const a = await api("/api/activity");
    box.textContent = a.summary[lang] || a.summary.en;
    box.className = "live-mini" + (a.counts.running ? " on" : "");
  } catch { box.textContent = ""; }
}
setInterval(refreshLiveMini, 5000);
