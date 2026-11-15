"""Channel concepts: produce and publish videos with one concept's recipe, and keep its stock of ready videos."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mediafactory.db.models import Concept, ProductionJob, YouTubeChannel

# A video counts as "in stock" from the moment it is queued until it is published or thrown away.
IN_STOCK = ("discovered", "retry_wait", "script_draft", "rendering", "needs_review", "approved")
MAX_NEW_PER_RUN = 2  # never flood the render queue: top up at most two videos at a time


def out(c: Concept, *, stock: int | None = None) -> dict:
    return {
        "id": c.id, "name": c.name, "enabled": c.enabled, "language": c.language, "topic": c.topic,
        "seconds": c.seconds, "style": c.style, "voice": c.voice, "music": c.music, "background": c.background,
        "youtube_channel_id": c.youtube_channel_id, "platforms": c.platforms, "privacy": c.privacy,
        "ready_buffer": c.ready_buffer, "auto_approve": c.auto_approve, "stock": stock,
    }  # fmt: skip


def concept_of(db: Session, job: ProductionJob) -> Concept | None:
    cid = (job.payload or {}).get("concept_id")
    return db.get(Concept, int(cid)) if cid else None


def channel_for(db: Session, concept: Concept | None) -> YouTubeChannel | None:
    return db.get(YouTubeChannel, concept.youtube_channel_id) if concept and concept.youtube_channel_id else None


def jobs_of(concept_id: int):
    return ProductionJob.payload["concept_id"].as_integer() == concept_id


def stock(db: Session, concept: Concept) -> int:
    return db.scalar(select(func.count(ProductionJob.id)).where(jobs_of(concept.id), ProductionJob.status.in_(IN_STOCK))) or 0


def produce(db: Session, concept: Concept, *, origin: str, auto_approve: bool | None = None,
            auto_publish: bool = False) -> ProductionJob | None:  # fmt: skip
    """Start one video with the concept's recipe from a random unused story; None when no story is left."""
    from mediafactory.pipeline.production import start_production
    from mediafactory.schedule.runner import pick_story

    item = pick_story(db, topic=concept.topic or "random", language=concept.language)
    if item is None:
        return None
    extra: dict = {"concept_id": concept.id}
    if auto_publish:
        extra["auto_publish"] = {"privacy": concept.privacy, "platforms": concept.platforms or ["youtube"],
                                 "channel_id": concept.youtube_channel_id}  # fmt: skip
    jobs = start_production(
        db, item, languages=[concept.language], seconds=concept.seconds, background=concept.background or "random",
        style=concept.style, voice=concept.voice, music=concept.music,
        auto_approve=concept.auto_approve if auto_approve is None else auto_approve, origin=origin, extra_payload=extra,
    )  # fmt: skip
    return jobs[0]


def keep_stock(db: Session) -> list[str]:
    """Top up every enabled concept that has a stock target. Returns a line per concept that got new videos."""
    notes = []
    for c in db.scalars(select(Concept).where(Concept.enabled.is_(True), Concept.ready_buffer > 0).order_by(Concept.id)):
        missing = min(MAX_NEW_PER_RUN, c.ready_buffer - stock(db, c))
        made = 0
        for _ in range(max(0, missing)):
            if produce(db, c, origin=f"stock:{c.id}") is None:
                break
            made += 1
        if made:
            notes.append(f"{c.name}: {made} new video(s) for the stock of {c.ready_buffer}")
    return notes
