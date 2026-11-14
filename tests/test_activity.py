from datetime import timedelta

from mediafactory.db.base import utcnow
from mediafactory.db.models import JobStageRun, ProductionJob, Schedule, SystemSetting
from mediafactory.api.routes.activity import progress_from_log


def test_progress_from_log():
    assert progress_from_log("") == (0.0, None)
    assert progress_from_log("[1/4] script (en) from item 3\n") == (0.125, "script")
    assert progress_from_log("[1/4] script\n[2/4] voice (tr-chatterbox)\n") == (0.375, "voice")
    assert progress_from_log("[1/4] a\n[2/4] b\n[3/4] captions\n[4/4] render 1080x1920\n[+] cover image\n") == (0.95, "cover image")


def test_activity_shows_running_queue_schedules_and_worker(client, db):
    job = ProductionJob(status="rendering", language="tr", payload={"title": "Üçler Vakti"})
    waiting = ProductionJob(status="discovered", language="en", payload={"title": "Next one"})
    db.add_all([job, waiting])
    db.flush()
    db.add(JobStageRun(job_id=job.id, stage="make_short", job_class="render", state="running", locked_by="srv-1",
                       started_at=utcnow() - timedelta(seconds=90), log="[1/4] script\n[2/4] voice (tr-chatterbox)\n"))  # fmt: skip
    db.add(JobStageRun(job_id=waiting.id, stage="make_short", job_class="render", state="queued"))
    db.add(Schedule(name="Autopilot", kind="autopilot", enabled=True, times=[], weekdays=list(range(7)), timezone="UTC",
                    interval_min=120, params={}, next_run_at=utcnow() + timedelta(minutes=30)))  # fmt: skip
    db.add(SystemSetting(key="worker.heartbeat", value={"id": "srv-1", "at": utcnow().isoformat()}))
    db.flush()
    a = client.get("/api/activity").json()
    [run] = a["running"]
    assert run["job_id"] == job.id and run["title"] == "Üçler Vakti" and run["step"] == "voice"
    assert 0.3 < run["progress"] < 0.4 and run["elapsed_s"] >= 89 and "[2/4] voice" in run["log"]
    assert a["queued"][0]["title"] == "Next one" and a["counts"]["queued"] == 1
    assert a["schedules"][0]["name"] == "Autopilot" and a["schedules"][0]["next_run_at"]
    assert a["worker"]["alive"] is True
    assert "voice" in a["summary"]["en"] and "1" in a["summary"]["en"]


def test_activity_idle_summary(client, db):
    db.add(Schedule(name="Evening", kind="publish", enabled=True, times=["18:00"], weekdays=list(range(7)), timezone="UTC",
                    params={}, next_run_at=utcnow() + timedelta(hours=1)))  # fmt: skip
    db.flush()
    a = client.get("/api/activity").json()
    assert a["running"] == [] and a["worker"]["alive"] is False
    assert "Evening" in a["summary"]["en"] and "Evening" in a["summary"]["tr"]
