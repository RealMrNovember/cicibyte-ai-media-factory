import io
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from mediafactory.db.models import JobStageRun, ProductionJob, Schedule, SourceConnector, SourceItem
from mediafactory.pipeline import backgrounds as bg
from mediafactory.schedule.runner import pick_story, run_due

H = {"X-MF-Client": "1"}


def _stories(db):
    horror = SourceConnector(name="r/nosleep", adapter="reddit_rss", params={"subreddit": "nosleep"})
    science = SourceConnector(name="Evrim", adapter="rss", params={"url": "https://evrimagaci.org/rss.xml"})
    db.add_all([horror, science])
    db.flush()
    for sid, lang, key in ((horror.id, "en", "h1"), (science.id, "tr", "s1"), (science.id, "tr", "s2")):
        db.add(SourceItem(source_id=sid, source_type="rss", title=key, raw_text="x", normalized_text="y" * 400,
                          content_hash=key, language=lang))  # fmt: skip
    db.flush()


def test_pick_story_by_topic_and_language(db):
    _stories(db)
    assert pick_story(db, topic="horror").title == "h1"
    assert pick_story(db, topic="science", language="tr").title in ("s1", "s2")
    assert pick_story(db, topic="horror", language="tr") is None
    picks = {pick_story(db, rng=random.Random(i)).title for i in range(20)}
    assert picks == {"h1", "s1", "s2"}  # random topic covers everything over time


def test_autopilot_schedule_makes_a_publishable_job(db):
    _stories(db)
    now = datetime(2026, 11, 16, 9, 0, tzinfo=timezone.utc)
    sch = Schedule(name="auto", kind="autopilot", enabled=True, times=[], weekdays=list(range(7)), timezone="UTC",
                   interval_min=120, params={"topic": "science", "language": "tr", "privacy": "public"},
                   next_run_at=now)  # fmt: skip
    db.add(sch)
    db.flush()
    import contextlib

    assert run_due(lambda: contextlib.nullcontext(db), now=now) == 1
    job = db.scalar(select(ProductionJob))
    assert job.language == "tr" and job.payload["auto_approve"] and job.payload["auto_publish"] == {"privacy": "public"}
    assert sch.next_run_at == now + timedelta(hours=2)


def test_render_then_auto_publish_or_hold(db, monkeypatch, tmp_path):
    import mediafactory.pipeline.make as make_mod
    from mediafactory.pipeline import handlers
    from mediafactory.queue.registry import StageContext
    from tests.test_schedules_youtube import _connect

    _connect(db)
    video = tmp_path / "short.mp4"
    video.write_bytes(b"v")
    for qc_ok, expected in ((True, "uploading"), (False, "needs_review")):
        monkeypatch.setattr(make_mod, "make_short",
                            lambda s, i, **kw: {"video": str(video), "folder": str(tmp_path), "qc": {"passed": qc_ok, "checks": []}})  # fmt: skip
        job = ProductionJob(status="discovered", language="en", payload={"auto_approve": True, "auto_publish": {"privacy": "unlisted"}})
        db.add(job)
        db.flush()
        run = JobStageRun(job_id=job.id, stage="make_short", job_class="render", inputs={"item_id": 1})
        db.add(run)
        db.flush()
        out = handlers.make_short_stage(StageContext(db, job, run, lambda m: None, lambda: False))
        assert out.next_status == expected
    uploads = db.scalars(select(JobStageRun).where(JobStageRun.stage == "upload_youtube")).all()
    assert len(uploads) == 1 and uploads[0].inputs["privacy"] == "unlisted"


def test_schedule_api_accepts_interval_autopilot(client):
    body = {"name": "Every 2h", "kind": "autopilot", "interval_min": 120, "window": ["9:00", "23:00"],
            "timezone": "Europe/Istanbul", "params": {"topic": "random", "language": "tr"}}  # fmt: skip
    r = client.post("/api/schedules", json=body, headers=H)
    assert r.status_code == 201, r.text
    assert r.json()["interval_min"] == 120 and r.json()["window"] == ["09:00", "23:00"] and r.json()["next_run_at"]
    bad = {**body, "interval_min": None, "times": []}
    assert client.post("/api/schedules", json=bad, headers=H).status_code == 422


def test_clip_tags_steer_random_background(tmp_path):
    for name, tags in (("horror.mp4", ["horror"]), ("space.mp4", ["science", "curious"]), ("plain.mp4", [])):
        bg.add_clip(tmp_path, name, io.BytesIO(b"x"), licence="", tags=tags)
    rng = random.Random(3)
    assert {bg.pick_background(tmp_path, rng=rng, category="science").name for _ in range(6)} == {"space.mp4"}
    assert bg.pick_background(tmp_path, rng=rng, category="history") is not None  # nothing tagged: any clip
    assert bg.set_tags(tmp_path, "plain.mp4", ["history", "nonsense"]) == ["history"]
    assert bg.info(tmp_path / "media/backgrounds/plain.mp4")["tags"] == ["history"]


def test_clip_tags_api(client, tmp_path, monkeypatch):
    from mediafactory.api.routes import backgrounds as route

    monkeypatch.setattr(route, "_data", lambda: tmp_path)
    monkeypatch.setattr(bg, "thumbnail", lambda clip: clip)
    r = client.post("/api/backgrounds", headers=H, data={"tags": "horror,drama"},
                    files={"file": ("c.mp4", io.BytesIO(b"x"), "video/mp4")})  # fmt: skip
    assert r.json()["tags"] == ["drama", "horror"]
    assert client.put("/api/backgrounds/c.mp4/tags", json={"tags": ["tech"]}, headers=H).json()["tags"] == ["tech"]
