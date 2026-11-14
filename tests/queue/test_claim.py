import threading

from mediafactory.queue.claim import claim_next
from mediafactory.queue.jobs import create_job, enqueue_stage

LIMITS = {"llm": 1, "render": 1, "tts": 1, "stt": 1, "io": 100}


def _seed(factory, n, job_class="io"):
    with factory() as s:
        job = create_job(s)
        ids = [enqueue_stage(s, job.id, f"stage{i}", job_class).id for i in range(n)]
        s.commit()
    return ids


def test_two_workers_never_claim_same_run(factory):
    ids = _seed(factory, 20)
    claimed: list[int] = []
    lock = threading.Lock()

    def worker(name):
        while True:
            with factory() as s:
                run = claim_next(s, worker_id=name, limits=LIMITS)
                s.commit()
                if run is None:
                    return
                with lock:
                    claimed.append(run.id)

    threads = [threading.Thread(target=worker, args=(f"w{i}",)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(claimed) == sorted(ids)


def test_class_limit_respected(factory):
    _seed(factory, 2, job_class="render")
    with factory() as s:
        first = claim_next(s, worker_id="a", limits=LIMITS)
        s.commit()
    assert first is not None and first.state == "running"
    with factory() as s:
        assert claim_next(s, worker_id="b", limits=LIMITS) is None


def test_claim_uses_application_clock_not_db_clock(factory, monkeypatch):
    """run_after is written with the app clock; comparing it to the DB's now() breaks under clock skew."""
    from datetime import timedelta

    from mediafactory.db.base import utcnow
    from mediafactory.db.models import JobStageRun
    from mediafactory.queue import claim as claim_mod

    (rid,) = _seed(factory, 1)
    future = utcnow() + timedelta(hours=1)  # ahead of the DB clock
    with factory() as s:
        s.get(JobStageRun, rid).run_after = future
        s.commit()
    monkeypatch.setattr(claim_mod, "utcnow", lambda: future + timedelta(seconds=1))
    with factory() as s:
        run = claim_next(s, worker_id="a", limits=LIMITS)
        s.commit()
    assert run is not None and run.id == rid


def test_future_run_after_not_claimed(factory):
    from datetime import timedelta

    from mediafactory.db.base import utcnow
    from mediafactory.db.models import JobStageRun

    (rid,) = _seed(factory, 1)
    with factory() as s:
        s.get(JobStageRun, rid).run_after = utcnow() + timedelta(minutes=5)
        s.commit()
    with factory() as s:
        assert claim_next(s, worker_id="a", limits=LIMITS) is None
