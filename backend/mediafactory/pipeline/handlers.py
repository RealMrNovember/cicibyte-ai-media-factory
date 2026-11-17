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
    if script.get("doctor"):
        from mediafactory.pipeline.doctor import summary

        ctx.log(f"Script Doctor: {summary(script['doctor'])}")
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
        category=inputs.get("category"),
        data_dir=Path(get_settings().data_dir),
        log=ctx.log,
    )
    ctx.job.payload = {**(ctx.job.payload or {}), "result": result}
    # Rendered: waits in the Ready catalog for approval, unless a schedule asked for automatic approval.
    # A video that fails the quality check always waits for a person, even when auto-approve is on.
    qc_ok = (result.get("qc") or {}).get("passed", True)
    status = "approved" if (ctx.job.payload or {}).get("auto_approve") and qc_ok else "needs_review"
    auto_publish = (ctx.job.payload or {}).get("auto_publish")
    if status == "approved" and auto_publish:
        from mediafactory.publishing import publish_job

        ctx.job.status = "approved"
        platforms = auto_publish.get("platforms") or ["youtube"]
        try:
            from mediafactory.db.models import YouTubeChannel

            chan = ctx.session.get(YouTubeChannel, auto_publish["channel_id"]) if auto_publish.get("channel_id") else None
            publish_job(ctx.session, ctx.job, platforms=platforms, privacy=auto_publish.get("privacy", "public"), channel=chan)
            ctx.log(f"queued for {' + '.join(platforms)} (autopilot)")
            status = ctx.job.status
        except ValueError as exc:  # e.g. no channel connected: keep it approved for later
            ctx.log(f"not published automatically: {exc}")
    elif auto_publish and not qc_ok:
        ctx.log("quality check failed: waiting for your review instead of publishing")
    return StageOutcome(next_status=status, outputs=result)


# Register the YouTube upload stage with the same worker.
import mediafactory.instagram.publish  # noqa: E402,F401
import mediafactory.tiktok.publish  # noqa: E402,F401
import mediafactory.youtube.publish  # noqa: E402,F401
