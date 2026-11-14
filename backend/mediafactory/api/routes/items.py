from collections.abc import Iterator
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_user
from mediafactory.audit.service import record_audit
from mediafactory.core.config import get_settings
from mediafactory.core.net import SafeFetcher
from mediafactory.db.models import SourceItem, User
from mediafactory.db.models.sources import RIGHTS_STATUSES
from mediafactory.sources.adapters import RawItem
from mediafactory.sources.ingest import store_items
from mediafactory.sources.manual import MAX_UPLOAD_BYTES, ManualInputError, extract_file_text, fetch_url_item

router = APIRouter(prefix="/api/items", tags=["items"])

RightsStatus = Literal["unknown", "user_owned", "licensed", "permission_granted", "public_domain", "restricted"]
assert set(RightsStatus.__args__) == set(RIGHTS_STATUSES)  # keep the API enum in sync with the DB constraint


def get_fetcher() -> Iterator[SafeFetcher]:
    fetcher = SafeFetcher(allowlist=get_settings().fetch_allowlist)
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
