"""Runs due schedules: produce new videos from fresh stories, or publish approved videos to YouTube."""

import logging
import threading
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from mediafactory.db.models import ProductionJob, Schedule, SourceItem
from mediafactory.schedule.timing import next_run

log = logging.getLogger(__name__)


def plan_next(schedule: Schedule, now: datetime) -> None:
    schedule.next_run_at = next_run(schedule.times, schedule.weekdays, schedule.timezone, now) if schedule.enabled else None


def run_produce(db: Session, schedule: Schedule) -> str:
    from mediafactory.pipeline.production import start_production

    p = schedule.params or {}
    q = select(SourceItem).where(SourceItem.processing_status == "discovered", SourceItem.rights_status != "restricted")
    if p.get("source_id"):
        q = q.where(SourceItem.source_id == int(p["source_id"]))
    if p.get("min_chars"):
        q = q.where(func.length(SourceItem.normalized_text) >= int(p["min_chars"]))
    items = list(db.scalars(q.order_by(SourceItem.fetched_at.desc()).limit(max(1, min(20, int(p.get("count", 1)))))))
    jobs = 0
    for item in items:
        jobs += len(start_production(
            db, item, languages=p.get("languages") or ["en"], seconds=int(p.get("seconds", 50)),
            background=p.get("background", "random"), style=p.get("style"), auto_approve=bool(p.get("auto_approve")),
            origin=f"schedule:{schedule.id}",
        ))  # fmt: skip
    return f"{len(items)} stories → {jobs} videos" if items else "no unused stories to produce from"


def run_publish(db: Session, schedule: Schedule) -> str:
    from mediafactory.youtube.publish import queue_upload

    p = schedule.params or {}
    candidates = db.scalars(
        select(ProductionJob).where(ProductionJob.status == "approved").order_by(ProductionJob.updated_at).limit(50)
    )
    sent = 0
    for job in candidates:
        if sent >= max(1, min(10, int(p.get("count", 1)))):
            break
        if (job.payload or {}).get("youtube", {}).get("id") or (p.get("language") and job.language != p["language"]):
            continue
        queue_upload(db, job, privacy=p.get("privacy", "public"))
        sent += 1
    return f"{sent} videos sent to YouTube" if sent else "no approved videos waiting"


ACTIONS = {"produce": run_produce, "publish": run_publish}


def run_due(factory: Callable[[], Session], *, now: datetime | None = None, limit: int = 10) -> int:
    """Run every enabled schedule whose time has come (each in its own transaction)."""
    now = now or datetime.now(timezone.utc)
    with factory() as db:
        ids = list(db.scalars(select(Schedule.id).where(Schedule.enabled.is_(True), Schedule.next_run_at <= now)
                              .order_by(Schedule.next_run_at).limit(limit)))  # fmt: skip
    done = 0
    for sid in ids:
        with factory() as db:
            sch = db.scalar(select(Schedule).where(Schedule.id == sid).with_for_update(skip_locked=True))
            if sch is None or not sch.enabled or sch.next_run_at is None or sch.next_run_at > now:
                continue
            try:
                with db.begin_nested():
                    sch.last_result = ACTIONS[sch.kind](db, sch)
            except Exception as exc:  # one broken schedule must not stop the others
                log.exception("schedule %s failed", sid)
                sch.last_result = f"error: {exc}"[:1000]
            sch.last_run_at = now
            plan_next(sch, now)
            db.commit()
            done += 1
    return done


class Scheduler(threading.Thread):
    def __init__(self, factory: Callable[[], Session], *, stop_event: threading.Event, interval_s: float = 20):
        super().__init__(name="scheduler", daemon=True)
        self.factory, self.stop_event, self.interval_s = factory, stop_event, interval_s

    def run(self) -> None:
        log.info("scheduler started (every %ss)", self.interval_s)
        while not self.stop_event.is_set():
            try:
                run_due(self.factory)
            except OperationalError as exc:
                log.warning("database unavailable for schedules (%s)", type(exc).__name__)
            except Exception:
                log.exception("scheduler iteration failed")
            self.stop_event.wait(self.interval_s)
