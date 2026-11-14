"""Regression tests for the whole-branch review findings of Plan 1."""

import json
import time
from datetime import timedelta

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from mediafactory.ai.client import ProviderError, chat
from mediafactory.api.app import create_app
from mediafactory.core.config import Settings
from mediafactory.db.base import utcnow
from mediafactory.db.models import AIProvider, AuditLog, JobStageRun
from tests.conftest import TEST_DATABASE_URL
from tests.helpers import csrf_headers, login


# --- Important 1: get_db must commit before the response is sent -------------------------------
def test_commit_failure_is_not_reported_as_success(db, make_user, monkeypatch):
    from mediafactory.api import deps
    from mediafactory.auth import service

    service.reset_rate_limits()
    make_user()

    class FailingCommit(Session):
        def commit(self):
            raise RuntimeError("commit failed")

    monkeypatch.setattr(
        deps, "SessionLocal", lambda: FailingCommit(bind=db.connection(), join_transaction_mode="create_savepoint")
    )
    client = TestClient(create_app(), raise_server_exceptions=False)
    assert login(client).status_code == 500


# --- Important 3: trusted proxy headers give real client IP and https scheme --------------------
def _proxy_app(db, trusted):
    from mediafactory.api.deps import get_db
    from mediafactory.auth import service

    service.reset_rate_limits()
    s = Settings(
        _env_file=None, database_url=TEST_DATABASE_URL, secret_key="k" * 40,
        allowed_hosts=["testserver"], trusted_proxies=trusted,
    )  # fmt: skip
    app = create_app(s)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_trusted_proxy_headers_used(db, make_user):
    make_user()
    client = _proxy_app(db, ["*"])
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "correct horse battery"},
        headers={"X-Forwarded-For": "203.0.113.9", "X-Forwarded-Proto": "https"},
    )
    assert r.status_code == 200
    assert "secure" in r.headers["set-cookie"].lower()
    row = db.scalar(select(AuditLog).where(AuditLog.action == "auth.login"))
    assert row.ip == "203.0.113.9"


def test_untrusted_proxy_headers_ignored(db, make_user):
    make_user()
    client = _proxy_app(db, ["10.9.9.9"])
    client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "correct horse battery"},
        headers={"X-Forwarded-For": "203.0.113.9"},
    )
    row = db.scalar(select(AuditLog).where(AuditLog.action == "auth.login"))
    assert row.ip != "203.0.113.9"


# --- Important 4: logout / password reset end existing sessions --------------------------------
def test_cookie_replay_after_logout_rejected(client, make_user):
    make_user()
    login(client)
    stolen = dict(client.cookies)
    client.post("/api/auth/logout", headers=csrf_headers(client))
    replay = TestClient(client.app, cookies=stolen)
    assert replay.get("/api/auth/me").status_code == 401


def test_password_reset_ends_sessions(client, make_user, db):
    from mediafactory.auth.service import end_all_sessions

    user = make_user()
    login(client)
    assert client.get("/api/auth/me").status_code == 200
    end_all_sessions(user)
    db.flush()
    assert client.get("/api/auth/me").status_code == 401


# --- Important 2: stale running stages are reclaimed ------------------------------------------
@pytest.fixture
def qfactory(engine):
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    def _wipe():
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE job_stage_runs, production_jobs RESTART IDENTITY CASCADE"))

    _wipe()
    yield sessionmaker(bind=engine, expire_on_commit=False)
    _wipe()


def test_stale_running_run_is_reclaimed(qfactory):
    from mediafactory.queue.claim import claim_next
    from mediafactory.queue.jobs import create_job, enqueue_stage

    with qfactory() as s:
        job = create_job(s)
        run = enqueue_stage(s, job.id, "render_it", "render")
        run.state, run.attempts = "running", 1
        run.started_at = run.heartbeat_at = utcnow() - timedelta(minutes=30)
        s.commit()
        rid = run.id
    with qfactory() as s:
        claimed = claim_next(s, worker_id="new", limits={"render": 1})
        s.commit()
    assert claimed is not None and claimed.id == rid and claimed.attempts == 2


def test_worker_heartbeats_while_running(qfactory):
    from mediafactory.queue import registry as reg
    from mediafactory.queue.jobs import create_job, enqueue_stage
    from mediafactory.queue.registry import StageOutcome
    from mediafactory.queue.worker import process_one

    seen = {}

    def slow(ctx):
        time.sleep(0.6)
        with qfactory() as s:
            r = s.get(JobStageRun, ctx.run.id)
            seen["hb"], seen["start"] = r.heartbeat_at, r.started_at
        return StageOutcome(next_status="normalized")

    saved = dict(reg.HANDLERS)
    reg.HANDLERS.clear()
    reg.stage_handler("slow", "io")(slow)
    try:
        with qfactory() as s:
            job = create_job(s)
            enqueue_stage(s, job.id, "slow", "io")
            s.commit()
        process_one(qfactory, worker_id="w", limits={"io": 1}, heartbeat_s=0.1)
    finally:
        reg.HANDLERS.clear()
        reg.HANDLERS.update(saved)
    assert seen["hb"] > seen["start"]


# --- Minor 7: retry while active refused; cancelled handler work not committed ---------------------
def test_retry_refused_while_stage_active(qfactory):
    from mediafactory.queue.jobs import JobBusy, cancel_job, create_job, enqueue_stage, retry_failed

    with qfactory() as s:
        job = create_job(s)
        enqueue_stage(s, job.id, "a", "io")
        enqueue_stage(s, job.id, "b", "io")
        s.commit()
        jid = job.id
    with qfactory() as s:
        first = s.scalar(select(JobStageRun).where(JobStageRun.stage == "a"))
        first.state = "failed"
        s.commit()
    with qfactory() as s, pytest.raises(JobBusy):
        retry_failed(s, jid)
    with qfactory() as s:
        cancel_job(s, jid)
        s.commit()


def test_cancelled_handler_changes_not_committed(qfactory):
    from mediafactory.db.models import ProductionJob
    from mediafactory.queue import registry as reg
    from mediafactory.queue.jobs import cancel_job, create_job, enqueue_stage
    from mediafactory.queue.registry import StageOutcome
    from mediafactory.queue.worker import process_one

    def h(ctx):
        with qfactory() as s:
            cancel_job(s, ctx.job.id)
            s.commit()
        ctx.job.payload = {"written_by_handler": True}
        return StageOutcome(next_status="normalized")

    saved = dict(reg.HANDLERS)
    reg.HANDLERS.clear()
    reg.stage_handler("h", "io")(h)
    try:
        with qfactory() as s:
            job = create_job(s)
            enqueue_stage(s, job.id, "h", "io")
            s.commit()
            jid = job.id
        process_one(qfactory, worker_id="w", limits={"io": 1})
    finally:
        reg.HANDLERS.clear()
        reg.HANDLERS.update(saved)
    with qfactory() as s:
        job = s.get(ProductionJob, jid)
        assert job.payload.get("cancelled") is True and "written_by_handler" not in job.payload
        assert job.status == "failed"


# --- Minor 1: malformed provider responses become ProviderError ----------------------------------
BASE = "http://llm.test/v1"


def _prov(**kw):
    from mediafactory.core.crypto import encrypt

    base = dict(id=1, name="p", kind="openai_compatible", base_url=BASE, api_key_enc=encrypt("k"),
                locality="remote", timeout_s=5, max_concurrency=1, enabled=True)  # fmt: skip
    return AIProvider(**{**base, **kw})


@respx.mock
def test_non_dict_message_raises_provider_error():
    respx.post(f"{BASE}/chat/completions").mock(return_value=httpx.Response(200, json={"choices": [{"message": "x"}]}))
    with pytest.raises(ProviderError):
        chat(_prov(), "m", [{"role": "user", "content": "hi"}])


@respx.mock
def test_non_dict_sse_chunks_ignored():
    body = 'data: "ping"\n\n' + "data: " + json.dumps({"choices": [{"delta": {"content": "ok"}}]}) + "\n\ndata: [DONE]\n\n"
    respx.post(f"{BASE}/chat/completions").mock(
        return_value=httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})
    )
    assert chat(_prov(locality="local"), "m", [{"role": "user", "content": "hi"}]).text == "ok"


def test_undecryptable_key_is_non_retryable_provider_error():
    with pytest.raises(ProviderError) as e:
        chat(_prov(api_key_enc="garbage"), "m", [{"role": "user", "content": "hi"}])
    assert not e.value.retryable


@respx.mock
def test_decoding_error_is_provider_error():
    respx.post(f"{BASE}/chat/completions").mock(side_effect=httpx.DecodingError("bad gzip"))
    with pytest.raises(ProviderError):
        chat(_prov(), "m", [{"role": "user", "content": "hi"}])
