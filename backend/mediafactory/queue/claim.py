from datetime import timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from mediafactory.db.base import utcnow
from mediafactory.db.models import JobStageRun, ProductionJob

# Serialises claims across workers so per-class running counts are exact; claims are short.
_CLAIM_LOCK_KEY = 7_340_001
# A running stage whose worker has not sent a heartbeat for this long is considered lost (killed/crashed).
STALE_AFTER = timedelta(minutes=5)
LOST_ERROR = "worker lost (no heartbeat); stage re-queued"


def reclaim_stale(session: Session, *, stale_after: timedelta = STALE_AFTER) -> int:
    cutoff = utcnow() - stale_after
    stale = session.scalars(
        select(JobStageRun)
        .where(JobStageRun.state == "running", func.coalesce(JobStageRun.heartbeat_at, JobStageRun.started_at) < cutoff)
        .with_for_update(skip_locked=True)
    ).all()
    for run in stale:
        job = session.get(ProductionJob, run.job_id)
        run.error, run.finished_at = LOST_ERROR, utcnow()
        if run.attempts < run.max_attempts:
            run.state, run.run_after = "retry_wait", cutoff  # in the past: claimable at once
            job.status = "retry_wait"
        else:
            run.state = "failed"
            job.status = "failed"
    session.flush()
    return len(stale)


def claim_next(session: Session, *, worker_id: str, limits: dict[str, int]) -> JobStageRun | None:
    session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _CLAIM_LOCK_KEY})
    reclaim_stale(session)
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
            JobStageRun.run_after <= utcnow(),  # app clock: run_after is written with it too
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
    run.started_at = run.heartbeat_at = utcnow()
    run.locked_by = worker_id
    run.error = None
    session.flush()
    return run
