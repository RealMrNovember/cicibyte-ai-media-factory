import hashlib
import json
import urllib.parse
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from sqlalchemy import select

from mediafactory.db.models import JobStageRun, Schedule, SystemSetting
from mediafactory.instagram import publish as igp
from mediafactory.publishing import publish_job
from mediafactory.queue.registry import StageContext
from mediafactory.schedule.runner import run_due
from mediafactory.tiktok import client as tt
from mediafactory.tiktok import publish as ttp
from mediafactory.tiktok.client import TikTokError
from tests.test_schedules_youtube import NOW, _factory, _ready_job

H = {"X-MF-Client": "1"}
API = tt.API
REDIRECT = "http://127.0.0.1:51234/api/tiktok/callback"
TOKENS = {"access_token": "act." + "a" * 30, "refresh_token": "rft." + "r" * 30, "open_id": "OPEN1", "expires_in": 86400,
          "refresh_expires_in": 31536000, "scope": "user.info.basic,video.upload", "token_type": "Bearer"}  # fmt: skip


def _ctx(db, job, run):
    return StageContext(db, job, run, lambda m: None, lambda: False)


def _runs(db, job):
    return db.scalars(select(JobStageRun).where(JobStageRun.job_id == job.id).order_by(JobStageRun.id)).all()


def _connect_tt(db, **over):
    ttp.set_app(db, "awkey12345", "secret-12345")
    return ttp.save_tokens(db, {**TOKENS, **over}, info={"open_id": "OPEN1", "display_name": "Cici Tales", "avatar": None})


# ---------- client ----------


def test_pkce_challenge_is_hex_sha256_as_tiktok_wants():
    verifier, challenge = tt.pkce()
    assert 43 <= len(verifier) <= 128
    assert challenge == hashlib.sha256(verifier.encode()).hexdigest()


def test_auth_url_asks_for_draft_scopes_only_unless_direct():
    url = tt.auth_url("awkey", REDIRECT, "st", "ch", direct=False)
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
    assert url.startswith(tt.AUTH_URL) and q["client_key"] == "awkey" and q["redirect_uri"] == REDIRECT
    assert q["scope"] == "user.info.basic,video.upload" and q["code_challenge_method"] == "S256" and q["state"] == "st"
    q2 = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(tt.auth_url("k", REDIRECT, "s", "c", direct=True)).query))
    assert "video.publish" in q2["scope"].split(",")


def test_chunk_plan_follows_the_media_transfer_rules():
    assert tt.chunk_plan(2048) == (2048, 1)  # under 5 MB: one whole chunk
    assert tt.chunk_plan(8 * 2**20) == (8 * 2**20, 1)
    size = 47 * 2**20 + 123
    chunk, count = tt.chunk_plan(size)
    assert chunk == 10 * 2**20 and count == 4  # rounded down; the last chunk takes the rest (< 20 MB)
    assert size - chunk * (count - 1) < 64 * 2**20


@respx.mock
def test_draft_upload_sends_chunks_and_waits_for_the_inbox(tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"\x01" * 3000)
    init = respx.post(f"{API}/post/publish/inbox/video/init/").mock(return_value=httpx.Response(200, json={
        "data": {"publish_id": "v_inbox_1", "upload_url": "https://open-upload.tiktokapis.com/video/?upload_id=1"},
        "error": {"code": "ok", "message": ""}}))  # fmt: skip
    put = respx.put("https://open-upload.tiktokapis.com/video/?upload_id=1").mock(return_value=httpx.Response(201))
    status = respx.post(f"{API}/post/publish/status/fetch/").mock(side_effect=[
        httpx.Response(200, json={"data": {"status": "PROCESSING_UPLOAD"}, "error": {"code": "ok"}}),
        httpx.Response(200, json={"data": {"status": "SEND_TO_USER_INBOX"}, "error": {"code": "ok"}}),
    ])  # fmt: skip
    waits = []
    result = tt.send_video("tok", video, sleep=waits.append)
    assert result == {"publish_id": "v_inbox_1", "status": "SEND_TO_USER_INBOX", "post_id": None}
    body = json.loads(init.calls[0].request.content)
    assert body == {"source_info": {"source": "FILE_UPLOAD", "video_size": 3000, "chunk_size": 3000, "total_chunk_count": 1}}
    assert init.calls[0].request.headers["authorization"] == "Bearer tok"
    head = put.calls[0].request.headers
    assert head["content-range"] == "bytes 0-2999/3000" and head["content-type"] == "video/mp4"
    assert json.loads(status.calls[0].request.content) == {"publish_id": "v_inbox_1"} and waits


@respx.mock
def test_direct_post_sends_post_info_and_returns_the_post(tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"\x01" * 10)
    init = respx.post(f"{API}/post/publish/video/init/").mock(return_value=httpx.Response(200, json={
        "data": {"publish_id": "p1", "upload_url": "https://up.example/1"}, "error": {"code": "ok"}}))  # fmt: skip
    respx.put("https://up.example/1").mock(return_value=httpx.Response(201))
    respx.post(f"{API}/post/publish/status/fetch/").mock(return_value=httpx.Response(200, json={
        "data": {"status": "PUBLISH_COMPLETE", "publicaly_available_post_id": [7311]}, "error": {"code": "ok"}}))  # fmt: skip
    info = {"title": "Hi #x", "privacy_level": "SELF_ONLY"}
    result = tt.send_video("tok", video, post_info=info, sleep=lambda s: None)
    assert result["post_id"] == "7311" and json.loads(init.calls[0].request.content)["post_info"] == info


@respx.mock
def test_failed_processing_and_api_errors_are_reported(tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x")
    respx.post(f"{API}/post/publish/inbox/video/init/").mock(return_value=httpx.Response(429, json={
        "error": {"code": "rate_limit_exceeded", "message": "slow down"}}))  # fmt: skip
    with pytest.raises(TikTokError) as e:
        tt.send_video("tok", video, sleep=lambda s: None)
    assert e.value.transient and "slow down" in str(e.value)
    respx.post(f"{API}/post/publish/inbox/video/init/").mock(return_value=httpx.Response(403, json={
        "error": {"code": "spam_risk_too_many_pending_share", "message": "too many"}}))  # fmt: skip
    with pytest.raises(TikTokError, match="5 drafts") as e:
        tt.send_video("tok", video, sleep=lambda s: None)
    assert not e.value.transient


@respx.mock
def test_token_exchange_sends_the_verifier_and_reports_refusals():
    route = respx.post(tt.TOKEN_URL).mock(return_value=httpx.Response(200, json=TOKENS))
    out = tt.exchange_code({"client_key": "k", "client_secret": "s"}, "CODE", "VER", REDIRECT)
    sent = dict(httpx.QueryParams(route.calls[0].request.content.decode()))
    assert out["open_id"] == "OPEN1" and sent["code_verifier"] == "VER" and sent["grant_type"] == "authorization_code"
    respx.post(tt.TOKEN_URL).mock(return_value=httpx.Response(200, json={"error": "invalid_grant", "error_description": "bad code"}))
    with pytest.raises(TikTokError, match="bad code"):
        tt.exchange_code({"client_key": "k", "client_secret": "s"}, "CODE", "VER", REDIRECT)


# ---------- connection ----------


def test_app_secret_and_tokens_are_stored_encrypted(client, db):
    r = client.put("/api/tiktok/app", json={"client_key": "awkey12345", "client_secret": "secret-12345"}, headers=H)
    assert r.status_code == 200
    _connect_tt(db)
    blob = str(db.get(SystemSetting, ttp.APP_KEY).value) + str(db.get(SystemSetting, ttp.ACCOUNT_KEY).value)
    assert "secret-12345" not in blob and "act.aaa" not in blob and "rft.rrr" not in blob
    st = client.get("/api/tiktok", headers=H).json()
    assert st["client_key"] == "awkey12345" and st["account"]["display_name"] == "Cici Tales" and st["account"]["mode"] == "draft"
    assert "rft." not in json.dumps(st) and "secret-12345" not in json.dumps(st)


def test_sign_in_flow_needs_a_loopback_address_and_finishes_in_the_callback(client, db, monkeypatch):
    ttp.set_app(db, "awkey12345", "secret-12345")
    assert client.post("/api/tiktok/auth", json={"redirect_uri": "http://mediafactory:8080/api/tiktok/callback"}, headers=H).status_code == 422
    url = client.post("/api/tiktok/auth", json={"redirect_uri": REDIRECT}, headers=H).json()["url"]
    state = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))["state"]
    seen = {}

    def fake_exchange(app, code, verifier, redirect_uri, **kw):
        seen.update(code=code, verifier=verifier, redirect_uri=redirect_uri)
        return TOKENS

    monkeypatch.setattr(tt, "exchange_code", fake_exchange)
    monkeypatch.setattr(tt, "user_info", lambda token, **kw: {"open_id": "OPEN1", "display_name": "Cici Tales", "avatar": None})
    page = client.get(f"/api/tiktok/callback?state={state}&code=CODE1", headers=H)
    assert page.status_code == 200 and "Cici Tales" in page.text
    assert seen["code"] == "CODE1" and seen["redirect_uri"] == REDIRECT and len(seen["verifier"]) >= 43
    assert ttp.get_account(db)["display_name"] == "Cici Tales"
    again = client.get(f"/api/tiktok/callback?state={state}&code=CODE1", headers=H)
    assert again.status_code == 400  # a link works once


def test_access_token_is_refreshed_when_it_runs_out_and_the_new_refresh_token_kept(db, monkeypatch):
    _connect_tt(db, expires_in=60)  # expires within the safety margin
    monkeypatch.setattr(tt, "refresh", lambda app, rt, **kw: {**TOKENS, "access_token": "act.new", "refresh_token": "rft.new"})
    token, acc = ttp.access_token(db)
    assert token == "act.new"
    from mediafactory.core.crypto import decrypt

    assert decrypt(ttp.get_account(db)["refresh_enc"]) == "rft.new"


def test_revoked_access_asks_to_reconnect(db, monkeypatch):
    _connect_tt(db, expires_in=60)

    def refused(app, rt, **kw):
        raise TikTokError("TikTok refused the refresh: invalid_grant", reauth=True)

    monkeypatch.setattr(tt, "refresh", refused)
    with pytest.raises(TikTokError, match="reconnect"):
        ttp.access_token(db)
    assert ttp.get_account(db)["needs_reconnect"] is True


def test_direct_mode_needs_the_publish_permission_and_a_chosen_privacy(client, db, monkeypatch):
    _connect_tt(db)
    r = client.put("/api/tiktok/mode", json={"mode": "direct", "privacy_level": "PUBLIC_TO_EVERYONE"}, headers=H)
    assert r.status_code == 409 and "reconnect" in r.json()["detail"]
    _connect_tt(db, scope="user.info.basic,video.upload,video.publish")
    monkeypatch.setattr(tt, "creator_info", lambda token, **kw: {"creator_nickname": "Cici",
                        "privacy_level_options": ["SELF_ONLY", "MUTUAL_FOLLOW_FRIENDS"]})  # fmt: skip
    r = client.put("/api/tiktok/mode", json={"mode": "direct", "privacy_level": "PUBLIC_TO_EVERYONE"}, headers=H)
    assert r.status_code == 422  # not one of the account's options
    assert client.put("/api/tiktok/mode", json={"mode": "direct"}, headers=H).status_code == 422  # no default privacy
    r = client.put("/api/tiktok/mode", json={"mode": "direct", "privacy_level": "SELF_ONLY"}, headers=H)
    assert r.status_code == 200 and r.json()["account"]["mode"] == "direct"


# ---------- publishing ----------


def test_tiktok_only_publish_sends_a_draft_and_marks_the_inbox(db, tmp_path, monkeypatch):
    _connect_tt(db)
    job = _ready_job(db, tmp_path)
    publish_job(db, job, platforms=["tiktok"])
    assert job.status == "uploading" and job.payload["tiktok"]["state"] == "queued"
    runs = _runs(db, job)
    assert [r.stage for r in runs] == ["upload_tiktok"]
    seen = {}

    def fake_send(token, video, *, post_info=None, **kw):
        seen.update(token=token, post_info=post_info)
        return {"publish_id": "v_inbox_1", "status": "SEND_TO_USER_INBOX", "post_id": None}

    monkeypatch.setattr(tt, "send_video", fake_send)
    outcome = ttp.upload_stage(_ctx(db, job, runs[0]))
    assert outcome.next_status == "published" and seen["post_info"] is None and seen["token"].startswith("act.")
    t = job.payload["tiktok"]
    assert t["state"] == "inbox" and t["publish_id"] == "v_inbox_1" and t["caption"].startswith("Eleven Gallons")


def test_direct_mode_posts_with_the_chosen_privacy_and_ai_label(db, tmp_path, monkeypatch):
    _connect_tt(db, scope="user.info.basic,video.upload,video.publish")
    ttp.set_mode(db, "direct", "SELF_ONLY")
    job = _ready_job(db, tmp_path)
    publish_job(db, job, platforms=["tiktok"])
    monkeypatch.setattr(tt, "creator_info", lambda token, **kw: {"privacy_level_options": ["SELF_ONLY"], "comment_disabled": True})
    seen = {}

    def fake_send(token, video, *, post_info=None, **kw):
        seen.update(post_info=post_info)
        return {"publish_id": "p1", "status": "PUBLISH_COMPLETE", "post_id": "7311"}

    monkeypatch.setattr(tt, "send_video", fake_send)
    ttp.upload_stage(_ctx(db, job, _runs(db, job)[0]))
    info = seen["post_info"]
    assert info["privacy_level"] == "SELF_ONLY" and info["is_aigc"] is True and info["disable_comment"] is True
    assert info["title"].startswith("Eleven Gallons")
    assert job.payload["tiktok"]["state"] == "published" and job.payload["tiktok"]["url"].endswith("/video/7311")


def test_three_platforms_run_one_after_another(db, tmp_path, monkeypatch):
    from tests.test_schedules_youtube import _connect

    _connect(db)
    igp.save_account(db, "IGtoken-" + "x" * 30, info={"user_id": "1", "username": "cici", "account_type": "BUSINESS"})
    _connect_tt(db)
    job = _ready_job(db, tmp_path)
    publish_job(db, job, platforms=["youtube", "instagram", "tiktok"])
    assert [r.stage for r in _runs(db, job)] == ["upload_youtube"]
    assert job.payload["tiktok"]["after"] == "instagram"
    from mediafactory.publishing import next_stage_after

    assert next_stage_after(job, "youtube") == ("upload_instagram", "io")
    assert next_stage_after(job, "instagram") == ("upload_tiktok", "io")
    # Instagram failing for good still lets TikTok go
    from mediafactory.instagram import client as ig

    monkeypatch.setattr(ig, "publish_reel", lambda *a, **kw: (_ for _ in ()).throw(ig.InstagramError("nope")))
    run = JobStageRun(job_id=job.id, stage="upload_instagram", job_class="io", inputs={"attempt": 1})
    outcome = igp.upload_stage(_ctx(db, job, run))
    assert outcome.next_stage == ("upload_tiktok", "io")


def test_tiktok_only_without_youtube_or_instagram_follows_nothing(db, tmp_path):
    from tests.test_schedules_youtube import _connect

    _connect(db)
    _connect_tt(db)
    job = _ready_job(db, tmp_path)
    publish_job(db, job, platforms=["youtube", "tiktok"])
    assert job.payload["tiktok"]["after"] == "youtube"
    from mediafactory.publishing import next_stage_after

    assert next_stage_after(job, "youtube") == ("upload_tiktok", "io")


def test_failure_keeps_other_platforms_and_transient_errors_retry(db, tmp_path, monkeypatch):
    _connect_tt(db)
    job = _ready_job(db, tmp_path, status="published")
    job.payload = {**job.payload, "youtube": {"state": "published", "id": "v", "url": "u"}}
    publish_job(db, job, platforms=["tiktok"])
    monkeypatch.setattr(tt, "send_video", lambda *a, **kw: (_ for _ in ()).throw(TikTokError("busy", transient=True)))
    ttp.upload_stage(_ctx(db, job, _runs(db, job)[0]))
    runs = _runs(db, job)
    assert len(runs) == 2 and runs[1].inputs["attempt"] == 2 and runs[1].run_after > datetime.now(UTC)
    monkeypatch.setattr(tt, "send_video", lambda *a, **kw: (_ for _ in ()).throw(TikTokError("bad video")))
    outcome = ttp.upload_stage(_ctx(db, job, runs[1]))
    assert outcome.next_status == "published" and job.payload["tiktok"]["state"] == "failed"
    publish_job(db, job, platforms=["tiktok"])  # can try again after a failure
    assert job.payload["tiktok"]["state"] == "queued"


def test_cannot_send_twice_or_without_connection(db, tmp_path):
    job = _ready_job(db, tmp_path)
    with pytest.raises(ValueError, match="TikTok"):
        publish_job(db, job, platforms=["tiktok"])
    _connect_tt(db)
    publish_job(db, job, platforms=["tiktok"])
    with pytest.raises(ValueError, match="already"):
        publish_job(db, job, platforms=["tiktok"])


def test_scheduled_tiktok_waits_for_its_time(db, tmp_path):
    _connect_tt(db)
    job = _ready_job(db, tmp_path)
    at = datetime.now(UTC) + timedelta(hours=3)
    publish_job(db, job, platforms=["tiktok"], publish_at=at)
    assert job.status == "scheduled" and abs(_runs(db, job)[0].run_after - at) < timedelta(seconds=1)


def test_publish_api_and_schedule_accept_tiktok(client, db, tmp_path):
    _connect_tt(db)
    job = _ready_job(db, tmp_path)
    r = client.post(f"/api/jobs/{job.id}/publish", json={"platforms": ["tiktok"]}, headers=H)
    assert r.status_code == 200 and r.json()["tiktok"]["state"] == "queued"
    job2 = _ready_job(db, tmp_path / "b") if (tmp_path / "b").mkdir() is None else None
    db.add(Schedule(name="tt", kind="publish", enabled=True, times=["18:00"], weekdays=list(range(7)),
                    timezone="UTC", params={"count": 1, "platforms": ["tiktok"]}, next_run_at=NOW))  # fmt: skip
    db.flush()
    run_due(_factory(db), now=NOW)
    assert job2.payload["tiktok"]["state"] == "queued"


def test_manual_pack_and_mark_shared(client, db, tmp_path):
    job = _ready_job(db, tmp_path)
    pack = client.get(f"/api/jobs/{job.id}/tiktok-pack", headers=H).json()
    assert pack["caption"].startswith("Eleven Gallons") and "#horror" in pack["caption"]
    assert client.post(f"/api/jobs/{job.id}/tiktok-manual", headers=H).json()["tiktok"]["state"] == "manual"


def test_export_and_import_carry_the_tiktok_connection(db):
    from mediafactory import portability

    _connect_tt(db)
    out = portability.export_settings(db, password="pw-123456")
    assert "rft." not in json.dumps(out["data"])
    ttp.remove_account(db)
    db.delete(db.get(SystemSetting, ttp.APP_KEY))
    db.flush()
    portability.import_settings(db, out, password="pw-123456")
    from mediafactory.core.crypto import decrypt

    assert ttp.get_app(db)["client_secret"] == "secret-12345"
    assert decrypt(ttp.get_account(db)["refresh_enc"]) == TOKENS["refresh_token"]
