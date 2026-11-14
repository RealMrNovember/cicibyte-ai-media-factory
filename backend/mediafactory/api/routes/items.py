from collections.abc import Iterator
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_user
from mediafactory.audit.service import record_audit
from mediafactory.core.config import get_settings
from mediafactory.core.net import SafeFetcher
from mediafactory.db.models import SourceItem, SourceRightsRecord, User
from mediafactory.db.models.sources import RIGHTS_STATUSES
from mediafactory.sources.adapters import RawItem
from mediafactory.sources.ingest import store_items
from mediafactory.sources.manual import MAX_UPLOAD_BYTES, ManualInputError, extract_file_text, fetch_url_item

router = APIRouter(prefix="/api/items", tags=["items"])

RightsStatus = Literal["unknown", "user_owned", "licensed", "permission_granted", "public_domain", "restricted"]
assert set(RightsStatus.__args__) == set(RIGHTS_STATUSES)  # keep the API enum in sync with the DB constraint


def get_fetcher() -> Iterator[SafeFetcher]:
    from mediafactory.core.throttle import DbHostThrottle
    from mediafactory.db.session import SessionLocal

    # Shared with the worker through the database, so both processes respect spacing and 429 cooldowns.
    fetcher = SafeFetcher(allowlist=get_settings().fetch_allowlist, throttle=DbHostThrottle(SessionLocal))
    try:
        yield fetcher
    finally:
        fetcher.close()


def item_out(item: SourceItem, *, full: bool = False) -> dict:
    text = item.normalized_text or ""
    return {
        "id": item.id,
        "source_id": item.source_id,
        "source_type": item.source_type,
        "title": item.title,
        "author": item.author,
        "canonical_url": item.canonical_url,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "fetched_at": item.fetched_at.isoformat() if item.fetched_at else None,
        "language": item.language,
        "rights_status": item.rights_status,
        "attribution_required": item.attribution_required,
        "processing_status": item.processing_status,
        "revision": item.revision,
        "chars": len(text),
        "text": text if full else text[:400],
    }


def _get_item(db: Session, iid: int) -> SourceItem:
    item = db.get(SourceItem, iid)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item


@router.get("")
def list_items(
    status: str | None = None,
    rights: str | None = None,
    source_id: int | None = None,
    q: str | None = Query(default=None, max_length=200),
    language: str | None = Query(default=None, max_length=8),
    limit: int = Query(50, ge=1, le=200),
    before_id: int | None = None,
    db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
) -> dict:
    query = select(SourceItem).order_by(SourceItem.id.desc()).limit(limit)
    if language == "en":  # older items without a language were English sources
        query = query.where(or_(SourceItem.language == "en", SourceItem.language.is_(None)))
    elif language:
        query = query.where(SourceItem.language == language)
    if status:
        query = query.where(SourceItem.processing_status == status)
    if rights:
        query = query.where(SourceItem.rights_status == rights)
    if source_id is not None:
        query = query.where(SourceItem.source_id == source_id)
    if q:
        pattern = f"%{q}%"
        query = query.where(or_(SourceItem.title.ilike(pattern), SourceItem.normalized_text.ilike(pattern)))
    if before_id is not None:
        query = query.where(SourceItem.id < before_id)
    return {"items": [item_out(i) for i in db.scalars(query).all()]}


@router.get("/{iid}")
def get_item(iid: int, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    item = _get_item(db, iid)
    history = db.scalars(
        select(SourceRightsRecord).where(SourceRightsRecord.item_id == iid).order_by(SourceRightsRecord.id)
    ).all()
    return {
        "item": item_out(item, full=True),
        "rights_history": [
            {"from_status": r.from_status, "to_status": r.to_status, "note": r.note, "actor_id": r.actor_id,
             "at": r.at.isoformat()}  # fmt: skip
            for r in history
        ],
    }


class StatusIn(BaseModel):
    processing_status: Literal["discovered", "rejected", "archived"]


@router.patch("/{iid}")
def update_item_status(
    iid: int, body: StatusIn, request: Request, db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
) -> dict:  # fmt: skip
    item = _get_item(db, iid)
    previous = item.processing_status
    item.processing_status = body.processing_status
    record_audit(
        db, actor_id=user.id, action="item.status", target_type="source_item", target_id=str(iid),
        details={"from": previous, "to": body.processing_status}, ip=client_ip(request),
    )  # fmt: skip
    return {"item": item_out(item)}


class RightsIn(BaseModel):
    rights_status: RightsStatus
    note: str | None = Field(default=None, max_length=1000)
    attribution_required: bool | None = None


@router.post("/{iid}/rights")
def change_rights(
    iid: int, body: RightsIn, request: Request, db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
) -> dict:  # fmt: skip
    item = _get_item(db, iid)
    previous = item.rights_status
    item.rights_status = body.rights_status
    if body.attribution_required is not None:
        item.attribution_required = body.attribution_required
    db.add(SourceRightsRecord(item_id=iid, from_status=previous, to_status=body.rights_status, note=body.note,
                              actor_id=user.id))  # fmt: skip
    record_audit(
        db, actor_id=user.id, action="item.rights", target_type="source_item", target_id=str(iid),
        details={"from": previous, "to": body.rights_status, "note": body.note}, ip=client_ip(request),
    )  # fmt: skip
    db.flush()
    return {"item": item_out(item)}


class ManualIn(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    text: str | None = Field(default=None, max_length=500_000)
    url: str | None = Field(default=None, max_length=2000)
    rights_status: RightsStatus = "unknown"
    language: str | None = Field(default=None, max_length=8)
    attribution_required: bool = False
    note: str | None = Field(default=None, max_length=1000)


def _store_manual(
    db: Session, raw: RawItem, *, user: User, rights: str, attribution: bool, note: str | None, ip: str | None,
    response: Response,
) -> dict:  # fmt: skip
    result = store_items(
        db, None, [raw], source_type="manual", rights_status=rights, actor_id=user.id, attribution_required=attribution
    )
    if result.skipped:
        raise HTTPException(status_code=422, detail="the text is too short (at least 50 characters)")
    item = db.get(SourceItem, result.item_ids[0])
    if result.duplicates:
        response.status_code = 200
        return {"item": item_out(item), "duplicate": True}
    record_audit(
        db, actor_id=user.id, action="item.manual", target_type="source_item", target_id=str(item.id),
        details={"rights_status": rights, "note": note, "url": raw.url}, ip=ip,
    )  # fmt: skip
    response.status_code = 201
    return {"item": item_out(item), "duplicate": False}


@router.post("/manual", status_code=201)
def create_manual(
    body: ManualIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
    fetcher: SafeFetcher = Depends(get_fetcher),
) -> dict:
    if not (body.text and body.text.strip()) and not (body.url and body.url.strip()):
        raise HTTPException(status_code=422, detail="provide 'text' or 'url'")
    try:
        if body.text and body.text.strip():
            raw = RawItem(external_id="", url=body.url or None, title=body.title or "", text=body.text)
        else:
            raw = fetch_url_item(body.url, fetcher)
            if body.title:
                raw.title = body.title
    except ManualInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    raw.language = body.language or raw.language
    return _store_manual(
        db, raw, user=user, rights=body.rights_status, attribution=body.attribution_required, note=body.note,
        ip=client_ip(request), response=response,
    )  # fmt: skip


class AIStoryIn(BaseModel):
    topic: str = Field(default="", max_length=500)
    language: Literal["en", "tr"] = "tr"
    words: int = Field(default=600, ge=150, le=1500)


@router.post("/ai-story", status_code=201)
def create_ai_story(
    body: AIStoryIn, request: Request, response: Response, db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
) -> dict:  # fmt: skip
    """The connected AI writes a new original story, which is added like a manual story."""
    from mediafactory.ai.router import TaskNotConfigured
    from mediafactory.pipeline.story import write_story

    try:
        story = write_story(db, body.topic, language=body.language, words=body.words)
    except TaskNotConfigured:
        raise HTTPException(status_code=409, detail="no AI is set up for the 'script' task (Settings)") from None
    except Exception as exc:  # provider down, bad output…
        raise HTTPException(status_code=502, detail=f"AI could not write the story: {exc}") from None
    raw = RawItem(external_id="", url=None, title=story["title"], text=story["story"], language=body.language)
    return _store_manual(db, raw, user=user, rights="user_owned", attribution=False,
                         note=f"written by AI ({story['model']}) from topic: {body.topic[:200]}",
                         ip=client_ip(request), response=response)  # fmt: skip


@router.post("/manual/upload", status_code=201)
def upload_manual(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    rights_status: RightsStatus = Form("unknown"),
    title: str | None = Form(None),
    language: str | None = Form(None),
    attribution_required: bool = Form(False),
    note: str | None = Form(None),
    db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
) -> dict:
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=422, detail="file is larger than 10 MB")
    try:
        text = extract_file_text(file.filename or "", data)
    except ManualInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    name = (file.filename or "upload").rsplit(".", 1)[0]
    raw = RawItem(external_id="", url=None, title=title or name, text=text, language=language)
    return _store_manual(
        db, raw, user=user, rights=rights_status, attribution=attribution_required, note=note,
        ip=client_ip(request), response=response,
    )  # fmt: skip
