"""Start video production for a story (used by the Studio, the API and schedules)."""

from sqlalchemy.orm import Session

from mediafactory.db.models import ProductionJob, SourceItem
from mediafactory.pipeline.handlers import DRAFT_SCRIPT, MAKE_SHORT
from mediafactory.pipeline.style import CaptionStyle
from mediafactory.pipeline.voice import VoiceSettings
from mediafactory.queue.jobs import create_job, enqueue_stage


def start_production(
    db: Session, item: SourceItem, *, languages: list[str], seconds: int = 50, background: str = "random",
    style: CaptionStyle | dict | None = None, auto_approve: bool = False, origin: str = "manual",
    review_script: bool = False, voice: dict | None = None,
) -> list[ProductionJob]:  # fmt: skip
    """One job per language, same content group, each queued for the make_short stage."""
    style_dict = style.model_dump() if isinstance(style, CaptionStyle) else CaptionStyle(**(style or {})).model_dump()
    voice_dict = VoiceSettings(**(voice or {})).model_dump()
    langs = list(dict.fromkeys(languages))
    group = f"item{item.id}-{len(langs)}l"
    jobs = []
    for lang in langs:
        make = {"item_id": item.id, "language": lang, "seconds": seconds, "background": background, "style": style_dict,
                "voice": voice_dict}  # fmt: skip
        job = create_job(db, status="discovered", source_item_id=item.id, language=lang, content_group=group,
                         payload={"title": item.title, "auto_approve": auto_approve, "origin": origin, "make": make})  # fmt: skip
        if review_script:
            enqueue_stage(db, job.id, DRAFT_SCRIPT, "llm", inputs=make)
        else:
            enqueue_stage(db, job.id, MAKE_SHORT, "render", inputs=make)
        jobs.append(job)
    item.processing_status = "queued"
    return jobs
