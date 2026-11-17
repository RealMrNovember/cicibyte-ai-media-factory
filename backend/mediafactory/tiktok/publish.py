"""Send a finished video to TikTok: as a draft in the creator's inbox (default) or posted directly.

The connection is the user's own TikTok developer app (client key + secret) and a sign-in through the desktop
app (loopback address, PKCE). Like Instagram, TikTok has no scheduled posting in the API, so a scheduled video
waits in the queue. When several platforms are chosen, TikTok goes last (see publishing.next_stage_after).
"""

import json
import secrets
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from mediafactory.core.crypto import decrypt, encrypt
from mediafactory.db.models import ProductionJob, SystemSetting
from mediafactory.queue.jobs import enqueue_stage
from mediafactory.queue.registry import StageContext, StageOutcome, stage_handler
from mediafactory.tiktok import client as tt
from mediafactory.tiktok.client import TikTokError

STAGE = "upload_tiktok"
APP_KEY = "tiktok_app"
ACCOUNT_KEY = "tiktok_account"
PENDING_PREFIX = "tiktok_pending:"
PENDING_TTL_S = 15 * 60
PUBLISHABLE = ("needs_review", "approved", "failed", "published", "scheduled")
DONE_STATES = ("queued", "uploading", "inbox", "published", "manual")
MAX_ATTEMPTS = 3
REFRESH_MARGIN = timedelta(minutes=10)
KEEP_ALIVE = timedelta(days=7)


# ---------- the user's TikTok developer app ----------


def get_app(db: Session) -> dict | None:
    row = db.get(SystemSetting, APP_KEY)
    if not row or not isinstance(row.value, dict) or not row.value.get("client_key"):
        return None
    return {"client_key": row.value["client_key"], "client_secret": decrypt(row.value["client_secret_enc"])}


def set_app(db: Session, client_key: str, client_secret: str) -> None:
    value = {"client_key": client_key.strip(), "client_secret_enc": encrypt(client_secret.strip())}
    row = db.get(SystemSetting, APP_KEY)
    if row is None:
        db.add(SystemSetting(key=APP_KEY, value=value))
    else:
        row.value = value


# ---------- the connected account ----------


def get_account(db: Session) -> dict | None:
    row = db.get(SystemSetting, ACCOUNT_KEY)
    return row.value if row and isinstance(row.value, dict) and row.value.get("refresh_enc") else None


def public_account(db: Session) -> dict | None:
    acc = get_account(db)
    if not acc:
        return None
    scopes = str(acc.get("scope") or "").split(",")
    return {"display_name": acc.get("display_name"), "avatar": acc.get("avatar"), "mode": acc.get("mode", "draft"),
            "privacy_level": acc.get("privacy_level"), "can_direct": tt.DIRECT_SCOPE in scopes,
            "needs_reconnect": bool(acc.get("needs_reconnect")), "refresh_expires": acc.get("refresh_expires")}  # fmt: skip


def _store(db: Session, value: dict) -> dict:
    row = db.get(SystemSetting, ACCOUNT_KEY)
    if row is None:
        db.add(SystemSetting(key=ACCOUNT_KEY, value=value))
    else:
        row.value = value
    return value


def save_tokens(db: Session, tokens: dict, *, info: dict | None = None) -> dict:
    """Store fresh tokens (encrypted). Keeps the chosen mode; info replaces the shown name/avatar."""
    old = get_account(db) or {}
    now = datetime.now(UTC)
    value = {
        "open_id": (info or {}).get("open_id") or tokens.get("open_id") or old.get("open_id"),
        "display_name": (info or {}).get("display_name") or old.get("display_name") or "TikTok",
        "avatar": (info or {}).get("avatar") if info else old.get("avatar"),
        "scope": tokens.get("scope") or old.get("scope") or "",
        "access_enc": encrypt(tokens["access_token"]),
        "refresh_enc": encrypt(tokens["refresh_token"]),
        "access_expires": (now + timedelta(seconds=int(tokens.get("expires_in", 86400)))).isoformat(),
        "refresh_expires": (now + timedelta(seconds=int(tokens.get("refresh_expires_in", 31536000)))).isoformat(),
        "refreshed_at": now.isoformat(),
        "mode": old.get("mode", "draft"),
        "privacy_level": old.get("privacy_level"),
        "needs_reconnect": False,
    }
    if tt.DIRECT_SCOPE not in value["scope"].split(","):
        value["mode"] = "draft"
    return _store(db, value)


def remove_account(db: Session) -> bool:
    row = db.get(SystemSetting, ACCOUNT_KEY)
    if row is None:
        return False
    db.delete(row)
    return True


def set_mode(db: Session, mode: str, privacy_level: str | None) -> dict:
    acc = get_account(db)
    if acc is None:
        raise ValueError("connect TikTok first")
    if mode == "direct" and tt.DIRECT_SCOPE not in str(acc.get("scope") or "").split(","):
        raise PermissionError("direct posting needs the video.publish permission: reconnect TikTok with direct posting")
    return _store(db, {**acc, "mode": mode, "privacy_level": privacy_level if mode == "direct" else None})


def start_auth(db: Session, redirect_uri: str, *, direct: bool = False) -> str:
    app = get_app(db)
    if app is None:
        raise TikTokError("add your TikTok client key and secret first")
    state = secrets.token_urlsafe(24)
    verifier, challenge = tt.pkce()
    db.add(SystemSetting(key=PENDING_PREFIX + state,
                         value={"verifier": verifier, "redirect_uri": redirect_uri, "expires": time.time() + PENDING_TTL_S}))  # fmt: skip
    return tt.auth_url(app["client_key"], redirect_uri, state, challenge, direct=direct)


def finish_auth(db: Session, state: str, code: str) -> dict:
    row = db.get(SystemSetting, PENDING_PREFIX + state) if state else None
    if row is None:
        raise TikTokError("this sign-in link is unknown or was already used — start again from Settings")
    pending = dict(row.value)
    db.delete(row)
    if pending.get("expires", 0) < time.time():
        raise TikTokError("this sign-in link expired — start again from Settings")
    app = get_app(db)
    if app is None:
        raise TikTokError("the TikTok client key is not set")
    tokens = tt.exchange_code(app, code, pending["verifier"], pending["redirect_uri"])
    return save_tokens(db, tokens, info=tt.user_info(tokens["access_token"]))


def access_token(db: Session, *, force: bool = False) -> tuple[str, dict]:
    """A working access token, refreshed when it is about to run out (TikTok's last for a day or less)."""
    acc = get_account(db)
    if acc is None:
        raise TikTokError("TikTok is not connected (Settings → TikTok)")
    if not force and datetime.fromisoformat(acc["access_expires"]) - datetime.now(UTC) > REFRESH_MARGIN:
        return decrypt(acc["access_enc"]), acc
    app = get_app(db)
    if app is None:
        raise TikTokError("the TikTok client key is not set (Settings → TikTok)")
    try:
        tokens = tt.refresh(app, decrypt(acc["refresh_enc"]))
    except TikTokError as exc:
        if exc.reauth:
            _store(db, {**acc, "needs_reconnect": True})
            db.commit()  # keep the warning even though the caller fails
            raise TikTokError("TikTok access ended: reconnect TikTok in Settings", reauth=True) from None
        raise
    acc = save_tokens(db, tokens)
    return tokens["access_token"], acc


def keep_alive(db: Session) -> None:
    """Called by the scheduler: refresh now and then, so an unused connection does not expire."""
    acc = get_account(db)
    if acc and not acc.get("needs_reconnect"):
        if datetime.now(UTC) - datetime.fromisoformat(acc["refreshed_at"]) > KEEP_ALIVE:
            access_token(db, force=True)


# ---------- publishing ----------


def caption_for(db: Session, job: ProductionJob) -> str:
    from mediafactory import credit
    from mediafactory.instagram.client import build_caption

    result = (job.payload or {}).get("result") or {}
    script_file = Path(result.get("folder", "")) / "script.json"
    script = json.loads(script_file.read_text(encoding="utf-8")) if script_file.is_file() else {"title": result.get("title")}
    return build_caption(script, credit=credit.line(db, job.language))  # same limits as Instagram: 2200 chars


def queue_tiktok(db: Session, job: ProductionJob, *, publish_at: datetime | None = None, after: str | None = None) -> None:
    payload = job.payload or {}
    if not (payload.get("result") or {}).get("video"):
        raise ValueError("only a finished video can be sent to TikTok")
    if ((payload.get("tiktok") or {}).get("state")) in DONE_STATES:
        raise ValueError("this video is already on TikTok or on its way")
    if job.status not in PUBLISHABLE and not (after and job.status == "uploading"):
        raise ValueError("only a finished, approved video can be sent to TikTok")
    if publish_at is not None and publish_at <= datetime.now(UTC):
        raise ValueError("the publish time must be in the future")
    if get_account(db) is None:
        raise ValueError("connect a TikTok account in Settings first")
    job.payload = {**payload, "tiktok": {
        "state": "queued", "publish_at": publish_at.isoformat() if publish_at else None, "after": after,
        "prev_status": job.status,
    }}  # fmt: skip
    if after:
        return  # started by the platform before it, when that one finishes
    if job.status in ("needs_review", "approved", "failed"):
        job.status = "scheduled" if publish_at else "uploading"
    run = enqueue_stage(db, job.id, STAGE, "io", inputs={"attempt": 1})
    if publish_at:
        run.run_after = publish_at


def _status_after(job: ProductionJob, *, ok: bool) -> str:
    p = job.payload or {}
    yt = (p.get("youtube") or {}).get("state")
    if yt in ("published", "scheduled"):
        return yt
    if ok or (p.get("instagram") or {}).get("state") in ("published", "manual"):
        return "published"
    prev = (p.get("tiktok") or {}).get("prev_status")
    return prev if prev in ("needs_review", "approved") else "failed"


def _set(job: ProductionJob, **fields) -> None:
    job.payload = {**(job.payload or {}), "tiktok": {**((job.payload or {}).get("tiktok") or {}), **fields}}


def _post_info(token: str, acc: dict, caption: str) -> dict:
    """What a direct post needs; checked against what TikTok allows this creator right now."""
    info = tt.creator_info(token)
    privacy = acc.get("privacy_level")
    if privacy not in (info.get("privacy_level_options") or []):
        raise TikTokError(f"the chosen TikTok visibility ({privacy}) is not available for this account any more: "
                          "choose it again in Settings → TikTok")  # fmt: skip
    return {"title": caption, "privacy_level": privacy, "disable_comment": bool(info.get("comment_disabled")),
            "disable_duet": bool(info.get("duet_disabled")), "disable_stitch": bool(info.get("stitch_disabled")),
            "is_aigc": True}  # fmt: skip


@stage_handler(STAGE, "io")
def upload_stage(ctx: StageContext) -> StageOutcome:
    db, job, inputs = ctx.session, ctx.job, ctx.run.inputs or {}
    info = (job.payload or {}).get("tiktok") or {}
    at = datetime.fromisoformat(info["publish_at"]) if info.get("publish_at") else None
    if at and at > datetime.now(UTC) + timedelta(seconds=30):  # chained after a platform that ran early
        run = enqueue_stage(db, job.id, STAGE, "io", inputs=inputs)
        run.run_after = at
        ctx.log(f"waiting until {at.isoformat()} to send to TikTok")
        return StageOutcome(next_status="scheduled" if job.status in ("uploading", "approved") else job.status)
    result = (job.payload or {}).get("result") or {}
    try:
        video = Path(result.get("video", ""))
        if not video.is_file():
            raise TikTokError("the rendered video file is missing")
        token, acc = access_token(db)
        caption = caption_for(db, job)
        direct = acc.get("mode") == "direct"
        _set(job, state="uploading", account=acc.get("display_name"), caption=caption)
        ctx.log(f"sending to TikTok ({'direct post' if direct else 'draft in the inbox'}) for {acc.get('display_name')}")
        sent = tt.send_video(token, video, post_info=_post_info(token, acc, caption) if direct else None, log=ctx.log)
    except TikTokError as exc:
        attempt = int(inputs.get("attempt", 1))
        if exc.transient and attempt < MAX_ATTEMPTS:
            run = enqueue_stage(db, job.id, STAGE, "io", inputs={**inputs, "attempt": attempt + 1})
            run.run_after = datetime.now(UTC) + timedelta(minutes=5 * attempt)
            _set(job, state="queued", error=str(exc)[:300])
            ctx.log(f"{exc} — trying again in {5 * attempt} min")
            return StageOutcome(next_status=job.status)
        _set(job, state="failed", error=str(exc)[:300])
        ctx.log(f"not sent to TikTok: {exc}")
        return StageOutcome(next_status=_status_after(job, ok=False))
    if sent["status"] == "SEND_TO_USER_INBOX":
        _set(job, state="inbox", publish_id=sent["publish_id"], url="https://www.tiktok.com/", error=None)
        ctx.log("done: the video is waiting in your TikTok inbox — open TikTok to post it")
    else:
        url = f"https://www.tiktok.com/@/video/{sent['post_id']}" if sent.get("post_id") else "https://www.tiktok.com/"
        _set(job, state="published", publish_id=sent["publish_id"], url=url, error=None)
        ctx.log(f"done: {url}")
    return StageOutcome(next_status=_status_after(job, ok=True), outputs={"tiktok_publish_id": sent["publish_id"]})
