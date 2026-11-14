"""Start video production for a story (used by the Studio, the API and schedules)."""

from sqlalchemy.orm import Session

from mediafactory.db.models import ProductionJob, SourceItem
from mediafactory.pipeline.handlers import MAKE_SHORT
from mediafactory.pipeline.style import CaptionStyle
from mediafactory.queue.jobs import create_job, enqueue_stage


def start_production(
    db: Session, item: SourceItem, *, languages: list[str], seconds: int = 50, background: str = "random",
    style: CaptionStyle | dict | None = None, auto_approve: bool = False, origin: str = "manual",
) -> list[ProductionJob]:  # fmt: skip
    """One job per language, same content group, each queued for the make_short stage."""
    style_dict = style.model_dump() if isinstance(style, CaptionStyle) else CaptionStyle(**(style or {})).model_dump()
    langs = list(dict.fromkeys(languages))
    group = f"item{item.id}-{len(langs)}l"
    jobs = []
    for lang in langs:
        job = create_job(db, status="discovered", source_item_id=item.id, language=lang, content_group=group,
                         payload={"title": item.title, "auto_approve": auto_approve, "origin": origin})  # fmt: skip
        enqueue_stage(db, job.id, MAKE_SHORT, "render", inputs={
            "item_id": item.id, "language": lang, "seconds": seconds, "background": background, "style": style_dict,
        })  # fmt: skip
        jobs.append(job)
    item.processing_status = "queued"
    return jobs
