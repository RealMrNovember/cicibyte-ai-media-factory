import threading
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import sessionmaker

from mediafactory.db.base import utcnow
from mediafactory.db.models import SourceConnector, SourceItem
from mediafactory.sources.poller import poll_due, run_source, schedule_next
from tests.sources.helpers import LONG, make_fetcher

RSS = f"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>One</title><link>https://example.com/1</link><guid>1</guid><description>{LONG}</description></item>
</channel></rss>""".encode()


@pytest.fixture
def sf(engine):
    def wipe():
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE source_rights_records, source_items, source_connectors RESTART IDENTITY CASCADE"))

    wipe()
    yield sessionmaker(bind=engine, expire_on_commit=False)
    wipe()


def add(sf, **kw):
    base = dict(name="feed", adapter="rss", params={"url": "https://example.com/feed"}, poll_interval_min=60)
    with sf() as s:
        c = SourceConnector(**{**base, **kw})
        s.add(c)
        s.commit()
        return c.id


def ok_fetcher():
    return make_fetcher(lambda r: httpx.Response(200, content=RSS))


def get(sf, cid):
    with sf() as s:
        return s.get(SourceConnector, cid)


def test_due_source_runs_and_schedules_next(sf):
    cid = add(sf)
    assert poll_due(sf, fetcher=ok_fetcher()) == 1
    c = get(sf, cid)
    assert c.items_total == 1 and c.last_success_at is not None and c.last_error is None
    assert c.next_run_at > utcnow() + timedelta(minutes=59)
    assert poll_due(sf, fetcher=ok_fetcher()) == 0  # not due again yet


def test_disabled_and_deleted_sources_skipped(sf):
    add(sf, name="off", enabled=False)
    add(sf, name="gone", deleted_at=utcnow())
    assert poll_due(sf, fetcher=ok_fetcher()) == 0


def test_failure_backs_off_exponentially_capped_24h():
    c = SourceConnector(name="x", adapter="rss", params={}, poll_interval_min=60, consecutive_failures=0)
    before = utcnow()
    for failures, minutes in ((1, 120), (2, 240), (3, 480), (10, 24 * 60)):
        c.consecutive_failures = failures
        schedule_next(c, failed=True)
        delta = c.next_run_at - before
        assert timedelta(minutes=minutes) <= delta < timedelta(minutes=minutes, seconds=30), (failures, delta)


def test_failed_run_records_error_and_failures(sf):
    cid = add(sf)
    poll_due(sf, fetcher=make_fetcher(lambda r: httpx.Response(429)))
    c = get(sf, cid)
    assert "429" in c.last_error and c.consecutive_failures == 1
    assert c.next_run_at > utcnow() + timedelta(minutes=119)


def test_one_failing_source_does_not_block_others(sf):
    add(sf, name="bad", params={"url": "https://bad.example/feed"})
    good = add(sf, name="good", params={"url": "https://good.example/feed"})

    def handler(request):
        if request.url.host == "bad.example":
            raise RuntimeError("boom inside transport")
        return httpx.Response(200, content=RSS)

    assert poll_due(sf, fetcher=make_fetcher(handler)) == 2
    assert get(sf, good).items_total == 1


def test_invalid_params_recorded_as_error(sf):
    cid = add(sf, params={"url": "not a url"})
    poll_due(sf, fetcher=ok_fetcher())
    assert "url" in get(sf, cid).last_error


def test_two_pollers_do_not_run_same_source(sf):
    add(sf)
    gate = threading.Barrier(2)
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(200, content=RSS)

    def worker():
        gate.wait()
        poll_due(sf, fetcher=make_fetcher(handler))

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(calls) == 1


def test_run_source_reports_result(sf):
    cid = add(sf)
    with sf() as s:
        result = run_source(s, s.get(SourceConnector, cid), fetcher=ok_fetcher())
        s.commit()
    assert result.new == 1 and result.error is None
    with sf() as s:
        assert s.scalar(select(func.count()).select_from(SourceItem)) == 1


def test_reddit_api_without_credentials_sets_error(sf):
    cid = add(sf, name="r", adapter="reddit", params={"subreddit": "nosleep"})
    poll_due(sf, fetcher=ok_fetcher())
    assert "not configured" in get(sf, cid).last_error
