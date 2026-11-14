import httpx
import pytest
from sqlalchemy import select

from mediafactory.db.models import AuditLog, SourceConnector, SourceItem
from tests.helpers import csrf_headers, login
from tests.sources.helpers import LONG, make_fetcher

RSS = f"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>One</title><link>https://example.com/1</link><guid>1</guid><description>{LONG}</description></item>
</channel></rss>""".encode()

NEW = {"name": "Nosleep", "adapter": "reddit_rss", "params": {"subreddit": "nosleep", "sort": "top", "time": "week"}}


@pytest.fixture
def h(client, make_user):
    make_user(email="ed@example.com", role="editor")
    login(client, email="ed@example.com")
    return csrf_headers(client)


def test_unauthenticated_401(client):
    assert client.get("/api/sources").status_code == 401


def test_create_source_validates_params_422(client, h):
    bad = {**NEW, "params": {"subreddit": "no/sleep"}}
    r = client.post("/api/sources", json=bad, headers=h)
    assert r.status_code == 422 and "subreddit" in r.json()["detail"]
    assert client.post("/api/sources", json={**NEW, "adapter": "manual"}, headers=h).status_code == 422
    assert client.post("/api/sources", json={**NEW, "adapter": "wattpad"}, headers=h).status_code == 422


def test_editor_can_manage_sources_full_cycle(client, h, db):
    r = client.post("/api/sources", json=NEW, headers=h)
    assert r.status_code == 201
    src = r.json()
    assert src["params"] == {"subreddit": "nosleep", "sort": "top", "time": "week", "min_chars": 400,
                             "max_items": 25, "include_nsfw": False}  # fmt: skip
    assert src["enabled"] is True and src["default_rights"] == "unknown"
    assert client.post("/api/sources", json=NEW, headers=h).status_code == 409
    assert client.get("/api/auth/me").status_code == 200  # conflict did not break the session

    r = client.patch(f"/api/sources/{src['id']}", json={"enabled": False, "poll_interval_min": 120}, headers=h)
    assert r.status_code == 200 and r.json()["enabled"] is False and r.json()["poll_interval_min"] == 120
    r = client.patch(f"/api/sources/{src['id']}", json={"params": {"subreddit": "x/y"}}, headers=h)
    assert r.status_code == 422

    assert client.delete(f"/api/sources/{src['id']}", headers=h).status_code == 204
    assert client.get("/api/sources").json()["items"] == []
    listed = client.get("/api/sources?include_deleted=true").json()["items"]
    assert listed[0]["deleted"] is True
    actions = set(db.scalars(select(AuditLog.action)).all())
    assert {"source.create", "source.update", "source.delete"} <= actions


def test_run_now_returns_ingest_result(client, h, app):
    from mediafactory.api.routes.items import get_fetcher

    app.dependency_overrides[get_fetcher] = lambda: make_fetcher(lambda r: httpx.Response(200, content=RSS))
    sid = client.post("/api/sources", json={"name": "feed", "adapter": "rss", "params": {"url": "https://example.com/f"}},
                      headers=h).json()["id"]  # fmt: skip
    r = client.post(f"/api/sources/{sid}/run", headers=h)
    assert r.status_code == 200 and r.json()["new"] == 1 and r.json()["error"] is None
    again = client.post(f"/api/sources/{sid}/run", headers=h).json()
    assert again["new"] == 0 and again["duplicates"] == 1
    src = client.get("/api/sources").json()["items"][0]
    assert src["items_total"] == 1 and src["last_success_at"] is not None


def test_run_disabled_source_409(client, h):
    sid = client.post("/api/sources", json={**NEW, "enabled": False}, headers=h).json()["id"]
    assert client.post(f"/api/sources/{sid}/run", headers=h).status_code == 409


def test_delete_keeps_items(client, h, db):
    sid = client.post("/api/sources", json=NEW, headers=h).json()["id"]
    item = SourceItem(source_id=sid, source_type="reddit_rss", title="t", raw_text=LONG, normalized_text=LONG,
                      content_hash="f" * 64)  # fmt: skip
    db.add(item)
    db.flush()
    assert client.delete(f"/api/sources/{sid}", headers=h).status_code == 204
    db.flush()
    db.expire_all()
    assert db.get(SourceItem, item.id) is not None and db.get(SourceConnector, sid).deleted_at is not None
