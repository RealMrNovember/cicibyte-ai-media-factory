"""Queue stage handlers for the production pipeline (registered when the worker imports this module)."""

from pathlib import Path

from mediafactory.core.config import get_settings
from mediafactory.queue.registry import StageContext, StageOutcome, stage_handler

MAKE_SHORT = "make_short"
DRAFT_SCRIPT = "draft_script"


@stage_handler(DRAFT_SCRIPT, "llm")
def draft_script_stage(ctx: StageContext) -> StageOutcome:
    """Write the script only and stop, so a person can edit it before voice and video are made."""
    from mediafactory.db.models import SourceItem
    from mediafactory.pipeline.script import generate_script

    inputs = ctx.run.inputs or {}
    item = ctx.session.get(SourceItem, int(inputs["item_id"]))
    if item is None:
        raise ValueError(f"source item {inputs['item_id']} not found")
    ctx.log(f"writing the script ({inputs.get('language', 'en')}) for review: {item.title[:70]}")
    script = generate_script(ctx.session, item, language=inputs.get("language", "en"), seconds=int(inputs.get("seconds", 50)))
    ctx.job.payload = {**(ctx.job.payload or {}), "script": script, "title": script.get("title") or item.title}
    ctx.log(f"-> '{script['title']}' ({len(script['narration'].split())} words); waiting for your review")
    return StageOutcome(next_status="script_draft", outputs={"title": script["title"]})


@stage_handler(MAKE_SHORT, "render")
def make_short_stage(ctx: StageContext) -> StageOutcome:
    from mediafactory.pipeline.make import make_short

    inputs = ctx.run.inputs or {}
    result = make_short(
        ctx.session,
        int(inputs["item_id"]),
        language=inputs.get("language", "en"),
        seconds=int(inputs.get("seconds", 50)),
        background_choice=inputs.get("background", "random"),
        style=inputs.get("style"),
        script=inputs.get("script"),
        voice=inputs.get("voice"),
        music=inputs.get("music"),
        data_dir=Path(get_settings().data_dir),
        log=ctx.log,
    )
    ctx.job.payload = {**(ctx.job.payload or {}), "result": result}
    # Rendered: waits in the Ready catalog for approval, unless a schedule asked for automatic approval.
    # A video that fails the quality check always waits for a person, even when auto-approve is on.
    qc_ok = (result.get("qc") or {}).get("passed", True)
    status = "approved" if (ctx.job.payload or {}).get("auto_approve") and qc_ok else "needs_review"
    return StageOutcome(next_status=status, outputs=result)


# Register the YouTube upload stage with the same worker.
import mediafactory.youtube.publish  # noqa: E402,F401
