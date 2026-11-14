"""Store fetched items: normalize, deduplicate by canonical URL and content hash, detect updates."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from mediafactory.db.base import utcnow
from mediafactory.db.models import SourceConnector, SourceItem, SourceRightsRecord
from mediafactory.sources.adapters import RawItem
from mediafactory.sources.text import content_hash, normalize_text, strip_html
from mediafactory.sources.urls import canonical_url

MIN_CHARS = 50


@dataclass
class IngestResult:
    new: int = 0
    updated: int = 0
    duplicates: int = 0
    skipped: int = 0
    item_ids: list[int] | None = None

    def as_dict(self) -> dict:
        return {"new": self.new, "updated": self.updated, "duplicates": self.duplicates, "skipped": self.skipped}


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
        digest = content_hash(text)

        existing = _find(session, url=url) if url else None
        if existing is not None:
            result.item_ids.append(existing.id)
            if existing.content_hash == digest:
                result.duplicates += 1
                continue
            twin = _find(session, digest=digest)
            if twin is not None and twin.id != existing.id:
                result.duplicates += 1  # new text equals another stored item: nothing new to keep
                continue
            existing.raw_text, existing.normalized_text, existing.content_hash = raw.text, text, digest
            existing.title = strip_html(raw.title)[:500] or existing.title
            existing.revision += 1
            existing.processing_status = "updated"
            existing.meta = {**(existing.meta or {}), "updated_at": utcnow().isoformat()}
            result.updated += 1
            continue

        if _find(session, digest=digest) is not None:
            result.duplicates += 1
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
        session.add(item)
        session.flush()
        session.add(SourceRightsRecord(item_id=item.id, from_status=None, to_status=rights, note="ingest", actor_id=actor_id))
        result.new += 1
        result.item_ids.append(item.id)
    session.flush()
    return result
