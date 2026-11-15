from sqlalchemy import select

from mediafactory.concepts import keep_stock, stock
from mediafactory.db.models import Concept, JobStageRun, ProductionJob, Schedule
from mediafactory.instagram import publish as igp
from mediafactory.schedule.runner import run_due
from tests.test_schedules_youtube import NOW, _connect, _factory, _item, _ready_job

H = {"X-MF-Client": "1"}


def _concept(db, **kw):
    c = Concept(name=kw.pop("name", "Night Tales TR"), language="tr", topic="random", seconds=40,
                style={"font": "bebas"}, voice={"tr": "tr_TR-dfki-medium", "speed": 1.1}, music={"track": "none"},
                background="random", **{"platforms": ["youtube"], "privacy": "unlisted", **kw})  # fmt: skip
    db.add(c)
    db.flush()
    return c


def _stories(db, n, language="tr"):
    items = [_item(db, f"c{i}") for i in range(n)]
    for it in items:
        it.language = language
    db.flush()
    return items


def test_api_creates_lists_and_validates(client, db):
    body = {"name": "Gece Hikâyeleri", "language": "tr", "seconds": 45, "ready_buffer": 3, "platforms": ["youtube", "instagram"]}
    r = client.post("/api/concepts", json=body, headers=H)
    assert r.status_code == 201 and r.json()["ready_buffer"] == 3 and r.json()["stock"] == 0
    assert client.post("/api/concepts", json=body, headers=H).status_code == 409  # same name
    assert client.post("/api/concepts", json={**body, "name": "x", "youtube_channel_id": 999}, headers=H).status_code == 422
    assert client.post("/api/concepts", json={**body, "name": "y", "ready_buffer": 99}, headers=H).status_code == 422
    items = client.get("/api/concepts", headers=H).json()["items"]
    assert [c["name"] for c in items] == ["Gece Hikâyeleri"] and items[0]["voice"]["speed"] == 1.0


def test_produce_now_uses_the_concepts_recipe(client, db):
    c = _concept(db)
    _stories(db, 1)
    r = client.post(f"/api/concepts/{c.id}/produce", headers=H)
    assert r.status_code == 200
    job = db.get(ProductionJob, r.json()["job_id"])
    make = db.scalar(select(JobStageRun).where(JobStageRun.job_id == job.id)).inputs
    assert job.language == "tr" and job.payload["concept_id"] == c.id
    assert make["seconds"] == 40 and make["voice"]["tr"] == "tr_TR-dfki-medium" and make["style"]["font"] == "bebas"


def test_produce_without_stories_is_a_clear_409(client, db):
    c = _concept(db)
    assert client.post(f"/api/concepts/{c.id}/produce", headers=H).status_code == 409


def test_stock_keeper_tops_up_two_at_a_time_until_the_target(db):
    c = _concept(db, ready_buffer=3, auto_approve=True)
    _stories(db, 5)
    keep_stock(db)
    assert stock(db, c) == 2  # at most two new videos per run
    keep_stock(db)
    assert stock(db, c) == 3
    keep_stock(db)
    assert stock(db, c) == 3  # full: nothing more
    jobs = db.scalars(select(ProductionJob).where(ProductionJob.payload["concept_id"].as_integer() == c.id)).all()
    assert all(j.payload["auto_approve"] for j in jobs)


def test_published_videos_leave_the_stock(db):
    c = _concept(db, ready_buffer=1)
    _stories(db, 2)
    keep_stock(db)
    job = db.scalar(select(ProductionJob).where(ProductionJob.payload["concept_id"].as_integer() == c.id))
    job.status = "published"
    db.flush()
    keep_stock(db)
    assert stock(db, c) == 1 and db.scalar(select(ProductionJob).where(ProductionJob.id != job.id)) is not None


def test_disabled_or_targetless_concepts_are_left_alone(db):
    _concept(db, name="off", ready_buffer=2, enabled=False)
    _concept(db, name="no target", ready_buffer=0)
    _stories(db, 3)
    assert keep_stock(db) == [] and db.scalar(select(ProductionJob)) is None


def test_stories_in_other_languages_are_not_used(db):
    c = _concept(db, ready_buffer=2)
    _stories(db, 2, language="en")
    keep_stock(db)
    assert stock(db, c) == 0


def test_autopilot_following_a_concept_publishes_to_its_channel(db):
    chan = _connect(db)
    c = _concept(db, youtube_channel_id=chan.id, platforms=["youtube", "instagram"])
    _stories(db, 1)
    db.add(Schedule(name="auto", kind="autopilot", enabled=True, times=["09:00"], weekdays=list(range(7)), timezone="UTC",
                    params={"concept_id": c.id, "publish": True}, next_run_at=NOW))  # fmt: skip
    db.flush()
    run_due(_factory(db), now=NOW)
    job = db.scalar(select(ProductionJob))
    assert job.payload["concept_id"] == c.id and job.payload["auto_approve"] is True
    assert job.payload["auto_publish"] == {"privacy": "unlisted", "platforms": ["youtube", "instagram"], "channel_id": chan.id}


def test_publish_schedule_following_a_concept_only_sends_its_videos(db, tmp_path):
    chan = _connect(db)
    igp.save_account(db, "IGtoken-" + "x" * 30, info={"user_id": "1", "username": "u", "account_type": "BUSINESS"})
    c = _concept(db, youtube_channel_id=chan.id, platforms=["instagram"])
    mine = _ready_job(db, tmp_path)
    mine.payload = {**mine.payload, "concept_id": c.id}
    other = ProductionJob(status="approved", language="en", payload=dict(mine.payload, concept_id=None))
    db.add(other)
    db.add(Schedule(name="pub", kind="publish", enabled=True, times=["18:00"], weekdays=list(range(7)), timezone="UTC",
                    params={"count": 5, "concept_id": c.id}, next_run_at=NOW))  # fmt: skip
    db.flush()
    run_due(_factory(db), now=NOW)
    assert mine.payload["instagram"]["state"] == "queued" and "youtube" not in mine.payload
    assert "instagram" not in other.payload


def test_deleting_a_channel_keeps_the_concept(db):
    chan = _connect(db)
    c = _concept(db, youtube_channel_id=chan.id)
    db.delete(chan)
    db.flush()
    db.expire(c)
    assert db.get(Concept, c.id).youtube_channel_id is None
