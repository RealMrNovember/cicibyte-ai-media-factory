"""Ready-made source catalog (English and Turkish): browse and add with one click."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_user
from mediafactory.audit.service import record_audit
from mediafactory.db.base import utcnow
from mediafactory.db.models import SourceConnector, User
from mediafactory.sources.adapters import get_adapter
from mediafactory.sources.catalog import BY_KEY, CATALOG, CATEGORIES, CatalogSource

router = APIRouter(prefix="/api/sources/catalog", tags=["sources"])


def _identity(adapter: str, params: dict) -> tuple[str, str]:
    return adapter, str(params.get("subreddit") or params.get("url") or "").lower()


def _existing(db: Session) -> dict[tuple[str, str], int]:
    rows = db.scalars(select(SourceConnector).where(SourceConnector.deleted_at.is_(None)))
    return {_identity(c.adapter, c.params or {}): c.id for c in rows}


@router.get("")
def catalog(db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    have = _existing(db)
    return {
        "categories": {k: {"en": en, "tr": tr} for k, (en, tr) in CATEGORIES.items()},
        "items": [
            {"key": s.key, "name": s.name, "language": s.language, "category": s.category, "adapter": s.adapter,
             "about": {"en": s.about_en, "tr": s.about_tr}, "interval_min": s.interval_min,
             "source_id": have.get(_identity(s.adapter, s.params))}  # fmt: skip
            for s in CATALOG
        ],
    }


class AddIn(BaseModel):
    keys: list[str] = Field(min_length=1, max_length=len(CATALOG))


def _add(db: Session, s: CatalogSource, offset_s: int) -> SourceConnector:
    name, n = s.name, 2
    while db.scalar(select(SourceConnector.id).where(SourceConnector.name == name)) is not None:
        name, n = f"{s.name} ({n})", n + 1
    c = SourceConnector(
        name=name, adapter=s.adapter, params=get_adapter(s.adapter).validate(dict(s.params)), enabled=True,
        poll_interval_min=s.interval_min, default_rights="unknown", default_language=s.language,
        next_run_at=utcnow() + timedelta(seconds=offset_s),  # spread first runs so sites are not hit at once
    )  # fmt: skip
    db.add(c)
    db.flush()
    return c


@router.post("/add")
def add_from_catalog(
    body: AddIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    unknown = [k for k in body.keys if k not in BY_KEY]
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown catalog sources: {', '.join(unknown)}")
    have = _existing(db)
    added, skipped, reddit = [], [], 0
    for key in dict.fromkeys(body.keys):
        s = BY_KEY[key]
        if _identity(s.adapter, s.params) in have:
            skipped.append(key)
            continue
        offset = 90 * reddit if s.adapter.startswith("reddit") else 20 * len(added)
        reddit += s.adapter.startswith("reddit")
        c = _add(db, s, offset)
        have[_identity(c.adapter, c.params)] = c.id
        added.append(key)
    record_audit(db, actor_id=user.id, action="source.catalog_add", details={"added": added, "skipped": skipped},
                 ip=client_ip(request))  # fmt: skip
    return {"added": added, "skipped": skipped}
