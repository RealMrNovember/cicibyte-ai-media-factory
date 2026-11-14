from mediafactory.db.models import SourceConnector, SourceItem

H = {"X-MF-Client": "1"}


def _setup(db):
    horror = SourceConnector(name="r/nosleep", adapter="reddit_rss", params={"subreddit": "nosleep"}, default_language="en")
    science = SourceConnector(name="Evrim Ağacı", adapter="rss", params={"url": "https://evrimagaci.org/rss.xml"},
                              default_language="tr")  # fmt: skip
    custom = SourceConnector(name="My blog", adapter="rss", params={"url": "https://blog.example/feed"})
    db.add_all([horror, science, custom])
    db.flush()
    rows = [(horror.id, "reddit_rss", "en", "h1"), (horror.id, "reddit_rss", "en", "h2"), (science.id, "rss", "tr", "s1"),
            (custom.id, "rss", "en", "c1"), (None, "manual", "tr", "m1")]  # fmt: skip
    for sid, st, lang, key in rows:
        db.add(SourceItem(source_id=sid, source_type=st, title=key, raw_text="x", normalized_text="x" * 50,
                          content_hash=key, language=lang))  # fmt: skip
    db.flush()
    return horror, science, custom


def test_items_carry_topic_and_source_name(client, db):
    horror, science, _ = _setup(db)
    items = {i["title"]: i for i in client.get("/api/items?limit=50").json()["items"]}
    assert items["h1"]["category"] == "horror" and items["h1"]["source_name"] == "r/nosleep"
    assert items["s1"]["category"] == "science"
    assert items["c1"]["category"] == "other" and items["m1"]["category"] == "manual"


def test_filter_by_topic_and_source(client, db):
    horror, science, custom = _setup(db)
    titles = lambda q: sorted(i["title"] for i in client.get(f"/api/items?limit=50&{q}").json()["items"])  # noqa: E731
    assert titles("category=horror") == ["h1", "h2"]
    assert titles("category=manual") == ["m1"]
    assert titles("category=other") == ["c1"]
    assert titles(f"source_id={science.id}") == ["s1"]
    assert titles("category=horror&language=tr") == []


def test_topics_endpoint_counts(client, db):
    _setup(db)
    data = client.get("/api/items/topics").json()
    counts = {t["key"]: t["count"] for t in data["topics"]}
    assert counts == {"horror": 2, "science": 1, "other": 1, "manual": 1}
    tr = {t["key"]: t["count"] for t in client.get("/api/items/topics?language=tr").json()["topics"]}
    assert tr == {"science": 1, "manual": 1}
    assert {s["name"]: s["count"] for s in data["sources"]}["r/nosleep"] == 2
