from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from mediafactory.db.base import utcnow
from mediafactory.db.models import JobStageRun

# Serialises claims across workers so per-class running counts are exact; claims are short.
_CLAIM_LOCK_KEY = 7_340_001


def claim_next(session: Session, *, worker_id: str, limits: dict[str, int]) -> JobStageRun | None:
    session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _CLAIM_LOCK_KEY})
    running = dict(
        session.execute(
            select(JobStageRun.job_class, func.count()).where(JobStageRun.state == "running").group_by(JobStageRun.job_class)
        ).all()
    )
    open_classes = [c for c, limit in limits.items() if running.get(c, 0) < limit]
    if not open_classes:
        return None
    run = session.scalar(
        select(JobStageRun)
        .where(
            JobStageRun.state.in_(("queued", "retry_wait")),
            JobStageRun.run_after <= func.now(),
            JobStageRun.job_class.in_(open_classes),
        )
        .order_by(JobStageRun.run_after, JobStageRun.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if run is None:
        return None
    run.state = "running"
    run.attempts += 1
    run.started_at = utcnow()
    run.locked_by = worker_id
    session.flush()
    return run
