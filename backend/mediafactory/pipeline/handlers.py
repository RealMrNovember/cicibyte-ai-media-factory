"""Queue stage handlers for the production pipeline (registered when the worker imports this module)."""

from pathlib import Path

from mediafactory.core.config import get_settings
from mediafactory.queue.registry import StageContext, StageOutcome, stage_handler

MAKE_SHORT = "make_short"


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
        data_dir=Path(get_settings().data_dir),
        log=ctx.log,
    )
    ctx.job.payload = {**(ctx.job.payload or {}), "result": result}
    # Rendered and waiting in the Ready catalog for a person to approve it.
    return StageOutcome(next_status="needs_review", outputs=result)
