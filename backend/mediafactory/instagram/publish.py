"""Send a finished video to Instagram as a Reel: now, at a chosen time, or right after its YouTube upload.

Instagram has no scheduled publishing in the API, so a scheduled Reel waits in the queue until its time.
Errors never mark an already-published (YouTube) video as failed: they are recorded under payload.instagram.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from mediafactory.core.crypto import decrypt, encrypt
from mediafactory.db.models import ProductionJob, SystemSetting
from mediafactory.instagram import client as ig
from mediafactory.instagram.client import InstagramError
from mediafactory.queue.jobs import enqueue_stage
from mediafactory.queue.registry import StageContext, StageOutcome, stage_handler

STAGE = "upload_instagram"
ACCOUNT_KEY = "instagram_account"
PUBLISHABLE = ("needs_review", "approved", "failed", "published", "scheduled")
MAX_ATTEMPTS = 3


def get_account(db: Session) -> dict | None:
    row = db.get(SystemSetting, ACCOUNT_KEY)
    return row.value if row and isinstance(row.value, dict) and row.value.get("token_enc") else None


def public_account(db: Session) -> dict | None:
    acc = get_account(db)
    return {k: acc.get(k) for k in ("username", "account_type", "expires_at")} if acc else None


def save_account(db: Session, token: str, *, info: dict | None = None, expires_at: datetime | None = None) -> dict:
    """Check the token with Instagram (must be a professional account) and store it encrypted."""
    token = token.strip()
    info = info or ig.account_info(token)
    now = datetime.now(UTC)
    value = {**info, "token_enc": encrypt(token), "refreshed_at": now.isoformat(),
             "expires_at": (expires_at or now + timedelta(days=60)).isoformat()}  # fmt: skip
    row = db.get(SystemSetting, ACCOUNT_KEY)
    if row is None:
        db.add(SystemSetting(key=ACCOUNT_KEY, value=value))
    else:
        row.value = value
    return value


def remove_account(db: Session) -> bool:
    row = db.get(SystemSetting, ACCOUNT_KEY)
    if row is None:
        return False
    db.delete(row)
    return True


def access_token(db: Session) -> tuple[str, dict]:
    """The stored token, refreshed first when due (a long-lived token lasts 60 days)."""
    acc = get_account(db)
    if acc is None:
        raise InstagramError("Instagram is not connected (Settings → Instagram)")
    token = decrypt(acc["token_enc"])
    if ig.refresh_due(acc):
        try:
            token, expires = ig.refresh_token(token)
            acc = save_account(db, token, info={k: acc[k] for k in ("user_id", "username", "account_type")}, expires_at=expires)
        except InstagramError:
            if datetime.fromisoformat(acc["expires_at"]) <= datetime.now(UTC):
                raise InstagramError("the Instagram token has expired: paste a new one in Settings → Instagram") from None
    return token, acc


def refresh_stored_token(db: Session) -> None:
    """Called periodically so an unused token does not run out."""
    if get_account(db) is not None:
        access_token(db)


def queue_instagram(db: Session, job: ProductionJob, *, publish_at: datetime | None = None, after_youtube: bool = False) -> None:
    payload = job.payload or {}
    if not (payload.get("result") or {}).get("video"):
        raise ValueError("only a finished video can be sent to Instagram")
    state = (payload.get("instagram") or {}).get("state")
    if state in ("queued", "uploading", "published", "manual"):
        raise ValueError("this video is already on Instagram or on its way")
    if job.status not in PUBLISHABLE and not (after_youtube and job.status == "uploading"):
        raise ValueError("only a finished, approved video can be sent to Instagram")
    if publish_at is not None and publish_at <= datetime.now(UTC):
        raise ValueError("the publish time must be in the future")
    if get_account(db) is None:
        raise ValueError("connect an Instagram professional account in Settings first")
    job.payload = {**payload, "instagram": {
        "state": "queued", "publish_at": publish_at.isoformat() if publish_at else None, "after_youtube": after_youtube,
        "prev_status": job.status,
    }}  # fmt: skip
    if after_youtube:
        return  # the YouTube stage starts it when it finishes (never both uploads at once)
    if job.status in ("needs_review", "approved", "failed"):
        job.status = "scheduled" if publish_at else "uploading"
    run = enqueue_stage(db, job.id, STAGE, "io", inputs={"attempt": 1})
    if publish_at:
        run.run_after = publish_at


def after_youtube_stage(job: ProductionJob) -> tuple[str, str] | None:
    """The next stage for the YouTube handler: Instagram, when the same publish asked for both."""
    ins = (job.payload or {}).get("instagram") or {}
    return (STAGE, "io") if ins.get("state") == "queued" and ins.get("after_youtube") else None


def _status_after(job: ProductionJob, *, ok: bool) -> str:
    yt = ((job.payload or {}).get("youtube") or {}).get("state")
    if yt in ("published", "scheduled"):
        return yt
    if ok:
        return "published"
    prev = ((job.payload or {}).get("instagram") or {}).get("prev_status")
    return prev if prev in ("needs_review", "approved") else "failed"


def _set(job: ProductionJob, **fields) -> None:
    job.payload = {**(job.payload or {}), "instagram": {**((job.payload or {}).get("instagram") or {}), **fields}}


@stage_handler(STAGE, "io")
def upload_stage(ctx: StageContext) -> StageOutcome:
    db, job, inputs = ctx.session, ctx.job, ctx.run.inputs or {}
    info = (job.payload or {}).get("instagram") or {}
    at = datetime.fromisoformat(info["publish_at"]) if info.get("publish_at") else None
    if at and at > datetime.now(UTC) + timedelta(seconds=30):  # chained after a scheduled YouTube upload
        run = enqueue_stage(db, job.id, STAGE, "io", inputs=inputs)
        run.run_after = at
        ctx.log(f"waiting until {at.isoformat()} to publish on Instagram")
        return StageOutcome(next_status="scheduled" if job.status in ("uploading", "approved") else job.status)
    result = (job.payload or {}).get("result") or {}
    try:
        video = Path(result.get("video", ""))
        if not video.is_file():
            raise InstagramError("the rendered video file is missing")
        script_file = Path(result.get("folder", "")) / "script.json"
        script = json.loads(script_file.read_text(encoding="utf-8")) if script_file.is_file() else {"title": result.get("title")}
        token, acc = access_token(db)
        _set(job, state="uploading", account=acc.get("username"))
        ctx.log(f"publishing the Reel on @{acc.get('username')}")
        from mediafactory import credit

        caption = ig.build_caption(script, credit=credit.line(db, job.language))
        media_id, url = ig.publish_reel(token, acc["user_id"], video, caption, log=ctx.log)
    except InstagramError as exc:
        attempt = int(inputs.get("attempt", 1))
        if exc.transient and attempt < MAX_ATTEMPTS:
            run = enqueue_stage(db, job.id, STAGE, "io", inputs={**inputs, "attempt": attempt + 1})
            run.run_after = datetime.now(UTC) + timedelta(minutes=5 * attempt)
            _set(job, state="queued", error=str(exc)[:300])
            ctx.log(f"{exc} — trying again in {5 * attempt} min")
            return StageOutcome(next_status=job.status)
        _set(job, state="failed", error=str(exc)[:300])
        ctx.log(f"not published on Instagram: {exc}")
        return StageOutcome(next_status=_status_after(job, ok=False))
    _set(job, state="published", id=media_id, url=url, error=None)
    ctx.log(f"done: {url}")
    return StageOutcome(next_status=_status_after(job, ok=True), outputs={"instagram_id": media_id, "url": url})
