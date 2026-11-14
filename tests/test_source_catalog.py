from mediafactory.sources.adapters import get_adapter
from mediafactory.sources.catalog import CATALOG, CATEGORIES
from mediafactory.sources.feeds import parse_feed

H = {"X-MF-Client": "1"}


def test_every_catalog_entry_is_valid():
    langs = {s.language for s in CATALOG}
    assert langs == {"en", "tr"}
    for s in CATALOG:
        assert s.category in CATEGORIES
        get_adapter(s.adapter).validate(dict(s.params))  # raises on bad params


def test_catalog_lists_and_adds_once(client):
    items = client.get("/api/sources/catalog").json()["items"]
    assert {i["language"] for i in items} == {"en", "tr"} and all(i["source_id"] is None for i in items)
    r = client.post("/api/sources/catalog/add", json={"keys": ["bbc-turkce", "r-nosleep"]}, headers=H)
    assert r.status_code == 200 and set(r.json()["added"]) == {"bbc-turkce", "r-nosleep"}
    again = client.post("/api/sources/catalog/add", json={"keys": ["bbc-turkce"]}, headers=H).json()
    assert again == {"added": [], "skipped": ["bbc-turkce"]}
    srcs = {s["name"]: s for s in client.get("/api/sources").json()["items"]}
    assert srcs["BBC Türkçe"]["default_language"] == "tr" and srcs["r/nosleep"]["poll_interval_min"] == 360
    marked = {i["key"]: i["source_id"] for i in client.get("/api/sources/catalog").json()["items"]}
    assert marked["bbc-turkce"] and marked["r-nosleep"] and marked["dw-turkce"] is None


def test_unknown_key_rejected(client):
    assert client.post("/api/sources/catalog/add", json={"keys": ["nope"]}, headers=H).status_code == 422


RDF = b"""<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/">
 <channel rdf:about="https://dw.example/"><title>DW</title></channel>
 <item rdf:about="https://dw.example/a1"><title>Haber bir</title><link>https://dw.example/a1</link>
  <description>Kisa ozet</description><dc:date>2026-11-14T08:00:00Z</dc:date></item>
</rdf:RDF>"""


def test_rss1_rdf_feed_parsed():
    [e] = parse_feed(RDF)
    assert e.title == "Haber bir" and e.link == "https://dw.example/a1" and e.summary_html == "Kisa ozet"
    assert e.published_at is not None


class _FakeFetcher:
    def __init__(self, pages, allowed=True):
        self.pages, self.allowed, self.calls = pages, allowed, []

    def robots_allowed(self, url):
        return self.allowed

    def get(self, url, headers=None):
        from types import SimpleNamespace

        self.calls.append(url)
        body = self.pages[url]
        return SimpleNamespace(content=body.encode(), text=body, url=url)


FEED = """<rss version="2.0"><channel><title>t</title>
<item><title>Short one</title><link>https://news.example/a</link><guid>a</guid><description>Only a teaser.</description></item>
</channel></rss>"""
ARTICLE = "<html><body><article><h1>Short one</h1>" + "<p>" + "The full story goes on and on with detail. " * 40 + "</p></article></body></html>"


def test_rss_full_text_replaces_teaser_with_article():
    from mediafactory.sources.adapters.base import FetchContext

    a = get_adapter("rss")
    params = a.validate({"url": "https://news.example/feed", "full_text": True, "min_chars": 400})
    f = _FakeFetcher({"https://news.example/feed": FEED, "https://news.example/a": ARTICLE})
    [item] = a.fetch(params, FetchContext(fetcher=f))
    assert "full story goes on" in item.text and len(item.text) > 1000


def test_rss_full_text_respects_robots_and_min_chars():
    from mediafactory.sources.adapters.base import FetchContext

    a = get_adapter("rss")
    params = a.validate({"url": "https://news.example/feed", "full_text": True, "min_chars": 400})
    f = _FakeFetcher({"https://news.example/feed": FEED, "https://news.example/a": ARTICLE}, allowed=False)
    assert a.fetch(params, FetchContext(fetcher=f)) == []  # teaser too short and the page may not be fetched
    assert f.calls == ["https://news.example/feed"]


def test_items_language_filter_treats_missing_as_english(client, db):
    from mediafactory.db.models import SourceItem

    for n, lang in enumerate(["tr", "en", None]):
        db.add(SourceItem(source_type="manual", title=f"s{n}", raw_text="x", normalized_text="x", content_hash=f"lang{n}", language=lang))
    db.flush()
    tr = [i["title"] for i in client.get("/api/items?language=tr").json()["items"]]
    en = [i["title"] for i in client.get("/api/items?language=en").json()["items"]]
    assert tr == ["s0"] and sorted(en) == ["s1", "s2"]
