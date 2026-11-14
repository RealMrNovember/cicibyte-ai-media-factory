"""Per-host request spacing and 429 cooldown, in memory and shared through the database."""

from datetime import timedelta

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from mediafactory.core.net import FetchError, SafeFetcher
from mediafactory.core.throttle import DbHostThrottle, MemoryHostThrottle, parse_retry_after
from mediafactory.db.base import utcnow
from tests.core.test_net import resolver_for


def fetch_with(handler, throttle, sleep=lambda s: None):
    return SafeFetcher(transport=httpx.MockTransport(handler), resolver=resolver_for({}), throttle=throttle, sleep=sleep)


def test_parse_retry_after():
    assert parse_retry_after("30") == 30
    assert parse_retry_after(None) == 60  # default when missing
    assert parse_retry_after("garbage") == 60
    assert parse_retry_after("999999") == 3600  # capped
    future = (utcnow() + timedelta(seconds=120)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    assert 100 <= parse_retry_after(future) <= 121


def test_429_sets_host_cooldown_and_next_call_short_circuits():
    calls = []

    def handler(request):
        calls.append(request.url.host)
        return httpx.Response(429, headers={"Retry-After": "120"})

    f = fetch_with(handler, MemoryHostThrottle())
    with pytest.raises(FetchError) as first:
        f.get("https://www.reddit.com/r/x/.rss")
    assert first.value.status == 429 and first.value.retryable
    with pytest.raises(FetchError) as second:
        f.get("https://www.reddit.com/r/y/.rss")
    assert second.value.status == 429 and "cooling down" in str(second.value)
    assert calls == ["www.reddit.com"]  # the second request never left the process
    # other hosts are not affected:
    ok = fetch_with(lambda r: httpx.Response(200, text="x"), f.throttle).get("https://example.com/")
    assert ok.status == 200


def test_reddit_spacing_is_longer():
    t = MemoryHostThrottle()
    assert t.interval_for("www.reddit.com") >= 5 and t.interval_for("example.com") == 2


@pytest.fixture
def factory(engine):
    def wipe():
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE host_rate_limits"))

    wipe()
    yield sessionmaker(bind=engine, expire_on_commit=False)
    wipe()


def test_db_throttle_spacing_shared_between_processes(factory):
    slept = []
    a = DbHostThrottle(factory, sleep=slept.append)
    b = DbHostThrottle(factory, sleep=slept.append)  # e.g. the API process
    a.acquire("example.com")
    b.acquire("example.com")
    assert len(slept) == 1 and 1.5 < slept[0] <= 2.0


def test_db_throttle_cooldown_shared_between_processes(factory):
    a = DbHostThrottle(factory, sleep=lambda s: None)
    b = DbHostThrottle(factory, sleep=lambda s: None)
    a.penalize("www.reddit.com", 300)
    with pytest.raises(FetchError) as e:
        b.acquire("www.reddit.com")
    assert e.value.status == 429
    b.acquire("example.com")  # unaffected
