from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from sqlalchemy import select

from mediafactory.db.models import JobStageRun, Schedule
from mediafactory.instagram import client as ig
from mediafactory.instagram import publish as igp
from mediafactory.instagram.client import InstagramError
from mediafactory.publishing import publish_job
from mediafactory.queue.registry import StageContext
from mediafactory.schedule.runner import run_due
from mediafactory.youtube import oauth
from mediafactory.youtube.publish import upload_stage as youtube_stage
from mediafactory.youtube.upload import UPLOAD_URL
from tests.test_schedules_youtube import NOW, _connect, _factory, _ready_job

H = {"X-MF-Client": "1"}
INFO = {"user_id": "1784", "username": "cici", "account_type": "BUSINESS"}


def _connect_ig(db):
    return igp.save_account(db, "IGtoken-" + "x" * 30, info=INFO)


def _ctx(db, job, run):
    return StageContext(db, job, run, lambda m: None, lambda: False)


def _runs(db, job):
    return db.scalars(select(JobStageRun).where(JobStageRun.job_id == job.id).order_by(JobStageRun.id)).all()


def test_token_is_stored_encrypted_and_never_returned(client, db, monkeypatch):
    monkeypatch.setattr(ig, "account_info", lambda token, **kw: INFO)
    r = client.put("/api/instagram/token", json={"access_token": "IGtoken-" + "s" * 30}, headers=H)
    assert r.status_code == 200 and r.json()["account"]["username"] == "cici"
    stored = igp.get_account(db)
    assert "IGtoken" not in str(stored) and stored["token_enc"]
    assert "token" not in str(client.get("/api/instagram", headers=H).json())


def test_personal_account_token_is_rejected_with_explanation(client, monkeypatch):
    def personal(token, **kw):
        raise InstagramError("this is a personal Instagram account: only professional accounts can publish")

    monkeypatch.setattr(ig, "account_info", personal)
    r = client.put("/api/instagram/token", json={"access_token": "IGtoken-" + "s" * 30}, headers=H)
    assert r.status_code == 422 and "personal" in r.json()["detail"]


def test_instagram_only_publish_queues_the_reel(db, tmp_path):
    _connect_ig(db)
    job = _ready_job(db, tmp_path)
    publish_job(db, job, platforms=["instagram"])
    assert job.status == "uploading" and job.payload["instagram"]["state"] == "queued"
    assert [r.stage for r in _runs(db, job)] == ["upload_instagram"]


def test_scheduled_instagram_waits_for_its_time(db, tmp_path):
    _connect_ig(db)
    job = _ready_job(db, tmp_path)
    at = datetime.now(UTC) + timedelta(hours=5)
    publish_job(db, job, platforms=["instagram"], publish_at=at)
    assert job.status == "scheduled" and abs(_runs(db, job)[0].run_after - at) < timedelta(seconds=1)


def test_both_platforms_run_one_after_the_other(db, tmp_path):
    chan = _connect(db)
    _connect_ig(db)
    job = _ready_job(db, tmp_path)
    publish_job(db, job, platforms=["youtube", "instagram"])
    runs = _runs(db, job)
    assert [r.stage for r in runs] == ["upload_youtube"]  # Instagram waits for YouTube
    with respx.mock:
        respx.post(oauth.TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "at"}))
        respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, headers={"Location": "https://upload.example/s"}))
        respx.put("https://upload.example/s").mock(return_value=httpx.Response(200, json={"id": "vid1"}))
        runs[0].inputs = {**runs[0].inputs, "channel_db_id": chan.id}
        outcome = youtube_stage(_ctx(db, job, runs[0]))
    assert outcome.next_stage == ("upload_instagram", "io")


def test_upload_stage_publishes_and_marks_the_job(db, tmp_path, monkeypatch):
    _connect_ig(db)
    job = _ready_job(db, tmp_path)
    publish_job(db, job, platforms=["instagram"])
    seen = {}

    def fake_publish(token, user_id, video, caption, **kw):
        seen.update(token=token, user_id=user_id, caption=caption)
        return "M1", "https://www.instagram.com/reel/x/"

    monkeypatch.setattr(ig, "publish_reel", fake_publish)
    outcome = igp.upload_stage(_ctx(db, job, _runs(db, job)[0]))
    assert outcome.next_status == "published"
    assert job.payload["instagram"]["state"] == "published" and job.payload["instagram"]["url"].endswith("/reel/x/")
    assert seen["token"].startswith("IGtoken-") and seen["user_id"] == "1784"
    assert seen["caption"].startswith("Eleven Gallons") and "#scarystory" in seen["caption"]


def test_instagram_failure_does_not_undo_a_youtube_publish(db, tmp_path, monkeypatch):
    _connect_ig(db)
    job = _ready_job(db, tmp_path, status="published")
    job.payload = {**job.payload, "youtube": {"state": "published", "id": "v", "url": "u"}}
    publish_job(db, job, platforms=["instagram"])

    def broken(*a, **kw):
        raise InstagramError("Instagram could not process the video: bad codec")

    monkeypatch.setattr(ig, "publish_reel", broken)
    outcome = igp.upload_stage(_ctx(db, job, _runs(db, job)[0]))
    assert outcome.next_status == "published"
    assert job.payload["instagram"]["state"] == "failed" and "bad codec" in job.payload["instagram"]["error"]


def test_instagram_only_failure_returns_to_review_and_can_be_retried(db, tmp_path, monkeypatch):
    _connect_ig(db)
    job = _ready_job(db, tmp_path, status="needs_review")
    publish_job(db, job, platforms=["instagram"])
    monkeypatch.setattr(ig, "publish_reel", lambda *a, **kw: (_ for _ in ()).throw(InstagramError("nope")))
    assert igp.upload_stage(_ctx(db, job, _runs(db, job)[0])).next_status == "needs_review"
    job.status = "needs_review"
    publish_job(db, job, platforms=["instagram"])  # allowed again after a failure
    assert job.payload["instagram"]["state"] == "queued"


def test_transient_errors_are_retried_later(db, tmp_path, monkeypatch):
    _connect_ig(db)
    job = _ready_job(db, tmp_path)
    publish_job(db, job, platforms=["instagram"])
    monkeypatch.setattr(ig, "publish_reel", lambda *a, **kw: (_ for _ in ()).throw(InstagramError("busy", transient=True)))
    igp.upload_stage(_ctx(db, job, _runs(db, job)[0]))
    runs = _runs(db, job)
    assert len(runs) == 2 and runs[1].inputs["attempt"] == 2 and runs[1].run_after > datetime.now(UTC)
    assert job.payload["instagram"]["state"] == "queued"


def test_cannot_publish_twice_or_without_account(db, tmp_path):
    job = _ready_job(db, tmp_path)
    with pytest.raises(ValueError, match="Instagram"):
        publish_job(db, job, platforms=["instagram"])
    _connect_ig(db)
    publish_job(db, job, platforms=["instagram"])
    with pytest.raises(ValueError, match="already"):
        publish_job(db, job, platforms=["instagram"])


def test_expired_token_is_refreshed_before_upload(db, monkeypatch):
    acc = _connect_ig(db)
    acc_row = {**acc, "refreshed_at": (datetime.now(UTC) - timedelta(days=9)).isoformat()}
    igp.save_account(db, "IGtoken-" + "x" * 30, info=INFO)
    from mediafactory.db.models import SystemSetting

    db.get(SystemSetting, igp.ACCOUNT_KEY).value = acc_row
    monkeypatch.setattr(ig, "refresh_token", lambda t, **kw: ("IGfresh-" + "y" * 30, datetime.now(UTC) + timedelta(days=60)))
    token, _ = igp.access_token(db)
    assert token.startswith("IGfresh-") and not ig.refresh_due(igp.get_account(db))


def test_publish_api_takes_platforms(client, db, tmp_path):
    _connect_ig(db)
    job = _ready_job(db, tmp_path)
    r = client.post(f"/api/jobs/{job.id}/publish", json={"platforms": ["instagram"]}, headers=H)
    assert r.status_code == 200 and r.json()["instagram"]["state"] == "queued"
    assert client.post(f"/api/jobs/{job.id}/publish", json={"platforms": []}, headers=H).status_code == 422


def test_manual_pack_and_mark_shared(client, db, tmp_path):
    job = _ready_job(db, tmp_path)
    pack = client.get(f"/api/jobs/{job.id}/instagram-pack", headers=H).json()
    assert pack["caption"].startswith("Eleven Gallons") and pack["video"] == f"/api/jobs/{job.id}/video"
    r = client.post(f"/api/jobs/{job.id}/instagram-manual", headers=H)
    assert r.json()["instagram"]["state"] == "manual"


def test_publish_schedule_can_target_instagram(db, tmp_path):
    _connect_ig(db)
    job = _ready_job(db, tmp_path)
    db.add(Schedule(name="ig", kind="publish", enabled=True, times=["18:00"], weekdays=list(range(7)),
                    timezone="UTC", params={"count": 1, "platforms": ["instagram"]}, next_run_at=NOW))  # fmt: skip
    db.flush()
    run_due(_factory(db), now=NOW)
    assert job.payload["instagram"]["state"] == "queued"
