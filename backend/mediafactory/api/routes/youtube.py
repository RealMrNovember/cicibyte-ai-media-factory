"""YouTube connection (Settings) and sending videos to YouTube (Ready videos)."""

from datetime import UTC, datetime
from html import escape
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_user
from mediafactory.audit.service import record_audit
from mediafactory.core.crypto import encrypt
from mediafactory.db.models import ProductionJob, User, YouTubeChannel
from mediafactory.publishing import publish_job
from mediafactory.youtube import oauth
from mediafactory.youtube.oauth import YouTubeError

router = APIRouter(prefix="/api", tags=["youtube"])


class ClientIn(BaseModel):
    client_id: str = Field(min_length=10, max_length=300)
    client_secret: str = Field(min_length=6, max_length=300)


class StartIn(BaseModel):
    redirect_uri: str = Field(max_length=300)


class PublishIn(BaseModel):
    privacy: Literal["public", "unlisted", "private"] = "public"
    publish_at: datetime | None = None
    channel_id: int | None = None
    platforms: list[Literal["youtube", "instagram"]] = Field(default_factory=lambda: ["youtube"], min_length=1, max_length=2)


def channel_out(c: YouTubeChannel) -> dict:
    return {"id": c.id, "channel_id": c.channel_id, "title": c.title, "thumbnail": c.thumbnail, "is_default": c.is_default}


@router.get("/youtube")
def status(db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    client = oauth.get_client(db)
    chans = db.scalars(select(YouTubeChannel).order_by(YouTubeChannel.id))
    return {"client_id": client["client_id"] if client else None, "channels": [channel_out(c) for c in chans]}


@router.put("/youtube/client")
def save_client(
    body: ClientIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    oauth.set_client(db, body.client_id, body.client_secret)
    record_audit(db, actor_id=user.id, action="youtube.client", details={"client_id": body.client_id}, ip=client_ip(request))
    return {"ok": True}


@router.post("/youtube/auth")
def start(body: StartIn, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    if not body.redirect_uri.startswith(("http://127.0.0.1:", "http://localhost:", "https://")):
        raise HTTPException(status_code=422, detail="redirect address must be loopback (desktop app) or https")
    try:
        return {"url": oauth.start_auth(db, body.redirect_uri)}
    except YouTubeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


def _page(title: str, text: str, ok: bool) -> HTMLResponse:
    colour = "#6fbf8e" if ok else "#e0645c"
    return HTMLResponse(
        f"""<!doctype html><meta charset="utf-8"><title>{escape(title)}</title>
<body style="background:#0b0b0e;color:#ececf1;font:16px system-ui;display:grid;place-items:center;height:100vh;margin:0">
<div style="text-align:center;max-width:520px"><h2 style="color:{colour}">{escape(title)}</h2><p>{escape(text)}</p>
<p style="color:#8e8e9c;font-size:13px">CiciByte AI Media Factory</p></div></body>""",
        status_code=200 if ok else 400,
    )


@router.get("/youtube/callback", include_in_schema=False)
def callback(
    request: Request, state: str = "", code: str = "", error: str = "", db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
) -> HTMLResponse:  # fmt: skip
    if error:
        return _page("YouTube not connected", f"Google said: {error}", False)
    try:
        pending = oauth.take_pending(db, state)
        client = oauth.get_client(db)
        if client is None:
            raise YouTubeError("Google client is not configured")
        tokens = oauth.exchange_code(client, code, pending["verifier"], pending["redirect_uri"])
        info = oauth.my_channel(tokens["access_token"])
    except YouTubeError as exc:
        db.commit()  # the used/expired link is gone either way
        return _page("YouTube not connected", str(exc), False)
    chan = db.scalar(select(YouTubeChannel).where(YouTubeChannel.channel_id == info["channel_id"]))
    first = db.scalar(select(YouTubeChannel.id).limit(1)) is None
    if chan is None:
        chan = YouTubeChannel(channel_id=info["channel_id"], is_default=first)
        db.add(chan)
    chan.title, chan.thumbnail, chan.refresh_token_enc = info["title"], info["thumbnail"], encrypt(tokens["refresh_token"])
    record_audit(db, actor_id=user.id, action="youtube.connect", details={"channel": info["title"]}, ip=client_ip(request))
    return _page("YouTube connected ✓", f"Channel “{info['title']}” is ready. You can close this tab and return to the app.", True)


@router.delete("/youtube/channels/{cid}")
def disconnect(
    cid: int, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    chan = db.get(YouTubeChannel, cid)
    if chan is None:
        raise HTTPException(status_code=404, detail="channel not found")
    db.delete(chan)
    record_audit(db, actor_id=user.id, action="youtube.disconnect", details={"channel": chan.title}, ip=client_ip(request))
    return {"ok": True}


@router.post("/jobs/{jid}/publish")
def publish(
    jid: int, body: PublishIn, request: Request, db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
) -> dict:  # fmt: skip
    job = db.get(ProductionJob, jid)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    at = body.publish_at
    if at is not None and at.tzinfo is None:
        at = at.replace(tzinfo=UTC)
    chan = db.get(YouTubeChannel, body.channel_id) if body.channel_id else None
    try:
        publish_job(db, job, platforms=body.platforms, privacy=body.privacy, publish_at=at, channel=chan)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    record_audit(db, actor_id=user.id, action="job.publish", target_type="production_job", target_id=str(jid),
                 details={"privacy": body.privacy, "publish_at": at.isoformat() if at else None, "platforms": body.platforms},
                 ip=client_ip(request))  # fmt: skip
    return {"ok": True, "youtube": job.payload.get("youtube"), "instagram": job.payload.get("instagram")}
