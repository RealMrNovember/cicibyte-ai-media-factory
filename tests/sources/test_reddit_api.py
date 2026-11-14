import base64

import httpx
import pytest

from mediafactory.sources.adapters import AdapterError, FetchContext, get_adapter
from mediafactory.sources.adapters import reddit as reddit_mod
from tests.sources.helpers import LONG, make_fetcher

CREDS = {"client_id": "cid", "client_secret": "csecret"}


@pytest.fixture(autouse=True)
def clear_tokens():
    reddit_mod.reset_token_cache()
    yield
    reddit_mod.reset_token_cache()


def post(pid, title, text=LONG, score=50, nsfw=False, stickied=False):
    return {"kind": "t3", "data": {
        "id": pid, "title": title, "selftext": text, "score": score, "over_18": nsfw, "stickied": stickied,
        "permalink": f"/r/nosleep/comments/{pid}/slug/", "author": "writer", "created_utc": 1794600000,
    }}  # fmt: skip


def handler_factory(calls, listing=None, token_status=200, listing_status=200):
    def handler(request):
        if request.url.host == "www.reddit.com" and request.url.path == "/api/v1/access_token":
            calls.append("token")
            assert request.method == "POST"
            assert request.headers["authorization"] == "Basic " + base64.b64encode(b"cid:csecret").decode()
            assert b"grant_type=client_credentials" in request.content
            if token_status != 200:
                return httpx.Response(token_status, json={"error": "invalid_grant"})
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600, "token_type": "bearer"})
        calls.append(str(request.url))
        assert request.headers["authorization"] == "Bearer tok"
        if listing_status != 200:
            return httpx.Response(listing_status, json={})
        return httpx.Response(200, json={"data": {"children": listing or []}})

    return handler


def run(params, handler, creds=CREDS):
    a = get_adapter("reddit")
    return a.fetch(a.validate(params), FetchContext(fetcher=make_fetcher(handler), credentials=creds))


def test_not_configured_error():
    with pytest.raises(AdapterError) as e:
        run({"subreddit": "nosleep"}, handler_factory([]), creds=None)
    assert not e.value.retryable and "not configured" in str(e.value)


def test_token_then_listing_filters_score_nsfw_length():
    calls = []
    listing = [
        post("a", "Good one"),
        post("b", "Low score", score=1),
        post("c", "Adult", nsfw=True),
        post("d", "Short", text="tiny"),
        post("e", "Pinned rules", stickied=True),
    ]
    items = run({"subreddit": "nosleep", "sort": "top", "time": "week", "min_score": 10}, handler_factory(calls, listing))
    assert calls[0] == "token"
    assert calls[1] == "https://oauth.reddit.com/r/nosleep/top?t=week&limit=25&raw_json=1"
    assert [i.title for i in items] == ["Good one"]
    item = items[0]
    assert item.url == "https://www.reddit.com/r/nosleep/comments/a/slug/" and item.external_id == "t3_a"
    assert item.author == "writer" and item.meta["score"] == 50 and item.published_at.year == 2026


def test_token_cached_until_expiry(monkeypatch):
    now = {"t": 1000.0}
    monkeypatch.setattr(reddit_mod, "_clock", lambda: now["t"])
    calls = []
    h = handler_factory(calls, [post("a", "A")])
    run({"subreddit": "nosleep"}, h)
    run({"subreddit": "nosleep"}, h)
    assert calls.count("token") == 1
    now["t"] += 3700
    run({"subreddit": "nosleep"}, h)
    assert calls.count("token") == 2


def test_401_not_retryable():
    with pytest.raises(AdapterError) as e:
        run({"subreddit": "nosleep"}, handler_factory([], token_status=401))
    assert not e.value.retryable


def test_listing_401_clears_token_and_is_not_retryable():
    calls = []
    with pytest.raises(AdapterError) as e:
        run({"subreddit": "nosleep"}, handler_factory(calls, listing_status=401))
    assert not e.value.retryable
    run({"subreddit": "nosleep"}, handler_factory(calls, [post("a", "A")]))
    assert calls.count("token") == 2


def test_429_retryable():
    with pytest.raises(AdapterError) as e:
        run({"subreddit": "nosleep"}, handler_factory([], listing_status=429))
    assert e.value.retryable


def test_reddit_rss_source_uses_official_api_when_keys_are_set(db):
    from mediafactory.db.models import SourceConnector
    from mediafactory.sources.credentials import set_reddit_credentials
    from mediafactory.sources.poller import run_source

    set_reddit_credentials(db, "cid", "csecret")
    c = SourceConnector(name="r/nosleep", adapter="reddit_rss", params={"subreddit": "nosleep", "sort": "top", "time": "week"})
    db.add(c)
    db.flush()
    calls = []
    result = run_source(db, c, fetcher=make_fetcher(handler_factory(calls, listing=[post("z1", "Via the API")])))
    assert result.error is None and result.new == 1
    assert calls[0] == "token" and "oauth.reddit.com" in calls[1]
