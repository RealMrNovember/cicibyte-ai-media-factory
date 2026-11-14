from sqlalchemy import select, update
from sqlalchemy.orm import Session

from mediafactory.db.base import utcnow
from mediafactory.db.models import JobStageRun, ProductionJob
from mediafactory.db.models.jobs import JOB_CLASSES

CANCELLED_ERROR = "cancelled by user"


def create_job(session: Session, *, status: str = "discovered", **fields) -> ProductionJob:
    job = ProductionJob(status=status, payload=fields.pop("payload", {}), **fields)
    session.add(job)
    session.flush()
    return job


def enqueue_stage(
    session: Session, job_id: int, stage: str, job_class: str, inputs: dict | None = None, max_attempts: int = 3
) -> JobStageRun:
    if job_class not in JOB_CLASSES:
        raise ValueError(f"unknown job class {job_class!r}")
    run = JobStageRun(
        job_id=job_id, stage=stage, job_class=job_class, state="queued", attempts=0,
        max_attempts=max_attempts, run_after=utcnow(), inputs=inputs or {}, outputs={}, log="",
    )  # fmt: skip
    session.add(run)
    session.flush()
    return run


def retry_failed(session: Session, job_id: int) -> JobStageRun | None:
    """Re-queue only the last failed or cancelled stage; earlier successful stages are not re-run."""
    run = session.scalar(
        select(JobStageRun)
        .where(JobStageRun.job_id == job_id, JobStageRun.state.in_(("failed", "cancelled")))
        .order_by(JobStageRun.id.desc())
        .limit(1)
    )
    if run is None:
        return None
    job = session.get(ProductionJob, job_id)
    new = enqueue_stage(session, job_id, run.stage, run.job_class, inputs=run.inputs, max_attempts=run.max_attempts)
    job.status = "retry_wait"
    return new


def cancel_job(session: Session, job_id: int) -> None:
    session.execute(
        update(JobStageRun)
        .where(JobStageRun.job_id == job_id, JobStageRun.state.in_(("queued", "retry_wait", "running")))
        .values(state="cancelled", finished_at=utcnow(), error=CANCELLED_ERROR)
    )
    job = session.get(ProductionJob, job_id)
    if job is not None:
        job.status = "failed"
        job.payload = {**(job.payload or {}), "cancelled": True}
