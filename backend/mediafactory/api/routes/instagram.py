"""Instagram connection (Settings) and the manual-share pack for personal accounts."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_user
from mediafactory.audit.service import record_audit
from mediafactory.db.models import ProductionJob, User
from mediafactory.instagram import publish as ig_publish
from mediafactory.instagram.client import InstagramError, build_caption

router = APIRouter(prefix="/api", tags=["instagram"])


class TokenIn(BaseModel):
    access_token: str = Field(min_length=20, max_length=1000)


@router.get("/instagram")
def status(db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    return {"account": ig_publish.public_account(db)}


@router.put("/instagram/token")
def save_token(
    body: TokenIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    try:
        acc = ig_publish.save_account(db, body.access_token)
    except InstagramError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    record_audit(db, actor_id=user.id, action="instagram.connect", details={"username": acc["username"]}, ip=client_ip(request))
    return {"account": ig_publish.public_account(db)}


@router.delete("/instagram")
def disconnect(request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    if not ig_publish.remove_account(db):
        raise HTTPException(status_code=404, detail="Instagram is not connected")
    record_audit(db, actor_id=user.id, action="instagram.disconnect", ip=client_ip(request))
    return {"ok": True}


@router.get("/jobs/{jid}/instagram-pack")
def share_pack(jid: int, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    """What a personal account needs to post the Reel by hand: the caption and where to download the video."""
    job = db.get(ProductionJob, jid)
    result = ((job.payload or {}).get("result") or {}) if job else {}
    if not result.get("video"):
        raise HTTPException(status_code=404, detail="no finished video")
    script_file = Path(result.get("folder", "")) / "script.json"
    script = json.loads(script_file.read_text(encoding="utf-8")) if script_file.is_file() else {"title": result.get("title")}
    return {"caption": build_caption(script), "video": f"/api/jobs/{jid}/video"}


@router.post("/jobs/{jid}/instagram-manual")
def mark_shared(jid: int, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    """Remember that the video was posted by hand, so it shows as shared and is not offered again."""
    job = db.get(ProductionJob, jid)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    job.payload = {**(job.payload or {}), "instagram": {"state": "manual", "url": "https://www.instagram.com/"}}
    record_audit(db, actor_id=user.id, action="instagram.manual", target_type="production_job", target_id=str(jid), ip=client_ip(request))
    return {"instagram": job.payload["instagram"]}
