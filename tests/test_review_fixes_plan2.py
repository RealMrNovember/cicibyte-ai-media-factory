"""Regression tests for the whole-branch review of Plan 2 (sources & ingest)."""

import io
import threading
import time
import zipfile
from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

from mediafactory.db.base import utcnow
from mediafactory.db.models import SourceConnector, SourceItem, SourceRightsRecord
from mediafactory.sources.adapters import AdapterError, FetchContext, RawItem, get_adapter
from mediafactory.sources.ingest import store_items
from mediafactory.sources.text import normalize_text, strip_html
from tests.helpers import csrf_headers, login
from tests.sources.helpers import LONG, make_fetcher


# --- Critical 1: backoff overflow must not kill the poller ---------------------------------------
def test_backoff_does_not_overflow_after_many_failures():
    from mediafactory.sources.poller import schedule_next

    c = SourceConnector(name="x", adapter="rss", params={}, poll_interval_min=60, consecutive_failures=40)
    schedule_next(c, failed=True)
    assert timedelta(hours=23, minutes=59) <= c.next_run_at - utcnow() <= timedelta(hours=24, seconds=5)


def test_failing_source_never_retries_sooner_than_its_interval():
    from mediafactory.sources.poller import schedule_next

    c = SourceConnector(name="x", adapter="rss", params={}, poll_interval_min=7 * 24 * 60, consecutive_failures=3)
    schedule_next(c, failed=True)
    assert c.next_run_at - utcnow() >= timedelta(days=7) - timedelta(seconds=5)


def test_poller_thread_survives_unexpected_error(monkeypatch):
    from mediafactory.sources import poller

    calls = {"n": 0}
    stop = threading.Event()

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("bug")
        stop.set()
        return 0

    monkeypatch.setattr(poller, "poll_due", flaky)
    t = poller.SourcePoller(lambda: None, fetcher=None, stop_event=stop, interval_s=0.01)
    t.error_sleep_s = 0.01
    t.start()
    t.join(timeout=5)
    assert calls["n"] == 2 and not t.is_alive()


# --- Important 2: tag stripping is linear -----------------------------------------------------------
def test_strip_html_is_linear_on_hostile_input():
    started = time.perf_counter()
    strip_html("<" * 200_000)  # quadratic regex: ~30 s; linear: milliseconds
    assert time.perf_counter() - started < 1.0


# --- extra: reddit signature only at the end -----------------------------------------------------
def test_signature_phrase_inside_story_is_kept():
    story = "She whispered: submitted by /u/ghost was carved on the door. " + LONG
    assert normalize_text(story).startswith("She whispered: submitted by /u/ghost")
    tail = LONG + " submitted by /u/writer [link] [comments]"
    assert "submitted by" not in normalize_text(tail)


# --- Important 3: empty feed is an error ----------------------------------------------------------
EMPTY_RSS = b'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>'


def test_empty_feed_is_retryable_adapter_error():
    a = get_adapter("rss")
    with pytest.raises(AdapterError) as e:
        a.fetch(a.validate({"url": "https://example.com/f"}), FetchContext(fetcher=make_fetcher(lambda r: httpx.Response(200, content=EMPTY_RSS))))
    assert e.value.retryable and "no entries" in str(e.value)


def test_all_entries_filtered_is_not_an_error():
    from html import escape

    from tests.sources.helpers import reddit_atom

    a = get_adapter("reddit_rss")
    feed = reddit_atom([("a", "short", escape("<p>tiny</p>"))])
    items = a.fetch(a.validate({"subreddit": "nosleep"}), FetchContext(fetcher=make_fetcher(lambda r: httpx.Response(200, content=feed))))
    assert items == []


def test_relative_feed_links_resolved_against_feed_url():
    feed = f"""<?xml version="1.0"?><rss version="2.0"><channel>
    <item><title>A</title><link>/post/1</link><guid>1</guid><description>{LONG}</description></item>
    <item><title>B</title><link>javascript:alert(1)</link><guid>2</guid><description>{LONG} b</description></item>
    </channel></rss>""".encode()
    a = get_adapter("rss")
    items = a.fetch(a.validate({"url": "https://blog.example/feed.xml"}), FetchContext(fetcher=make_fetcher(lambda r: httpx.Response(200, content=feed))))
    assert items[0].url == "https://blog.example/post/1"
    assert items[1].url is None


# --- extra: non-numeric reddit score skips only that post -----------------------------------------
def test_reddit_non_numeric_score_skips_post():
    import json

    from mediafactory.sources.adapters.reddit import RedditApiAdapter

    children = [
        {"data": {"id": "a", "title": "A", "selftext": LONG, "score": "lots", "permalink": "/r/x/comments/a/"}},
        {"data": {"id": "b", "title": "B", "selftext": LONG, "score": 5, "permalink": "/r/x/comments/b/"}},
    ]
    body = json.dumps({"data": {"children": children}})
    a = RedditApiAdapter()
    items = a._parse(body, a.validate({"subreddit": "nosleep"}))
    assert [i.title for i in items] == ["B"]


# --- Important 6: update semantics --------------------------------------------------------------------
def _src(db, name):
    c = SourceConnector(name=name, adapter="rss", params={})
    db.add(c)
    db.flush()
    return c


def test_same_url_from_another_source_is_duplicate_not_update(db):
    a, b = _src(db, "a"), _src(db, "b")
    store_items(db, a, [RawItem("1", "https://x.example/p", "T", LONG)], source_type="rss")
    r = store_items(db, b, [RawItem("1", "https://x.example/p", "T", LONG + " other text")], source_type="rss")
    assert r.duplicates == 1 and r.updated == 0
    assert "other text" not in db.scalar(select(SourceItem)).normalized_text


def test_manual_text_with_existing_url_does_not_overwrite(db):
    a = _src(db, "a")
    store_items(db, a, [RawItem("1", "https://x.example/p", "T", LONG)], source_type="rss")
    r = store_items(db, None, [RawItem("", "https://x.example/p", "T", LONG + " injected")], source_type="manual")
    assert r.updated == 0 and "injected" not in db.scalar(select(SourceItem)).normalized_text


def test_update_keeps_reviewed_status_and_drops_granted_rights(db):
    a = _src(db, "a")
    store_items(db, a, [RawItem("1", "https://x.example/p", "T", LONG)], source_type="rss")
    item = db.scalar(select(SourceItem))
    item.processing_status, item.rights_status = "rejected", "licensed"
    db.flush()
    r = store_items(db, a, [RawItem("1", "https://x.example/p", "T", LONG + " edited")], source_type="rss")
    assert r.updated == 1
    assert item.processing_status == "rejected" and item.meta.get("changed_after_review") is True
    assert item.rights_status == "unknown"
    last = db.scalars(select(SourceRightsRecord).where(SourceRightsRecord.item_id == item.id).order_by(SourceRightsRecord.id)).all()[-1]
    assert (last.from_status, last.to_status) == ("licensed", "unknown") and "changed" in last.note


def test_insert_race_counts_as_duplicate(db, monkeypatch):
    from mediafactory.sources import ingest

    store_items(db, None, [RawItem("", "https://x.example/p", "T", LONG)], source_type="rss")
    monkeypatch.setattr(ingest, "_find", lambda *a, **k: None)  # as if another process inserted meanwhile
    r = store_items(db, None, [RawItem("", "https://x.example/p", "T", LONG)], source_type="rss")
    assert r.duplicates == 1 and r.new == 0


# --- Important 4/5: uploads ------------------------------------------------------------------------------
def docx_bomb() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", b"0" * (60 * 1024 * 1024))
    return buf.getvalue()


@pytest.fixture
def h(client, make_user):
    make_user()
    login(client)
    return csrf_headers(client)


def test_docx_zip_bomb_rejected_422(client, h):
    data = docx_bomb()
    assert len(data) < 1_000_000
    r = client.post("/api/items/manual/upload", files={"file": ("bomb.docx", data)}, data={"rights_status": "unknown"}, headers=h)
    assert r.status_code == 422 and "too large" in r.json()["detail"]


def test_unexpected_pdf_library_error_is_422(client, h, monkeypatch):
    import pypdf

    class Boom:
        def __init__(self, *a, **k):
            raise ZeroDivisionError("malformed stream")

    monkeypatch.setattr(pypdf, "PdfReader", Boom)
    r = client.post("/api/items/manual/upload", files={"file": ("x.pdf", b"%PDF-1.4 junk")}, data={"rights_status": "unknown"}, headers=h)
    assert r.status_code == 422


def test_extracted_text_is_capped():
    from mediafactory.sources.manual import MAX_TEXT_CHARS, extract_file_text

    out = extract_file_text("big.txt", b"a " * 400_000)
    assert len(out) <= MAX_TEXT_CHARS


def test_oversized_body_rejected_before_auth(app):
    client = TestClient(app)
    big = b"x" * (13 * 1024 * 1024)
    r = client.post("/api/items/manual/upload", content=big, headers={"Content-Type": "multipart/form-data; boundary=x"})
    assert r.status_code == 413


# --- Important 7: run-now vs poller ---------------------------------------------------------------------------
@pytest.fixture
def sf(engine):
    def wipe():
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE source_rights_records, source_items, source_connectors RESTART IDENTITY CASCADE"))

    wipe()
    yield sessionmaker(bind=engine, expire_on_commit=False)
    wipe()


def test_poller_skips_source_locked_by_a_run_in_progress(sf):
    from mediafactory.sources.poller import poll_due

    with sf() as s:
        c = SourceConnector(name="f", adapter="rss", params={"url": "https://example.com/f"})
        s.add(c)
        s.commit()
        cid = c.id
    calls = []
    with sf() as holder:
        holder.get(SourceConnector, cid, with_for_update=True)  # e.g. "run now" in progress
        poll_due(sf, fetcher=make_fetcher(lambda r: calls.append(1) or httpx.Response(200, text="x")))
        holder.rollback()
    assert calls == []


# --- Important 8: robots cache expires ------------------------------------------------------------------------
def test_robots_failure_is_retried_after_short_ttl():
    from mediafactory.core.net import SafeFetcher
    from tests.core.test_net import resolver_for

    now = {"t": 1000.0}
    status = {"code": 503}

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(status["code"])
        return httpx.Response(200)

    f = SafeFetcher(transport=httpx.MockTransport(handler), resolver=resolver_for({}), sleep=lambda s: None,
                    clock=lambda: now["t"])  # fmt: skip
    assert f.robots_allowed("https://example.com/a") is False
    status["code"] = 404
    now["t"] += 6 * 60
    assert f.robots_allowed("https://example.com/a") is True


def test_run_now_while_source_is_running_409(sf, engine):
    from mediafactory.api.app import create_app
    from mediafactory.auth import service
    from mediafactory.auth.passwords import hash_password
    from mediafactory.db.models import User

    service.reset_rate_limits()
    with sf() as s:
        s.add(User(email="run@example.com", password_hash=hash_password("correct horse battery"), role="editor"))
        c = SourceConnector(name="f", adapter="rss", params={"url": "https://example.com/f"})
        s.add(c)
        s.commit()
        cid = c.id
    try:
        client = TestClient(create_app())
        login(client, email="run@example.com")
        with sf() as holder:
            holder.get(SourceConnector, cid, with_for_update=True)  # the poller is running it
            r = client.post(f"/api/sources/{cid}/run", headers=csrf_headers(client))
            holder.rollback()
        assert r.status_code == 409 and "already" in r.json()["detail"]
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM audit_logs; DELETE FROM users WHERE email='run@example.com'"))
