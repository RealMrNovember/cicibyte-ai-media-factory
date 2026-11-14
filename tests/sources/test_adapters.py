from html import escape

import httpx
import pytest

from mediafactory.sources.adapters import AdapterError, FetchContext, get_adapter
from tests.sources.helpers import LONG, make_fetcher, reddit_atom

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>News one</title><link>https://example.com/1</link><guid>g1</guid><description>Body one here</description></item>
<item><title>News two</title><link>https://example.com/2</link><guid>g2</guid><description>Body two here</description></item>
</channel></rss>"""


def ctx(handler):
    return FetchContext(fetcher=make_fetcher(handler))


def test_rss_adapter_returns_items():
    a = get_adapter("rss")
    params = a.validate({"url": "https://example.com/feed.xml"})
    items = a.fetch(params, ctx(lambda r: httpx.Response(200, content=RSS)))
    assert [i.title for i in items] == ["News one", "News two"]
    assert items[0].url == "https://example.com/1" and items[0].external_id == "g1" and items[0].text == "Body one here"


def test_rss_validate_rejects_bad_url():
    with pytest.raises(ValueError):
        get_adapter("rss").validate({"url": "ftp://x"})


def test_reddit_rss_builds_url_and_filters_short_and_nsfw():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(
            200,
            content=reddit_atom(
                [
                    ("a1", "A long story", escape(f"<p>{LONG}</p>")),
                    ("a2", "Too short", escape("<p>tiny</p>")),
                    ("a3", "Spicy [NSFW] tale", escape(f"<p>{LONG}</p>")),
                ]
            ),
        )

    a = get_adapter("reddit_rss")
    params = a.validate({"subreddit": "nosleep", "sort": "top", "time": "week"})
    items = a.fetch(params, ctx(handler))
    assert seen["url"] == "https://www.reddit.com/r/nosleep/top/.rss?t=week"
    assert [i.title for i in items] == ["A long story"]
    assert items[0].author == "writera1" and items[0].external_id == "t3_a1"


def test_reddit_rss_include_nsfw_keeps_it():
    def handler(request):
        return httpx.Response(200, content=reddit_atom([("a3", "Spicy [NSFW] tale", escape(f"<p>{LONG}</p>"))]))

    a = get_adapter("reddit_rss")
    items = a.fetch(a.validate({"subreddit": "nosleep", "include_nsfw": True}), ctx(handler))
    assert len(items) == 1


def test_reddit_rss_strips_signature():
    body = escape(f"<p>{LONG}</p> submitted by /u/writer [link] [comments]")
    a = get_adapter("reddit_rss")
    items = a.fetch(a.validate({"subreddit": "nosleep"}), ctx(lambda r: httpx.Response(200, content=reddit_atom([("x", "T", body)]))))
    assert "submitted by" not in items[0].text


def test_reddit_rss_invalid_subreddit_rejected():
    a = get_adapter("reddit_rss")
    for bad in ("", "a", "no/sleep", "../etc", "x" * 30):
        with pytest.raises(ValueError):
            a.validate({"subreddit": bad})
    with pytest.raises(ValueError):
        a.validate({"subreddit": "nosleep", "sort": "random"})


def test_web_adapter_respects_robots():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        return httpx.Response(200, text="<p>" + LONG + "</p>")

    a = get_adapter("web")
    with pytest.raises(AdapterError) as e:
        a.fetch(a.validate({"url": "https://example.com/story"}), ctx(handler))
    assert not e.value.retryable and "robots" in str(e.value)


def test_web_adapter_extracts_article():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text=f"<title>Haunted</title><article><p>{LONG}</p></article>")

    a = get_adapter("web")
    (item,) = a.fetch(a.validate({"url": "https://example.com/story"}), ctx(handler))
    assert item.title == "Haunted" and "basement light" in item.text and item.url == "https://example.com/story"


def test_web_adapter_short_page_error():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text="<p>Hi</p>")

    a = get_adapter("web")
    with pytest.raises(AdapterError):
        a.fetch(a.validate({"url": "https://example.com/x"}), ctx(handler))


def test_429_is_retryable_adapter_error():
    a = get_adapter("reddit_rss")
    with pytest.raises(AdapterError) as e:
        a.fetch(a.validate({"subreddit": "nosleep"}), ctx(lambda r: httpx.Response(429)))
    assert e.value.retryable


def test_bad_feed_is_non_retryable():
    a = get_adapter("rss")
    with pytest.raises(AdapterError) as e:
        a.fetch(a.validate({"url": "https://example.com/f"}), ctx(lambda r: httpx.Response(200, text="<html/>")))
    assert not e.value.retryable


def test_unknown_adapter():
    with pytest.raises(ValueError):
        get_adapter("wattpad")
