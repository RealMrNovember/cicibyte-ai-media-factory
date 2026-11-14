import logging
import os
import socket
import threading
import time
from collections.abc import Callable
from datetime import timedelta

from sqlalchemy import update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from mediafactory.core.redact import redact
from mediafactory.db.base import utcnow
from mediafactory.db.models import JobStageRun, ProductionJob
from mediafactory.queue.claim import claim_next
from mediafactory.queue.jobs import enqueue_stage
from mediafactory.queue.registry import StageContext, get_handler

log = logging.getLogger(__name__)

DEFAULT_LIMITS = {"llm": 1, "render": 1, "tts": 1, "stt": 1, "io": 4}
BACKOFF_BASE_S = 30
OUTAGE_SLEEP_S = 5
IDLE_SLEEP_S = 2
HEARTBEAT_S = 30

SessionFactory = Callable[[], Session]


def default_worker_id() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


def _state(factory: SessionFactory, run_id: int) -> str | None:
    with factory() as s:
        run = s.get(JobStageRun, run_id)
        return run.state if run else None


def _fail(s: Session, run: JobStageRun, job: ProductionJob, message: str, *, retry: bool) -> None:
    run.error = redact(message)[:4000]
    run.finished_at = utcnow()
    if retry and run.attempts < run.max_attempts:
        run.state = "retry_wait"
        run.run_after = utcnow() + timedelta(seconds=BACKOFF_BASE_S * 2 ** (run.attempts - 1))
        job.status = "retry_wait"
    else:
        run.state = "failed"
        job.status = "failed"


def _heartbeat(factory: SessionFactory, run_id: int, interval_s: float, stop: threading.Event) -> None:
    while not stop.wait(interval_s):
        try:
            with factory() as s:
                s.execute(
                    update(JobStageRun)
                    .where(JobStageRun.id == run_id, JobStageRun.state == "running")
                    .values(heartbeat_at=utcnow())
                )
                s.commit()
        except OperationalError:
            log.warning("heartbeat for run %s failed (database unavailable)", run_id)


def process_one(
    factory: SessionFactory, *, worker_id: str, limits: dict[str, int], heartbeat_s: float = HEARTBEAT_S
) -> bool:
    """Claim and run at most one stage. Returns False when nothing was claimable."""
    with factory() as s:
        run = claim_next(s, worker_id=worker_id, limits=limits)
        s.commit()
        if run is None:
            return False
        run_id, job_id, stage = run.id, run.job_id, run.stage

    lines: list[str] = []
    handler = get_handler(stage)
    stop = threading.Event()
    beat = threading.Thread(target=_heartbeat, args=(factory, run_id, heartbeat_s, stop), daemon=True)
    beat.start()
    try:
        with factory() as work:
            job = work.get(ProductionJob, job_id)
            run = work.get(JobStageRun, run_id)
            ctx = StageContext(
                session=work, job=job, run=run,
                log=lambda m: lines.append(redact(m)),
                is_cancelled=lambda: _state(factory, run_id) == "cancelled",
            )  # fmt: skip
            try:
                if handler is None:
                    raise LookupError(f"no handler registered for stage '{stage}'")
                outcome = handler(ctx)
                if ctx.is_cancelled():
                    work.rollback()  # cancelled meanwhile: discard the handler's writes
                else:
                    work.commit()
                error: str | None = None
            except Exception as exc:  # handler failures are recorded, never crash the worker
                work.rollback()
                outcome, error = None, f"{type(exc).__name__}: {exc}"
                log.warning("stage %s of job %s failed: %s", stage, job_id, redact(error))
    finally:
        stop.set()
        beat.join(timeout=5)

    with factory() as s:
        run = s.get(JobStageRun, run_id, with_for_update=True)
        job = s.get(ProductionJob, job_id)
        run.log = (run.log or "") + "".join(f"{line}\n" for line in lines)
        if run.state != "running":
            pass  # cancelled (or reclaimed) while running: keep that state, do not advance
        elif outcome is not None:
            run.state = "succeeded"
            run.finished_at = utcnow()
            run.outputs = outcome.outputs
            job.status = outcome.next_status
            if outcome.next_stage:
                enqueue_stage(s, job_id, *outcome.next_stage)
        else:
            _fail(s, run, job, error or "unknown error", retry=handler is not None)
        s.commit()
    return True


def run_worker(
    factory: SessionFactory,
    *,
    worker_id: str | None = None,
    limits: dict[str, int] | None = None,
    should_stop: Callable[[], bool] = lambda: False,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    worker_id = worker_id or default_worker_id()
    limits = limits or DEFAULT_LIMITS
    log.info("worker %s started with limits %s", worker_id, limits)
    while not should_stop():
        try:
            busy = process_one(factory, worker_id=worker_id, limits=limits)
        except OperationalError as exc:
            log.warning("database unavailable (%s); retrying in %ss", type(exc).__name__, OUTAGE_SLEEP_S)
            sleep(OUTAGE_SLEEP_S)
            continue
        if not busy:
            sleep(IDLE_SLEEP_S)
