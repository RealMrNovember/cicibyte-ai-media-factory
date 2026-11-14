import contextlib
import json
import urllib.parse
from datetime import datetime, timedelta, timezone

import httpx
import respx
from sqlalchemy import select

from mediafactory.core.crypto import encrypt
from mediafactory.db.models import JobStageRun, ProductionJob, Schedule, SourceItem, YouTubeChannel
from mediafactory.queue.registry import StageContext
from mediafactory.schedule.runner import run_due
from mediafactory.youtube import oauth
from mediafactory.youtube.publish import upload_stage
from mediafactory.youtube.upload import UPLOAD_URL, build_metadata

H = {"X-MF-Client": "1"}
NOW = datetime(2026, 11, 16, 9, 0, tzinfo=timezone.utc)


def _item(db, n):
    text = "A long quiet story. " * 40
    it = SourceItem(source_type="manual", title=f"story {n}", raw_text=text, normalized_text=text, content_hash=f"h{n}")
    db.add(it)
    db.flush()
    return it


def _factory(db):
    return lambda: contextlib.nullcontext(db)


def _ready_job(db, tmp_path, status="approved"):
    folder = tmp_path / "v"
    folder.mkdir(exist_ok=True)
    (folder / "short.mp4").write_bytes(b"\x00" * 2048)
    (folder / "script.json").write_text(json.dumps({"title": "Eleven Gallons", "description": "d", "tags": ["horror", "scary story"]}))
    job = ProductionJob(status=status, language="en", payload={"result": {"video": str(folder / "short.mp4"), "folder": str(folder)}})
    db.add(job)
    db.flush()
    return job


def _connect(db):
    oauth.set_client(db, "cid-1234567890.apps.googleusercontent.com", "secret-123")
    chan = YouTubeChannel(channel_id="UC1", title="Night Tales", refresh_token_enc=encrypt("rt"), is_default=True)
    db.add(chan)
    db.flush()
    return chan


def test_produce_schedule_makes_videos_and_plans_next_run(db):
    items = [_item(db, n) for n in (1, 2, 3)]
    sch = Schedule(name="daily", kind="produce", enabled=True, times=["09:00"], weekdays=list(range(7)), timezone="UTC",
                   params={"count": 2, "languages": ["en", "tr"], "auto_approve": True}, next_run_at=NOW - timedelta(minutes=1))
    db.add(sch)
    db.flush()
    assert run_due(_factory(db), now=NOW) == 1
    jobs = list(db.scalars(select(ProductionJob)))
    assert len(jobs) == 4 and all(j.payload["auto_approve"] for j in jobs)
    assert sch.next_run_at == NOW + timedelta(days=1)
    assert sch.last_result == "2 stories → 4 videos"
    assert sorted(i.processing_status for i in items) == ["discovered", "queued", "queued"]


def test_schedule_not_due_does_nothing(db):
    db.add(Schedule(name="x", kind="produce", enabled=True, times=["09:00"], weekdays=list(range(7)), timezone="UTC",
                    params={}, next_run_at=NOW + timedelta(hours=1)))
    db.flush()
    assert run_due(_factory(db), now=NOW) == 0


def test_publish_schedule_queues_oldest_approved(db, tmp_path):
    _connect(db)
    job = _ready_job(db, tmp_path)
    db.add(Schedule(name="evening", kind="publish", enabled=True, times=["18:00"], weekdays=list(range(7)),
                    timezone="Europe/Istanbul", params={"count": 1, "privacy": "public"}, next_run_at=NOW))
    db.flush()
    run_due(_factory(db), now=NOW)
    assert job.status == "uploading"
    run = db.scalar(select(JobStageRun).where(JobStageRun.job_id == job.id))
    assert run.stage == "upload_youtube" and run.inputs["privacy"] == "public"


def test_metadata_for_scheduled_upload_is_private_with_publish_time():
    at = datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc)
    meta = build_metadata({"title": "<b>Hi</b>", "tags": ["horror"]}, language="en", privacy="public", publish_at=at)
    assert meta["status"]["privacyStatus"] == "private"
    assert meta["status"]["publishAt"] == "2026-11-20T15:00:00.000Z"
    assert meta["status"]["containsSyntheticMedia"] is True
    assert "<" not in meta["snippet"]["title"]
    assert "#shorts" in meta["snippet"]["description"]


@respx.mock
def test_upload_stage_sends_video_and_marks_published(db, tmp_path):
    chan = _connect(db)
    job = _ready_job(db, tmp_path, status="uploading")
    run = JobStageRun(job_id=job.id, stage="upload_youtube", job_class="io", inputs={"privacy": "public", "channel_db_id": chan.id})
    db.add(run)
    db.flush()
    respx.post(oauth.TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "at"}))
    init = respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, headers={"Location": "https://upload.example/session1"}))
    respx.put("https://upload.example/session1").mock(return_value=httpx.Response(200, json={"id": "vid123"}))
    outcome = upload_stage(StageContext(db, job, run, lambda m: None, lambda: False))
    assert outcome.next_status == "published"
    assert job.payload["youtube"]["url"] == "https://youtube.com/shorts/vid123"
    sent = json.loads(init.calls[0].request.content)
    assert sent["snippet"]["title"] == "Eleven Gallons" and sent["status"]["privacyStatus"] == "public"


def test_publish_api_rejects_past_time_and_unready(client, db, tmp_path):
    _connect(db)
    job = _ready_job(db, tmp_path)
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert client.post(f"/api/jobs/{job.id}/publish", json={"publish_at": past}, headers=H).status_code == 409
    fresh = ProductionJob(status="discovered", language="en", payload={})
    db.add(fresh)
    db.flush()
    assert client.post(f"/api/jobs/{fresh.id}/publish", json={}, headers=H).status_code == 409
    later = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    r = client.post(f"/api/jobs/{job.id}/publish", json={"publish_at": later, "privacy": "public"}, headers=H)
    assert r.status_code == 200 and job.status == "uploading"


def test_schedule_api_validates_and_plans(client):
    bad = {"name": "x", "kind": "produce", "times": ["9:75"], "timezone": "UTC"}
    assert client.post("/api/schedules", json=bad, headers=H).status_code == 422
    ok = {"name": "Morning", "kind": "produce", "times": ["9:05", "18:00"], "weekdays": [0, 2, 4],
          "timezone": "Europe/Istanbul", "params": {"count": 2, "languages": ["tr"]}}
    r = client.post("/api/schedules", json=ok, headers=H)
    assert r.status_code == 201
    body = r.json()
    assert body["times"] == ["09:05", "18:00"] and body["next_run_at"] and body["params"]["count"] == 2
    assert client.post("/api/schedules", json={**ok, "params": {"count": 99}}, headers=H).status_code == 422


@respx.mock
def test_connect_channel_flow(client, db):
    assert client.put("/api/youtube/client", json={"client_id": "cid-1234567890.apps.googleusercontent.com",
                                                   "client_secret": "secret-123"}, headers=H).status_code == 200  # fmt: skip
    redirect = "http://127.0.0.1:5555/api/youtube/callback"
    url = client.post("/api/youtube/auth", json={"redirect_uri": redirect}, headers=H).json()["url"]
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    assert q["redirect_uri"] == [redirect] and q["access_type"] == ["offline"] and q["code_challenge_method"] == ["S256"]
    respx.post(oauth.TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "at", "refresh_token": "rt"}))
    respx.get(oauth.CHANNELS_URL).mock(return_value=httpx.Response(200, json={"items": [{"id": "UC9", "snippet": {"title": "Night Tales"}}]}))
    r = client.get("/api/youtube/callback", params={"state": q["state"][0], "code": "c"})
    assert r.status_code == 200 and "Night Tales" in r.text
    assert client.get("/api/youtube").json()["channels"][0]["title"] == "Night Tales"
    again = client.get("/api/youtube/callback", params={"state": q["state"][0], "code": "c"})
    assert again.status_code == 400  # a sign-in link works once


@respx.mock
def test_upload_stage_sets_cover_image_and_survives_refusal(db, tmp_path):
    from mediafactory.youtube.upload import THUMBNAIL_URL

    chan = _connect(db)
    job = _ready_job(db, tmp_path, status="uploading")
    (tmp_path / "v" / "thumbnail.jpg").write_bytes(b"\xff\xd8jpeg")
    job.payload = {**job.payload, "result": {**job.payload["result"], "thumbnail": str(tmp_path / "v" / "thumbnail.jpg")}}
    run = JobStageRun(job_id=job.id, stage="upload_youtube", job_class="io", inputs={"privacy": "public", "channel_db_id": chan.id})
    db.add(run)
    db.flush()
    respx.post(oauth.TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "at"}))
    respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, headers={"Location": "https://upload.example/s2"}))
    respx.put("https://upload.example/s2").mock(return_value=httpx.Response(200, json={"id": "vid9"}))
    cover = respx.post(THUMBNAIL_URL).mock(return_value=httpx.Response(403, json={"error": "not verified"}))
    logs = []
    outcome = upload_stage(StageContext(db, job, run, logs.append, lambda: False))
    assert outcome.next_status == "published" and cover.called
    assert cover.calls[0].request.url.params["videoId"] == "vid9"
    assert any("not accepted" in line for line in logs)
