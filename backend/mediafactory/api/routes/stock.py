"""Stock clips for the background library: Coverr search/import (your API key) and Mixkit import by link."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_user
from mediafactory.audit.service import record_audit
from mediafactory.core.config import get_settings
from mediafactory.db.models import User
from mediafactory.pipeline import backgrounds as lib
from mediafactory.pipeline import stock

router = APIRouter(prefix="/api/stock", tags=["stock"])


class KeyIn(BaseModel):
    key: str = Field(default="", max_length=200, description="empty removes the key")


class ImportIn(BaseModel):
    tags: list[str] = Field(default_factory=list, max_length=10)


class MixkitIn(ImportIn):
    url: str = Field(max_length=500)


def _key(db: Session) -> str:
    key = stock.coverr_key(db)
    if key is None:
        raise HTTPException(status_code=409, detail="add your Coverr API key in Settings → Stock clips first")
    return key


def _out(clip: Path) -> dict:
    return lib.info(clip)


@router.get("")
def status(db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    return {"coverr": stock.coverr_key(db) is not None}


@router.put("/coverr-key")
def save_key(body: KeyIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    stock.set_coverr_key(db, body.key.strip() or None)
    record_audit(db, actor_id=user.id, action="stock.coverr_key", details={"set": bool(body.key.strip())}, ip=client_ip(request))
    return {"coverr": bool(body.key.strip())}


@router.get("/coverr")
def search(q: str = "", page: int = 0, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    key = _key(db)
    try:
        return stock.coverr_search(key, q.strip()[:100], page=max(0, page))
    except (stock.StockError, OSError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None


@router.post("/coverr/{video_id}/import", status_code=201)
def import_coverr(
    video_id: str, body: ImportIn, request: Request, db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
) -> dict:  # fmt: skip
    key = _key(db)
    try:
        clip = stock.coverr_import(Path(get_settings().data_dir), key, video_id, tags=body.tags)
    except (stock.StockError, OSError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    record_audit(db, actor_id=user.id, action="background.import", details={"source": "coverr", "id": video_id, "name": clip.name},
                 ip=client_ip(request))  # fmt: skip
    return _out(clip)


@router.post("/mixkit", status_code=201)
def import_mixkit(
    body: MixkitIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    try:
        clip = stock.mixkit_import(Path(get_settings().data_dir), body.url.strip(), tags=body.tags)
    except stock.StockError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except OSError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    record_audit(db, actor_id=user.id, action="background.import", details={"source": "mixkit", "url": body.url, "name": clip.name},
                 ip=client_ip(request))  # fmt: skip
    return _out(clip)
