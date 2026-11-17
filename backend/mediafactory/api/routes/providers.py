from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from mediafactory.ai.client import ProviderError, list_models
from mediafactory.api.db_utils import save_unique
from mediafactory.api.deps import client_ip, get_db, require_admin
from mediafactory.audit.service import record_audit
from mediafactory.core.crypto import encrypt
from mediafactory.db.models import AIProvider, User

router = APIRouter(prefix="/api/providers", tags=["providers"])
CONFLICT = "a provider with this name already exists"

DEFAULT_TIMEOUT = {"local": 600, "remote": 120}


class ProviderIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["openai_compatible", "ollama_native"] = "openai_compatible"
    base_url: str = Field(min_length=1, max_length=500)
    api_key: str | None = None
    locality: Literal["local", "remote"] = "remote"
    timeout_s: int | None = Field(default=None, ge=5, le=3600)
    max_concurrency: int = Field(default=1, ge=1, le=32)
    enabled: bool = True
    options: dict = Field(default_factory=dict)


class ProviderPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    api_key: str | None = None  # None = unchanged, "" = remove
    locality: Literal["local", "remote"] | None = None
    timeout_s: int | None = Field(default=None, ge=5, le=3600)
    max_concurrency: int | None = Field(default=None, ge=1, le=32)
    enabled: bool | None = None
    options: dict | None = None


def out(p: AIProvider) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "kind": p.kind,
        "base_url": p.base_url,
        "has_api_key": bool(p.api_key_enc),
        "locality": p.locality,
        "timeout_s": p.timeout_s,
        "max_concurrency": p.max_concurrency,
        "enabled": p.enabled,
        "options": p.options or {},
    }


def _get(db: Session, pid: int) -> AIProvider:
    p = db.get(AIProvider, pid)
    if p is None:
        raise HTTPException(status_code=404, detail="provider not found")
    return p


@router.get("")
def list_providers(db: Session = Depends(get_db, scope="function"), user: User = Depends(require_admin)) -> dict:
    return {"items": [out(p) for p in db.scalars(select(AIProvider).order_by(AIProvider.id)).all()]}


@router.post("", status_code=201)
def create_provider(
    body: ProviderIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_admin)
) -> dict:
    p = AIProvider(
        name=body.name,
        kind=body.kind,
        base_url=body.base_url,
        api_key_enc=encrypt(body.api_key) if body.api_key else None,
        locality=body.locality,
        timeout_s=body.timeout_s or DEFAULT_TIMEOUT[body.locality],
        max_concurrency=body.max_concurrency,
        enabled=body.enabled,
        options=body.options,
    )
    save_unique(db, lambda: db.add(p), CONFLICT)
    record_audit(
        db, actor_id=user.id, action="provider.create", target_type="ai_provider", target_id=str(p.id),
        details=body.model_dump(), ip=client_ip(request),
    )  # fmt: skip
    return out(p)


@router.patch("/{pid}")
def update_provider(
    pid: int, body: ProviderPatch, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_admin)
) -> dict:
    p = _get(db, pid)
    changes = body.model_dump(exclude_unset=True)
    def apply() -> None:
        for key, value in changes.items():
            if key == "api_key":
                p.api_key_enc = encrypt(value) if value else None
            elif value is not None:
                setattr(p, key, value)

    save_unique(db, apply, CONFLICT)
    record_audit(
        db, actor_id=user.id, action="provider.update", target_type="ai_provider", target_id=str(p.id),
        details=changes, ip=client_ip(request),
    )  # fmt: skip
    return out(p)


@router.delete("/{pid}", status_code=204)
def delete_provider(
    pid: int, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_admin)
) -> Response:
    p = _get(db, pid)
    db.delete(p)
    record_audit(
        db, actor_id=user.id, action="provider.delete", target_type="ai_provider", target_id=str(pid),
        details={"name": p.name}, ip=client_ip(request),
    )  # fmt: skip
    return Response(status_code=204)


@router.post("/{pid}/test")
def test_provider(pid: int, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_admin)) -> dict:
    p = _get(db, pid)
    try:
        return {"ok": True, "models": list_models(p)}
    except ProviderError as exc:
        return {"ok": False, "error": str(exc)}
