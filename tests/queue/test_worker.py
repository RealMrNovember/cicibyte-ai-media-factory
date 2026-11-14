from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from mediafactory.db.base import utcnow
from mediafactory.db.models import JobStageRun, ProductionJob
from mediafactory.queue import worker as worker_mod
from mediafactory.queue.jobs import cancel_job, create_job, enqueue_stage, retry_failed
from mediafactory.queue.registry import StageOutcome
from mediafactory.queue.worker import process_one, run_worker

LIMITS = {"llm": 1, "render": 1, "tts": 1, "stt": 1, "io": 4}


def _job_with_stage(factory, stage, job_class="io", max_attempts=3):
    with factory() as s:
        job = create_job(s, status="discovered")
        run = enqueue_stage(s, job.id, stage, job_class, max_attempts=max_attempts)
        s.commit()
        return job.id, run.id


def _runs(factory, job_id):
    with factory() as s:
        return s.scalars(select(JobStageRun).where(JobStageRun.job_id == job_id).order_by(JobStageRun.id)).all()


def _job(factory, job_id):
    with factory() as s:
        return s.get(ProductionJob, job_id)


def test_success_advances_status_and_enqueues_next(factory, registry):
    @registry.stage_handler("normalize", "io")
    def normalize(ctx):
        ctx.log("normalized ok")
        return StageOutcome(next_status="normalized", outputs={"chars": 10}, next_stage=("classify", "llm"))

    job_id, run_id = _job_with_stage(factory, "normalize")
    assert process_one(factory, worker_id="w", limits=LIMITS) is True
    runs = _runs(factory, job_id)
    assert runs[0].state == "succeeded" and runs[0].outputs == {"chars": 10} and "normalized ok" in runs[0].log
    assert runs[1].stage == "classify" and runs[1].job_class == "llm" and runs[1].state == "queued"
    assert _job(factory, job_id).status == "normalized"


def test_failure_goes_retry_wait_with_backoff(factory, registry):
    @registry.stage_handler("boom", "io")
    def boom(ctx):
        raise RuntimeError("api_key=sk-leak exploded")

    job_id, _ = _job_with_stage(factory, "boom")
    before = utcnow()
    process_one(factory, worker_id="w", limits=LIMITS)
    (run,) = _runs(factory, job_id)
    assert run.state == "retry_wait" and run.attempts == 1
    assert run.run_after >= before + timedelta(seconds=29)
    assert "sk-leak" not in run.error
    assert _job(factory, job_id).status == "retry_wait"


def test_failure_after_max_attempts_marks_job_failed(factory, registry):
    @registry.stage_handler("boom", "io")
    def boom(ctx):
        raise RuntimeError("nope")

    job_id, _ = _job_with_stage(factory, "boom", max_attempts=1)
    process_one(factory, worker_id="w", limits=LIMITS)
    (run,) = _runs(factory, job_id)
    assert run.state == "failed"
    assert _job(factory, job_id).status == "failed"


def test_unknown_stage_fails_without_retry(factory, registry):
    job_id, _ = _job_with_stage(factory, "nobody-handles-this")
    process_one(factory, worker_id="w", limits=LIMITS)
    (run,) = _runs(factory, job_id)
    assert run.state == "failed" and "no handler" in run.error


def test_retry_failed_reruns_only_failed_stage(factory, registry):
    calls = {"a": 0, "b": 0}

    @registry.stage_handler("a", "io")
    def a(ctx):
        calls["a"] += 1
        return StageOutcome(next_status="normalized", next_stage=("b", "io"))

    @registry.stage_handler("b", "io")
    def b(ctx):
        calls["b"] += 1
        if calls["b"] == 1:
            raise RuntimeError("first time fails")
        return StageOutcome(next_status="classified")

    with factory() as s:
        job = create_job(s)
        enqueue_stage(s, job.id, "a", "io")
        s.commit()
        job_id = job.id
    with factory() as s:
        for r in s.scalars(select(JobStageRun)).all():
            r.max_attempts = 1
        s.commit()
    process_one(factory, worker_id="w", limits=LIMITS)  # a ok
    with factory() as s:
        s.scalar(select(JobStageRun).where(JobStageRun.stage == "b")).max_attempts = 1
        s.commit()
    process_one(factory, worker_id="w", limits=LIMITS)  # b fails
    assert _job(factory, job_id).status == "failed"
    with factory() as s:
        retry_failed(s, job_id)
        s.commit()
    process_one(factory, worker_id="w", limits=LIMITS)  # b ok
    assert calls == {"a": 1, "b": 2}
    assert _job(factory, job_id).status == "classified"


def test_cancel_marks_queued_cancelled(factory, registry):
    job_id, run_id = _job_with_stage(factory, "x")
    with factory() as s:
        cancel_job(s, job_id)
        s.commit()
    (run,) = _runs(factory, job_id)
    assert run.state == "cancelled"
    assert process_one(factory, worker_id="w", limits=LIMITS) is False


def test_cancel_while_running_does_not_advance(factory, registry):
    @registry.stage_handler("slow", "io")
    def slow(ctx):
        with factory() as s:
            cancel_job(s, ctx.job.id)
            s.commit()
        assert ctx.is_cancelled()
        return StageOutcome(next_status="normalized", next_stage=("next", "io"))

    job_id, _ = _job_with_stage(factory, "slow")
    process_one(factory, worker_id="w", limits=LIMITS)
    runs = _runs(factory, job_id)
    assert [r.stage for r in runs] == ["slow"] and runs[0].state == "cancelled"
    assert _job(factory, job_id).status == "failed"


def test_worker_survives_db_outage(factory, registry, monkeypatch):
    calls = {"n": 0}
    stop = {"flag": False}
    sleeps = []

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))
        stop["flag"] = True
        return False

    monkeypatch.setattr(worker_mod, "process_one", flaky)
    run_worker(factory, worker_id="w", limits=LIMITS, should_stop=lambda: stop["flag"], sleep=sleeps.append)
    assert calls["n"] == 2
    assert 5 in sleeps


def test_log_is_visible_while_the_stage_runs(factory, registry, monkeypatch):
    import time as _time

    monkeypatch.setattr(worker_mod, "LOG_FLUSH_S", 0.05)
    seen = {}

    @registry.stage_handler("slow", "io")
    def slow(ctx):
        ctx.log("[1/4] script")
        _time.sleep(0.4)
        with factory() as other:  # another connection, like the panel
            seen["mid"] = other.get(JobStageRun, ctx.run.id).log
        ctx.log("[2/4] voice")
        return StageOutcome(next_status="done")

    job_id, _ = _job_with_stage(factory, "slow")
    process_one(factory, worker_id="w", limits=LIMITS)
    assert "[1/4] script" in (seen["mid"] or "")
    (run,) = _runs(factory, job_id)
    assert run.log.count("[1/4] script") == 1 and "[2/4] voice" in run.log  # no duplicates after the final write
