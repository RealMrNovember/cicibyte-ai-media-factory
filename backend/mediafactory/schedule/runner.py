"""Runs due schedules: produce new videos from fresh stories, or publish approved videos to YouTube."""

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from mediafactory.db.models import Concept, ProductionJob, Schedule, SourceItem
from mediafactory.schedule.timing import next_interval, next_run

log = logging.getLogger(__name__)


def plan_next(schedule: Schedule, now: datetime) -> None:
    if not schedule.enabled:
        schedule.next_run_at = None
    elif schedule.interval_min:
        schedule.next_run_at = next_interval(schedule.interval_min, schedule.weekdays, schedule.window, schedule.timezone, now)
    else:
        schedule.next_run_at = next_run(schedule.times, schedule.weekdays, schedule.timezone, now)


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
            voice=p.get("voice"), music=p.get("music"),
            origin=f"schedule:{schedule.id}",
        ))  # fmt: skip
    return f"{len(items)} stories → {jobs} videos" if items else "no unused stories to produce from"


def run_publish(db: Session, schedule: Schedule) -> str:
    from mediafactory.concepts import channel_for, jobs_of
    from mediafactory.publishing import publish_job

    p = schedule.params or {}
    concept = db.get(Concept, int(p["concept_id"])) if p.get("concept_id") else None
    platforms = (concept.platforms if concept else None) or p.get("platforms") or ["youtube"]
    privacy = concept.privacy if concept else p.get("privacy", "public")
    q = select(ProductionJob).where(ProductionJob.status == "approved")
    if concept:
        q = q.where(jobs_of(concept.id))
    candidates = db.scalars(q.order_by(ProductionJob.updated_at).limit(50))
    sent = 0
    for job in candidates:
        if sent >= max(1, min(10, int(p.get("count", 1)))):
            break
        if (job.payload or {}).get("youtube", {}).get("id") or (job.payload or {}).get("instagram") or (
            p.get("language") and job.language != p["language"]
        ):
            continue
        publish_job(db, job, platforms=platforms, privacy=privacy, channel=channel_for(db, concept))
        sent += 1
    return f"{sent} videos sent to {' + '.join(platforms)}" if sent else "no approved videos waiting"


def pick_story(db: Session, *, topic: str = "random", language: str = "random", rng=None) -> SourceItem | None:
    """A random unused story of the topic/language. topic "random" first picks a random topic that has stories."""
    import random as _random

    from mediafactory.api.routes.items import _source_topics

    rng = rng or _random
    q = select(SourceItem.id, SourceItem.source_id, SourceItem.source_type).where(
        SourceItem.processing_status == "discovered", SourceItem.rights_status != "restricted",
        func.length(SourceItem.normalized_text) >= 300,
    )  # fmt: skip
    if language == "en":
        q = q.where((SourceItem.language == "en") | SourceItem.language.is_(None))
    elif language == "tr":
        q = q.where(SourceItem.language == "tr")
    topics = _source_topics(db)
    by_topic: dict[str, list[int]] = {}
    for iid, sid, stype in db.execute(q):
        cat = "manual" if stype == "manual" or sid is None else topics.get(sid, ("", "other"))[1]
        by_topic.setdefault(cat, []).append(iid)
    if topic != "random":
        by_topic = {topic: by_topic.get(topic, [])}
    by_topic = {k: v for k, v in by_topic.items() if v}
    if not by_topic:
        return None
    chosen = rng.choice(sorted(by_topic))
    return db.get(SourceItem, rng.choice(by_topic[chosen]))


def run_autopilot(db: Session, schedule: Schedule) -> str:
    from mediafactory.pipeline.production import start_production

    p = schedule.params or {}
    if p.get("concept_id"):
        from mediafactory.concepts import produce

        concept = db.get(Concept, int(p["concept_id"]))
        if concept is None:
            return "the concept of this schedule was deleted"
        job = produce(db, concept, origin=f"autopilot:{schedule.id}", auto_approve=True, auto_publish=p.get("publish", True))
        if job is None:
            return f"no unused story for the concept “{concept.name}”"
        return f"{concept.name}: “{(job.payload or {}).get('title', '')[:60]}” → video #{job.id}{' (will be published)' if p.get('publish', True) else ''}"
    item = pick_story(db, topic=p.get("topic", "random"), language=p.get("language", "random"))
    if item is None:
        return "no unused story for this topic/language"
    lang = item.language or "en" if p.get("language", "random") == "random" else p["language"]
    jobs = start_production(
        db, item, languages=[lang if lang in ("en", "tr") else "en"], seconds=int(p.get("seconds", 50)),
        background=p.get("background", "random"), style=p.get("style"), voice=p.get("voice"), music=p.get("music"),
        auto_approve=True, origin=f"autopilot:{schedule.id}",
        extra_payload={"auto_publish": {"privacy": p.get("privacy", "public"), "platforms": p.get("platforms") or ["youtube"]}}
        if p.get("publish", True) else None,
    )  # fmt: skip
    return f"“{item.title[:60]}” → video #{jobs[0].id}{' (will be published)' if p.get('publish', True) else ''}"


ACTIONS = {"produce": run_produce, "publish": run_publish, "autopilot": run_autopilot}


def run_due(factory: Callable[[], Session], *, now: datetime | None = None, limit: int = 10) -> int:
    """Run every enabled schedule whose time has come (each in its own transaction)."""
    now = now or datetime.now(UTC)
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

    _token_checked = 0.0
    _stock_checked = 0.0

    def _keep_stock(self) -> None:
        """Every 10 minutes: produce videos for concepts whose ready stock is below its target."""
        import time as _time

        from mediafactory.concepts import keep_stock

        if _time.monotonic() - self._stock_checked < 600:
            return
        self._stock_checked = _time.monotonic()
        with self.factory() as db:
            for note in keep_stock(db):
                log.info("stock: %s", note)
            db.commit()

    def _keep_instagram_token(self) -> None:
        """Once an hour: refresh the Instagram token when due, so it does not expire unused (60 days)."""
        import time as _time

        from mediafactory.instagram.client import InstagramError
        from mediafactory.instagram.publish import refresh_stored_token

        if _time.monotonic() - self._token_checked < 3600:
            return
        self._token_checked = _time.monotonic()
        with self.factory() as db:
            try:
                refresh_stored_token(db)
                db.commit()
            except InstagramError as exc:
                log.warning("Instagram token refresh failed: %s", exc)

    def run(self) -> None:
        log.info("scheduler started (every %ss)", self.interval_s)
        while not self.stop_event.is_set():
            try:
                run_due(self.factory)
                self._keep_instagram_token()
                self._keep_stock()
            except OperationalError as exc:
                log.warning("database unavailable for schedules (%s)", type(exc).__name__)
            except Exception:
                log.exception("scheduler iteration failed")
            self.stop_event.wait(self.interval_s)
