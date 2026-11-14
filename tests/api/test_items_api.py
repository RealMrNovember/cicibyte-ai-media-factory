import pytest
from sqlalchemy import select

from mediafactory.db.models import AuditLog, SourceItem, SourceRightsRecord
from mediafactory.sources.adapters import RawItem
from mediafactory.sources.ingest import store_items
from tests.helpers import csrf_headers, login
from tests.sources.helpers import LONG


@pytest.fixture
def h(client, make_user):
    make_user(email="ed@example.com", role="editor")
    login(client, email="ed@example.com")
    return csrf_headers(client)


def seed(db, n=3):
    for i in range(n):
        store_items(db, None, [RawItem(external_id=str(i), url=f"https://example.com/{i}", title=f"Ghost {i}",
                                       text=f"{LONG} variant {i}")], source_type="rss")  # fmt: skip
    return [i.id for i in db.scalars(select(SourceItem).order_by(SourceItem.id)).all()]


def test_items_inbox_newest_first_and_truncated(client, h, db):
    ids = seed(db)
    items = client.get("/api/items").json()["items"]
    assert [i["id"] for i in items] == list(reversed(ids))
    assert len(items[0]["text"]) <= 400 and items[0]["chars"] > 400


def test_items_filters_and_pagination(client, h, db):
    ids = seed(db, 3)
    db.get(SourceItem, ids[0]).rights_status = "licensed"
    db.flush()
    assert [i["id"] for i in client.get("/api/items?rights=licensed").json()["items"]] == [ids[0]]
    assert [i["id"] for i in client.get("/api/items?q=Ghost 2").json()["items"]] == [ids[2]]
    page = client.get(f"/api/items?limit=1&before_id={ids[2]}").json()["items"]
    assert [i["id"] for i in page] == [ids[1]]


def test_item_detail_has_full_text_and_rights_history(client, h, db):
    (iid,) = seed(db, 1)
    body = client.get(f"/api/items/{iid}").json()
    assert body["item"]["text"].startswith("The basement") and len(body["item"]["text"]) > 400
    assert body["rights_history"][0]["to_status"] == "unknown"
    assert client.get("/api/items/999999").status_code == 404


def test_rights_change_records_history_and_audit(client, h, db):
    (iid,) = seed(db, 1)
    r = client.post(f"/api/items/{iid}/rights", json={"rights_status": "permission_granted", "note": "author agreed",
                                                      "attribution_required": True}, headers=h)  # fmt: skip
    assert r.status_code == 200 and r.json()["item"]["rights_status"] == "permission_granted"
    recs = db.scalars(select(SourceRightsRecord).where(SourceRightsRecord.item_id == iid).order_by(SourceRightsRecord.id)).all()
    assert [(x.from_status, x.to_status) for x in recs] == [(None, "unknown"), ("unknown", "permission_granted")]
    assert recs[1].actor_id is not None and recs[1].note == "author agreed"
    assert db.get(SourceItem, iid).attribution_required is True
    assert db.scalar(select(AuditLog).where(AuditLog.action == "item.rights")) is not None


def test_rights_invalid_422(client, h, db):
    (iid,) = seed(db, 1)
    assert client.post(f"/api/items/{iid}/rights", json={"rights_status": "free"}, headers=h).status_code == 422


def test_status_change(client, h, db):
    (iid,) = seed(db, 1)
    r = client.patch(f"/api/items/{iid}", json={"processing_status": "rejected"}, headers=h)
    assert r.status_code == 200 and r.json()["item"]["processing_status"] == "rejected"
    assert client.patch(f"/api/items/{iid}", json={"processing_status": "used"}, headers=h).status_code == 422
    assert db.scalar(select(AuditLog).where(AuditLog.action == "item.status")) is not None
