from sqlalchemy import func, select

from mediafactory.db.models import SourceConnector, SourceItem, SourceRightsRecord
from mediafactory.sources.adapters import RawItem
from mediafactory.sources.ingest import store_items
from tests.sources.helpers import LONG


def raw(url="https://example.com/a", text=LONG, title="T", ext="e1"):
    return RawItem(external_id=ext, url=url, title=title, text=text)


def count(db):
    return db.scalar(select(func.count()).select_from(SourceItem))


def test_new_items_stored_with_unknown_rights(db):
    r = store_items(db, None, [raw()], source_type="rss")
    assert (r.new, r.updated, r.duplicates, r.skipped) == (1, 0, 0, 0)
    item = db.scalar(select(SourceItem))
    assert item.rights_status == "unknown" and item.processing_status == "discovered"
    assert item.canonical_url == "https://example.com/a" and item.revision == 1 and len(item.content_hash) == 64


def test_connector_default_rights_and_language(db):
    c = SourceConnector(name="mine", adapter="rss", params={}, default_rights="user_owned", default_language="tr")
    db.add(c)
    db.flush()
    store_items(db, c, [raw()], source_type="rss")
    item = db.scalar(select(SourceItem))
    assert item.rights_status == "user_owned" and item.language == "tr" and item.source_id == c.id


def test_same_url_same_text_is_duplicate(db):
    store_items(db, None, [raw()], source_type="rss")
    r = store_items(db, None, [raw()], source_type="rss")
    assert r.duplicates == 1 and r.new == 0 and count(db) == 1


def test_reddit_url_variants_deduplicated(db):
    a = raw(url="https://old.reddit.com/r/nosleep/comments/abc/slug/?utm_source=share")
    b = raw(url="https://www.reddit.com/r/NoSleep/comments/abc")
    r = store_items(db, None, [a, b], source_type="reddit_rss")
    assert r.new == 1 and r.duplicates == 1 and count(db) == 1


def test_same_text_different_url_is_duplicate(db):
    store_items(db, None, [raw(url="https://a.example/x")], source_type="rss")
    r = store_items(db, None, [raw(url="https://b.example/y")], source_type="rss")
    assert r.duplicates == 1 and count(db) == 1


def test_changed_text_marks_updated_and_bumps_revision(db):
    store_items(db, None, [raw()], source_type="rss")
    r = store_items(db, None, [raw(text=LONG + " An ending was added.")], source_type="rss")
    assert r.updated == 1
    item = db.scalar(select(SourceItem))
    assert item.revision == 2 and item.processing_status == "updated" and "ending" in item.normalized_text
    assert "updated_at" in item.meta


def test_too_short_skipped(db):
    r = store_items(db, None, [raw(text="tiny")], source_type="rss")
    assert r.skipped == 1 and count(db) == 0


def test_initial_rights_record_written(db):
    store_items(db, None, [raw()], source_type="manual", rights_status="licensed", actor_id=None)
    rec = db.scalar(select(SourceRightsRecord))
    assert rec.from_status is None and rec.to_status == "licensed" and rec.note == "ingest"


def test_item_without_url_dedups_by_hash(db):
    store_items(db, None, [raw(url=None)], source_type="manual")
    r = store_items(db, None, [raw(url=None)], source_type="manual")
    assert r.duplicates == 1 and count(db) == 1


def test_duplicate_returns_existing_item_id(db):
    first = store_items(db, None, [raw(url=None)], source_type="manual")
    second = store_items(db, None, [raw(url=None)], source_type="manual")
    assert second.item_ids == first.item_ids
