"""Live activity: what is being produced right now, the queue, schedules, sources and the worker.

Used by the Live page and by the desktop app's window title.
"""

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mediafactory.api.deps import get_db, require_user
from mediafactory.db.models import JobStageRun, ProductionJob, Schedule, SourceConnector, SystemSetting, User

router = APIRouter(prefix="/api", tags=["activity"])
WORKER_ALIVE_S = 90
STEP = re.compile(r"^\[(\d)/4\]\s*(\w+)|^\[\+\]\s*(.+?)\s*$", re.M)
STEP_TR = {"script": "senaryo", "voice": "ses", "captions": "altyazı", "render": "render", "cover image": "kapak",
           "writing": "senaryo", "uploading": "yükleme"}  # fmt: skip


def progress_from_log(log: str) -> tuple[float, str | None]:
    """Rough progress of a make_short run from its step markers ([n/4] … [+] …)."""
    last = None
    for m in STEP.finditer(log or ""):
        last = m
    if last is None:
        return 0.0, None
    if last.group(3):
        return 0.95, last.group(3).split(" and ")[0]
    n = int(last.group(1))
    return (n - 0.5) / 4, last.group(2)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _fmt_elapsed(s: float) -> str:
    m, sec = divmod(int(s), 60)
    return f"{m}:{sec:02d}"


@router.get("/activity")
def activity(db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    now = datetime.now(timezone.utc)
    rows = db.execute(
        select(JobStageRun, ProductionJob).join(ProductionJob, ProductionJob.id == JobStageRun.job_id)
        .where(JobStageRun.state.in_(("running", "queued", "retry_wait"))).order_by(JobStageRun.id)
    ).all()  # fmt: skip
    running, queued = [], []
    for run, job in rows:
        title = (job.payload or {}).get("title") or f"#{job.id}"
        base = {"job_id": job.id, "run_id": run.id, "title": title, "language": job.language, "stage": run.stage,
                "job_class": run.job_class}  # fmt: skip
        if run.state == "running":
            progress, step = progress_from_log(run.log or "")
            if run.stage != "make_short":
                step = {"draft_script": "writing", "upload_youtube": "uploading"}.get(run.stage, run.stage)
                progress = 0.5
            elapsed = (now - run.started_at).total_seconds() if run.started_at else 0
            running.append({**base, "step": step, "progress": round(progress, 3), "elapsed_s": round(elapsed),
                            "started_at": _iso(run.started_at), "worker": run.locked_by,
                            "log": "\n".join((run.log or "").splitlines()[-40:])})  # fmt: skip
        else:
            queued.append({**base, "state": run.state, "run_after": _iso(run.run_after), "attempts": run.attempts})

    schedules = [{"id": s.id, "name": s.name, "kind": s.kind, "next_run_at": _iso(s.next_run_at),
                  "last_run_at": _iso(s.last_run_at), "last_result": s.last_result, "interval_min": s.interval_min}
                 for s in db.scalars(select(Schedule).where(Schedule.enabled.is_(True)).order_by(Schedule.next_run_at))]  # fmt: skip
    src = db.execute(select(func.count(), func.max(SourceConnector.last_run_at), func.min(SourceConnector.next_run_at),
                            func.count().filter(SourceConnector.last_error.is_not(None)))
                     .where(SourceConnector.enabled.is_(True), SourceConnector.deleted_at.is_(None))).one()  # fmt: skip
    hb = db.get(SystemSetting, "worker.heartbeat")
    hb_at = datetime.fromisoformat(hb.value["at"]) if hb and isinstance(hb.value, dict) and hb.value.get("at") else None
    alive = bool(hb_at and (now - hb_at).total_seconds() < WORKER_ALIVE_S) or bool(running)

    if running:
        r = running[0]
        step_en = r["step"] or "starting"
        extra = f" · {len(queued)} queued" if queued else ""
        extra_tr = f" · {len(queued)} sırada" if queued else ""
        summary = {"en": f"● Producing #{r['job_id']} · {step_en} · {_fmt_elapsed(r['elapsed_s'])}{extra}",
                   "tr": f"● Üretiliyor #{r['job_id']} · {STEP_TR.get(step_en, step_en)} · {_fmt_elapsed(r['elapsed_s'])}{extra_tr}"}  # fmt: skip
    else:
        nxt = next((s for s in schedules if s["next_run_at"]), None)
        when = ""
        if nxt:
            mins = max(0, int((datetime.fromisoformat(nxt["next_run_at"]) - now).total_seconds() // 60))
            when = f"{mins // 60} h {mins % 60} min" if mins >= 60 else f"{mins} min"
        summary = {"en": f"Idle{f' · {len(queued)} queued' if queued else ''}{f' · next: {nxt['name']} in {when}' if nxt else ''}",
                   "tr": f"Boşta{f' · {len(queued)} sırada' if queued else ''}{f' · sonraki: {nxt['name']} ({when} sonra)' if nxt else ''}"}  # fmt: skip
    return {
        "now": _iso(now),
        "running": running,
        "queued": queued,
        "counts": {"running": len(running), "queued": len(queued)},
        "schedules": schedules,
        "sources": {"enabled": src[0], "last_run_at": _iso(src[1]), "next_run_at": _iso(src[2]), "with_errors": src[3]},
        "worker": {"alive": alive, "id": hb.value.get("id") if hb else None, "seen_at": _iso(hb_at)},
        "summary": summary,
    }

