import httpx
import respx

from mediafactory.db.models import JobStageRun
from mediafactory.queue.registry import StageContext
from mediafactory.youtube import oauth
from mediafactory.youtube.publish import upload_stage
from mediafactory.youtube.upload import UPLOAD_URL, upload_video
from tests.test_schedules_youtube import _connect, _ready_job

SESSION = "https://upload.example/session-1"


def _video(tmp_path, size=2048):
    p = tmp_path / "v.mp4"
    p.write_bytes(b"\x01" * size)
    return p


@respx.mock
def test_new_upload_reports_its_session_before_sending(tmp_path):
    init = respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, headers={"Location": SESSION}))
    respx.put(SESSION).mock(return_value=httpx.Response(200, json={"id": "v1"}))
    seen = []
    assert upload_video("t", _video(tmp_path), {}, on_session=seen.append) == "v1"
    assert seen == [SESSION] and init.called


@respx.mock
def test_a_finished_session_is_not_uploaded_again(tmp_path):
    init = respx.post(UPLOAD_URL)
    status = respx.put(SESSION).mock(return_value=httpx.Response(200, json={"id": "v-earlier"}))
    assert upload_video("t", _video(tmp_path), {}, session_url=SESSION) == "v-earlier"
    assert not init.called and status.calls[0].request.headers["content-range"] == "bytes */2048"


@respx.mock
def test_an_interrupted_session_resumes_from_where_it_stopped(tmp_path):
    calls = []

    def put(request):
        calls.append(request)
        if len(calls) == 1:  # status check
            return httpx.Response(308, headers={"Range": "bytes=0-1023"})
        return httpx.Response(201, json={"id": "v-resumed"})

    respx.put(SESSION).mock(side_effect=put)
    assert upload_video("t", _video(tmp_path), {}, session_url=SESSION) == "v-resumed"
    assert calls[1].headers["content-range"] == "bytes 1024-2047/2048" and len(calls[1].content) == 1024


@respx.mock
def test_an_expired_session_starts_a_new_upload(tmp_path):
    respx.put(SESSION).mock(return_value=httpx.Response(404))
    respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, headers={"Location": "https://upload.example/new"}))
    respx.put("https://upload.example/new").mock(return_value=httpx.Response(200, json={"id": "v-new"}))
    assert upload_video("t", _video(tmp_path), {}, session_url=SESSION) == "v-new"


@respx.mock
def test_stage_retry_after_a_recorded_upload_does_not_upload_again(db, tmp_path):
    chan = _connect(db)
    job = _ready_job(db, tmp_path, status="uploading")
    job.payload = {**job.payload, "youtube": {"state": "uploaded", "id": "v-done", "channel": chan.title}}
    run = JobStageRun(job_id=job.id, stage="upload_youtube", job_class="io", inputs={"privacy": "public", "channel_db_id": chan.id})
    db.add(run)
    db.flush()
    respx.post(oauth.TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "at"}))
    init = respx.post(UPLOAD_URL)
    outcome = upload_stage(StageContext(db, job, run, lambda m: None, lambda: False))
    assert not init.called and outcome.next_status == "published" and job.payload["youtube"]["id"] == "v-done"


@respx.mock
def test_stage_records_session_and_id_as_it_goes(db, tmp_path):
    chan = _connect(db)
    job = _ready_job(db, tmp_path, status="uploading")
    run = JobStageRun(job_id=job.id, stage="upload_youtube", job_class="io", inputs={"privacy": "public", "channel_db_id": chan.id})
    db.add(run)
    db.flush()
    respx.post(oauth.TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "at"}))
    respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, headers={"Location": SESSION}))
    respx.put(SESSION).mock(return_value=httpx.Response(200, json={"id": "v9"}))
    upload_stage(StageContext(db, job, run, lambda m: None, lambda: False))
    assert job.payload["youtube"]["id"] == "v9" and job.payload["youtube"]["session"] == SESSION


def test_sending_again_after_an_interrupted_upload_keeps_its_session(db, tmp_path):
    from mediafactory.youtube.publish import queue_upload

    _connect(db)
    job = _ready_job(db, tmp_path, status="failed")
    job.payload = {**job.payload, "youtube": {"state": "uploading", "session": SESSION}}
    queue_upload(db, job)
    assert job.payload["youtube"]["session"] == SESSION and job.payload["youtube"]["state"] == "queued"
