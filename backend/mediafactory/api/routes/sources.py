from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from mediafactory.api.db_utils import save_unique
from mediafactory.api.deps import client_ip, get_db, require_user
from mediafactory.api.routes.items import RightsStatus, get_fetcher
from mediafactory.audit.service import record_audit
from mediafactory.core.net import SafeFetcher
from mediafactory.db.base import utcnow
from mediafactory.db.models import SourceConnector, User
from mediafactory.sources.adapters import get_adapter
from mediafactory.sources.poller import run_source

router = APIRouter(prefix="/api/sources", tags=["sources"])
CONFLICT = "a source with this name already exists"
RUN_NOW_MIN_GAP = timedelta(seconds=60)  # be polite to sources (Reddit answers 429 to rapid repeats)

# 'manual' is an intake path, not a pollable source.
PollableAdapter = Literal["reddit_rss", "reddit", "rss", "web"]


class SourceIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    adapter: PollableAdapter
    params: dict = Field(default_factory=dict)
    poll_interval_min: int = Field(default=60, ge=10, le=10_080)
    enabled: bool = True
    default_rights: RightsStatus = "unknown"
    default_language: str | None = Field(default=None, max_length=8)


class SourcePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    params: dict | None = None
    poll_interval_min: int | None = Field(default=None, ge=10, le=10_080)
    enabled: bool | None = None
    default_rights: RightsStatus | None = None
    default_language: str | None = Field(default=None, max_length=8)


def _iso(dt):
    return dt.isoformat() if dt else None


def out(c: SourceConnector) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "adapter": c.adapter,
        "params": c.params,
        "enabled": c.enabled,
        "poll_interval_min": c.poll_interval_min,
        "default_rights": c.default_rights,
        "default_language": c.default_language,
        "next_run_at": _iso(c.next_run_at),
        "last_run_at": _iso(c.last_run_at),
        "last_success_at": _iso(c.last_success_at),
        "last_error": c.last_error,
        "consecutive_failures": c.consecutive_failures,
        "items_total": c.items_total,
        "deleted": c.deleted_at is not None,
    }


def _validated(adapter: str, params: dict) -> dict:
    try:
        return get_adapter(adapter).validate(params)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


def _get(db: Session, sid: int) -> SourceConnector:
    c = db.get(SourceConnector, sid)
    if c is None or c.deleted_at is not None:
        raise HTTPException(status_code=404, detail="source not found")
    return c


def _audit(db, user, action, c, request, details=None):
    record_audit(
        db, actor_id=user.id, action=action, target_type="source", target_id=str(c.id), details=details,
        ip=client_ip(request),
    )  # fmt: skip


@router.get("")
def list_sources(
    include_deleted: bool = False, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    q = select(SourceConnector).order_by(SourceConnector.id)
    if not include_deleted:
        q = q.where(SourceConnector.deleted_at.is_(None))
    return {"items": [out(c) for c in db.scalars(q).all()]}


@router.post("", status_code=201)
def create_source(
    body: SourceIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    data = body.model_dump()
    data["params"] = _validated(body.adapter, body.params)
    c = SourceConnector(**data)
    save_unique(db, lambda: db.add(c), CONFLICT)
    _audit(db, user, "source.create", c, request, {"name": c.name, "adapter": c.adapter, "params": c.params})
    return out(c)


@router.patch("/{sid}")
def update_source(
    sid: int,
    body: SourcePatch,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
) -> dict:
    c = _get(db, sid)
    changes = body.model_dump(exclude_unset=True)
    if "params" in changes and changes["params"] is not None:
        changes["params"] = _validated(c.adapter, changes["params"])
    def apply() -> None:
        for key, value in changes.items():
            if value is not None or key == "default_language":
                setattr(c, key, value)
        if "poll_interval_min" in changes or changes.get("enabled") is True:
            c.next_run_at = None  # re-evaluate soon with the new settings

    save_unique(db, apply, CONFLICT)
    _audit(db, user, "source.update", c, request, changes)
    return out(c)


@router.delete("/{sid}", status_code=204)
def delete_source(
    sid: int, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> Response:
    c = _get(db, sid)
    c.deleted_at = utcnow()
    c.enabled = False
    _audit(db, user, "source.delete", c, request, {"name": c.name})
    return Response(status_code=204)


@router.post("/{sid}/run")
def run_now(
    sid: int,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
    fetcher: SafeFetcher = Depends(get_fetcher),
) -> dict:
    c = _get(db, sid)
    if not c.enabled:
        raise HTTPException(status_code=409, detail="source is disabled; enable it first")
    if c.last_run_at is not None and utcnow() - c.last_run_at < RUN_NOW_MIN_GAP:
        raise HTTPException(status_code=409, detail="this source was collected less than a minute ago; try again shortly")
    result = run_source(db, c, fetcher=fetcher)
    _audit(db, user, "source.run", c, request, result.as_dict())
    return result.as_dict()
