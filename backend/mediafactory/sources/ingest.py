"""Store fetched items: normalize, deduplicate by canonical URL and content hash, detect updates."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mediafactory.db.base import utcnow
from mediafactory.db.models import SourceConnector, SourceItem, SourceRightsRecord
from mediafactory.sources.adapters import RawItem
from mediafactory.sources.text import content_hash, normalize_text, strip_html
from mediafactory.sources.urls import canonical_url

MIN_CHARS = 50
REVIEWED_STATUSES = ("rejected", "archived", "queued", "used")
RIGHTS_KEPT_ON_CHANGE = ("unknown", "user_owned", "restricted")


@dataclass
class IngestResult:
    new: int = 0
    updated: int = 0
    duplicates: int = 0
    skipped: int = 0
    item_ids: list[int] | None = None
    error: str | None = None

    def as_dict(self) -> dict:
        return {
            "new": self.new, "updated": self.updated, "duplicates": self.duplicates, "skipped": self.skipped,
            "error": self.error,
        }  # fmt: skip


def _find(session: Session, *, url: str | None = None, digest: str | None = None) -> SourceItem | None:
    if url is not None:
        return session.scalar(select(SourceItem).where(SourceItem.canonical_url == url))
    return session.scalar(select(SourceItem).where(SourceItem.content_hash == digest))


def store_items(
    session: Session,
    connector: SourceConnector | None,
    items: list[RawItem],
    *,
    source_type: str,
    rights_status: str | None = None,
    actor_id: int | None = None,
    attribution_required: bool = False,
) -> IngestResult:
    result = IngestResult(item_ids=[])
    rights = rights_status or (connector.default_rights if connector else None) or "unknown"
    for raw in items:
        text = normalize_text(raw.text)
        if len(text) < MIN_CHARS:
            result.skipped += 1
            continue
        url = canonical_url(raw.url) if raw.url else None
        if url and len(url) > 2000:  # longer than the column allows: keep the story, drop the link
            url = None
        digest = content_hash(text)

        existing = _find(session, url=url) if url else None
        if existing is not None:
            result.item_ids.append(existing.id)
            if existing.content_hash == digest:
                result.duplicates += 1
                continue
            same_source = connector is not None and existing.source_id == connector.id
            twin = _find(session, digest=digest)
            if not same_source or (twin is not None and twin.id != existing.id):
                # Only the source that created an item may update it; anything else is a duplicate.
                result.duplicates += 1
                continue
            _apply_update(session, existing, raw, text, digest)
            result.updated += 1
            continue

        twin = _find(session, digest=digest)
        if twin is not None:
            result.duplicates += 1
            result.item_ids.append(twin.id)
            continue

        item = SourceItem(
            source_id=connector.id if connector else None,
            source_type=source_type,
            external_id=(raw.external_id or None) and raw.external_id[:300],
            canonical_url=url,
            title=strip_html(raw.title)[:500],
            author=(raw.author or None) and raw.author[:200],
            published_at=raw.published_at,
            fetched_at=utcnow(),
            raw_text=raw.text,
            normalized_text=text,
            language=raw.language or (connector.default_language if connector else None),
            content_hash=digest,
            revision=1,
            rights_status=rights,
            attribution_required=attribution_required,
            processing_status="discovered",
            meta=dict(raw.meta or {}),
        )
        try:
            with session.begin_nested():  # another process may insert the same URL/text concurrently
                session.add(item)
                session.flush()
        except IntegrityError:
            result.duplicates += 1
            winner = _find(session, url=url) if url else _find(session, digest=digest)
            if winner is not None:
                result.item_ids.append(winner.id)
            continue
        session.add(SourceRightsRecord(item_id=item.id, from_status=None, to_status=rights, note="ingest", actor_id=actor_id))
        result.new += 1
        result.item_ids.append(item.id)
    session.flush()
    return result


def _apply_update(session: Session, item: SourceItem, raw: RawItem, text: str, digest: str) -> None:
    item.raw_text, item.normalized_text, item.content_hash = raw.text, text, digest
    item.title = strip_html(raw.title)[:500] or item.title
    item.revision += 1
    meta = {**(item.meta or {}), "updated_at": utcnow().isoformat()}
    if item.processing_status in REVIEWED_STATUSES:
        meta["changed_after_review"] = True  # keep the user's/pipeline's decision, flag the change
    else:
        item.processing_status = "updated"
    item.meta = meta
    if item.rights_status not in RIGHTS_KEPT_ON_CHANGE:
        # A grant covered the old text, not this one.
        session.add(SourceRightsRecord(
            item_id=item.id, from_status=item.rights_status, to_status="unknown",
            note="source text changed; rights must be checked again",
        ))  # fmt: skip
        item.rights_status = "unknown"
