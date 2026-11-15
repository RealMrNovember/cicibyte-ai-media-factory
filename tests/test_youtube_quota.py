from datetime import datetime, timezone

import httpx
import pytest
import respx
from sqlalchemy import select

from mediafactory.db.models import JobStageRun, YouTubeChannel
from mediafactory.queue.registry import StageContext
from mediafactory.youtube import oauth, quota
from mediafactory.youtube.oauth import YouTubeError
from mediafactory.youtube.publish import upload_stage
from mediafactory.youtube.upload import CAPTIONS_URL, PLAYLIST_ITEMS_URL, THUMBNAIL_URL, UPLOAD_URL, playlist_id_from
from tests.test_schedules_youtube import _connect, _ready_job

H = {"X-MF-Client": "1"}


def _run(db, job, chan):
    run = JobStageRun(job_id=job.id, stage="upload_youtube", job_class="io", inputs={"privacy": "public", "channel_db_id": chan.id})
    db.add(run)
    db.flush()
    return run


def _mock_upload(vid="vid1"):
    respx.post(oauth.TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "at"}))
    respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, headers={"Location": "https://upload.example/s"}))
    respx.put("https://upload.example/s").mock(return_value=httpx.Response(200, json={"id": vid}))


def test_quota_day_follows_pacific_time():
    late_utc = datetime(2026, 11, 16, 7, 30, tzinfo=timezone.utc)  # 23:30 Pacific on the 15th
    assert quota.today(late_utc) == "2026-11-15"
    assert quota.next_reset(late_utc) == datetime(2026, 11, 16, 8, 5, tzinfo=timezone.utc)


def test_spending_counts_units_and_uploads_per_channel(db):
    chan = _connect(db)
    quota.spend(db, "upload", channel=chan)
    quota.spend(db, "captions")
    u = quota.usage(db)
    assert u["units"] == 2000 and u["uploads"] == {chan.channel_id: 1} and u["limit"] == 10_000


def test_usage_starts_fresh_on_a_new_day(db):
    chan = _connect(db)
    quota.spend(db, "upload", channel=chan, now=datetime(2026, 11, 14, 20, tzinfo=timezone.utc))
    assert quota.usage(db, now=datetime(2026, 11, 16, 20, tzinfo=timezone.utc))["units"] == 0


def test_daily_limit_and_quota_block_uploads(db):
    chan = _connect(db)
    chan.daily_limit = 2
    assert quota.blocked(db, chan) is None
    quota.spend(db, "upload", channel=chan)
    quota.spend(db, "upload", channel=chan)
    assert "daily upload limit" in quota.blocked(db, chan)
    chan.daily_limit = 0  # no own limit: only the API quota counts
    for _ in range(3):
        quota.spend(db, "upload", channel=chan)
    assert "quota" in quota.blocked(db, chan)  # 5 x 1600 + a full publish would pass 10,000


@respx.mock
def test_blocked_upload_waits_for_the_next_quota_day(db, tmp_path):
    chan = _connect(db)
    chan.daily_limit = 1
    quota.spend(db, "upload", channel=chan)
    job = _ready_job(db, tmp_path, status="uploading")
    outcome = upload_stage(StageContext(db, job, _run(db, job, chan), lambda m: None, lambda: False))
    assert outcome.next_status == "uploading" and job.payload["youtube"]["state"] == "waiting"
    runs = db.scalars(select(JobStageRun).where(JobStageRun.job_id == job.id).order_by(JobStageRun.id)).all()
    assert len(runs) == 2 and runs[1].run_after > datetime.now(timezone.utc)
    assert abs((runs[1].run_after - quota.next_reset()).total_seconds()) < 5


@respx.mock
def test_upload_adds_captions_and_playlist_and_counts_quota(db, tmp_path):
    chan = _connect(db)
    chan.playlist_id = "PLabcdefghij12"
    job = _ready_job(db, tmp_path, status="uploading")
    (tmp_path / "v" / "captions.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")
    _mock_upload()
    caps = respx.post(CAPTIONS_URL).mock(return_value=httpx.Response(200, json={"id": "c1"}))
    pl = respx.post(PLAYLIST_ITEMS_URL).mock(return_value=httpx.Response(200, json={"id": "p1"}))
    upload_stage(StageContext(db, job, _run(db, job, chan), lambda m: None, lambda: False))
    assert b'"videoId": "vid1"' in caps.calls[0].request.content and b"Hi" in caps.calls[0].request.content
    assert pl.calls[0].request.content and b"PLabcdefghij12" in pl.calls[0].request.content
    assert quota.usage(db)["units"] == 1600 + 400 + 50 and quota.usage(db)["uploads"][chan.channel_id] == 1


@respx.mock
def test_refused_extras_do_not_fail_the_upload(db, tmp_path):
    chan = _connect(db)
    chan.playlist_id = "PLabcdefghij12"
    job = _ready_job(db, tmp_path, status="uploading")
    (tmp_path / "v" / "captions.srt").write_text("x", encoding="utf-8")
    (tmp_path / "v" / "thumbnail.jpg").write_bytes(b"jpg")
    job.payload = {**job.payload, "result": {**job.payload["result"], "thumbnail": str(tmp_path / "v" / "thumbnail.jpg")}}
    _mock_upload()
    respx.post(THUMBNAIL_URL).mock(return_value=httpx.Response(403, json={}))
    respx.post(CAPTIONS_URL).mock(return_value=httpx.Response(403, json={"error": "insufficientPermissions"}))
    respx.post(PLAYLIST_ITEMS_URL).mock(return_value=httpx.Response(403, json={}))
    logs = []
    outcome = upload_stage(StageContext(db, job, _run(db, job, chan), logs.append, lambda: False))
    assert outcome.next_status == "published" and any("caption file not added" in m for m in logs)


@respx.mock
def test_revoked_access_marks_the_channel_for_reconnect(db, tmp_path):
    chan = _connect(db)
    job = _ready_job(db, tmp_path, status="uploading")
    respx.post(oauth.TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "invalid_grant"}))
    with pytest.raises(YouTubeError):
        upload_stage(StageContext(db, job, _run(db, job, chan), lambda m: None, lambda: False))
    assert chan.needs_reconnect and "invalid_grant" in chan.last_error


def test_playlist_ids_from_links():
    assert playlist_id_from("https://www.youtube.com/playlist?list=PLx1234567890abc") == "PLx1234567890abc"
    assert playlist_id_from("PLx1234567890abc") == "PLx1234567890abc"
    assert playlist_id_from("not a playlist!") is None


def test_channel_settings_api(client, db):
    chan = _connect(db)
    r = client.put(f"/api/youtube/channels/{chan.id}", json={"daily_limit": 3, "playlist": "https://youtube.com/playlist?list=PLx1234567890abc"},
                   headers=H)  # fmt: skip
    assert r.status_code == 200 and r.json()["daily_limit"] == 3 and r.json()["playlist_id"] == "PLx1234567890abc"
    assert client.put(f"/api/youtube/channels/{chan.id}", json={"playlist": "nope!"}, headers=H).status_code == 422
    status = client.get("/api/youtube", headers=H).json()
    assert status["quota"]["limit"] == 10_000 and status["channels"][0]["uploads_today"] == 0
    assert db.scalar(select(YouTubeChannel)).daily_limit == 3
