"""TikTok connection (Settings), posting mode, and the manual-share pack."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_user
from mediafactory.api.routes.youtube import _page
from mediafactory.audit.service import record_audit
from mediafactory.db.models import ProductionJob, User
from mediafactory.tiktok import client as tt
from mediafactory.tiktok import publish as ttp
from mediafactory.tiktok.client import TikTokError

router = APIRouter(prefix="/api", tags=["tiktok"])
# What to register in the TikTok developer portal (Login Kit → Desktop): any port of the desktop app.
REDIRECT_PATTERN = "http://127.0.0.1:*/api/tiktok/callback"


class AppIn(BaseModel):
    client_key: str = Field(min_length=6, max_length=200)
    client_secret: str = Field(min_length=6, max_length=300)


class StartIn(BaseModel):
    redirect_uri: str = Field(max_length=300)
    direct: bool = False


class ModeIn(BaseModel):
    mode: Literal["draft", "direct"]
    privacy_level: str | None = Field(default=None, max_length=60)


@router.get("/tiktok")
def status(db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    app = ttp.get_app(db)
    return {"client_key": app["client_key"] if app else None, "account": ttp.public_account(db), "redirect": REDIRECT_PATTERN}


@router.put("/tiktok/app")
def save_app(body: AppIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    ttp.set_app(db, body.client_key, body.client_secret)
    record_audit(db, actor_id=user.id, action="tiktok.app", details={"client_key": body.client_key}, ip=client_ip(request))
    return {"ok": True}


@router.post("/tiktok/auth")
def start(body: StartIn, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    if not body.redirect_uri.startswith(("http://127.0.0.1:", "http://localhost:")) or not body.redirect_uri.endswith("/api/tiktok/callback"):
        raise HTTPException(status_code=422, detail="connect TikTok from the desktop app (TikTok only accepts its local address)")
    try:
        return {"url": ttp.start_auth(db, body.redirect_uri, direct=body.direct)}
    except TikTokError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.get("/tiktok/callback", include_in_schema=False)
def callback(
    request: Request, state: str = "", code: str = "", error: str = "", error_description: str = "",
    db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user),
) -> HTMLResponse:  # fmt: skip
    if error:
        return _page("TikTok not connected", f"TikTok said: {error_description or error}", False)
    try:
        acc = ttp.finish_auth(db, state, code)
    except TikTokError as exc:
        db.commit()  # the used/expired link is gone either way
        return _page("TikTok not connected", str(exc), False)
    record_audit(db, actor_id=user.id, action="tiktok.connect", details={"account": acc["display_name"]}, ip=client_ip(request))
    return _page("TikTok connected ✓", f"“{acc['display_name']}” is ready. You can close this tab and return to the app.", True)


@router.get("/tiktok/creator")
def creator(db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    """What TikTok allows this account right now (needed to choose the visibility of direct posts)."""
    try:
        token, _ = ttp.access_token(db)
        info = tt.creator_info(token)
    except TikTokError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return {k: info.get(k) for k in ("creator_nickname", "creator_username", "creator_avatar_url", "privacy_level_options",
                                     "max_video_post_duration_sec", "comment_disabled", "duet_disabled", "stitch_disabled")}  # fmt: skip


@router.put("/tiktok/mode")
def set_mode(body: ModeIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    acc = ttp.get_account(db)
    if acc is None:
        raise HTTPException(status_code=404, detail="TikTok is not connected")
    if body.mode == "direct":
        if tt.DIRECT_SCOPE not in str(acc.get("scope") or "").split(","):
            raise HTTPException(status_code=409, detail="direct posting needs the video.publish permission: reconnect TikTok "
                                                        "with “direct posting” ticked")  # fmt: skip
        if not body.privacy_level:
            raise HTTPException(status_code=422, detail="choose who can see direct posts")
        try:
            token, _ = ttp.access_token(db)
            options = tt.creator_info(token).get("privacy_level_options") or []
        except TikTokError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None
        if body.privacy_level not in options:
            raise HTTPException(status_code=422, detail=f"this account can choose only: {', '.join(options) or 'none'}")
    ttp.set_mode(db, body.mode, body.privacy_level)
    record_audit(db, actor_id=user.id, action="tiktok.mode", details={"mode": body.mode, "privacy": body.privacy_level},
                 ip=client_ip(request))  # fmt: skip
    return {"account": ttp.public_account(db)}


@router.delete("/tiktok")
def disconnect(request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    if not ttp.remove_account(db):
        raise HTTPException(status_code=404, detail="TikTok is not connected")
    record_audit(db, actor_id=user.id, action="tiktok.disconnect", ip=client_ip(request))
    return {"ok": True}


@router.get("/jobs/{jid}/tiktok-pack")
def share_pack(jid: int, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    """The caption to paste in TikTok (for drafts and manual posts) and where to download the video."""
    job = db.get(ProductionJob, jid)
    if job is None or not ((job.payload or {}).get("result") or {}).get("video"):
        raise HTTPException(status_code=404, detail="no finished video")
    return {"caption": ttp.caption_for(db, job), "video": f"/api/jobs/{jid}/video"}


@router.post("/jobs/{jid}/tiktok-manual")
def mark_shared(jid: int, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    """Remember that the video was posted on TikTok by hand (or the draft was posted), so it is not offered again."""
    job = db.get(ProductionJob, jid)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    job.payload = {**(job.payload or {}), "tiktok": {**((job.payload or {}).get("tiktok") or {}), "state": "manual",
                                                     "url": "https://www.tiktok.com/"}}  # fmt: skip
    record_audit(db, actor_id=user.id, action="tiktok.manual", target_type="production_job", target_id=str(jid), ip=client_ip(request))
    return {"tiktok": job.payload["tiktok"]}
