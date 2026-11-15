"""Send an approved video to YouTube: now, or scheduled (YouTube publishes it at the chosen time)."""

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from mediafactory.core.crypto import decrypt
from mediafactory.db.models import ProductionJob, YouTubeChannel
from mediafactory.queue.jobs import enqueue_stage
from mediafactory.queue.registry import StageContext, StageOutcome, stage_handler
from mediafactory.youtube import oauth
from mediafactory.youtube.oauth import YouTubeError
from mediafactory.youtube.upload import build_metadata, set_thumbnail, upload_video

UPLOAD_STAGE = "upload_youtube"
PRIVACY = ("public", "unlisted", "private")
PUBLISHABLE = ("needs_review", "approved", "failed", "published", "scheduled")  # published: e.g. on Instagram only


def default_channel(db: Session) -> YouTubeChannel | None:
    return db.scalar(select(YouTubeChannel).order_by(YouTubeChannel.is_default.desc(), YouTubeChannel.id).limit(1))


def queue_upload(
    db: Session, job: ProductionJob, *, privacy: str = "public", publish_at: datetime | None = None,
    channel: YouTubeChannel | None = None,
) -> None:  # fmt: skip
    if privacy not in PRIVACY:
        raise ValueError("privacy must be public, unlisted or private")
    if job.status not in PUBLISHABLE or not ((job.payload or {}).get("result") or {}).get("video"):
        raise ValueError("only a finished, approved video can be sent to YouTube")
    if (job.payload or {}).get("youtube", {}).get("id"):
        raise ValueError("this video is already on YouTube")
    if publish_at is not None and publish_at <= datetime.now(UTC):
        raise ValueError("the publish time must be in the future")
    channel = channel or default_channel(db)
    if channel is None:
        raise ValueError("connect a YouTube channel in Settings first")
    job.payload = {**(job.payload or {}), "youtube": {
        "state": "queued", "privacy": privacy, "publish_at": publish_at.isoformat() if publish_at else None,
        "channel": channel.title,
    }}  # fmt: skip
    job.status = "uploading"
    enqueue_stage(db, job.id, UPLOAD_STAGE, "io", inputs={
        "privacy": privacy, "publish_at": publish_at.isoformat() if publish_at else None, "channel_db_id": channel.id,
    })  # fmt: skip


@stage_handler(UPLOAD_STAGE, "io")
def upload_stage(ctx: StageContext) -> StageOutcome:
    db, job, inputs = ctx.session, ctx.job, ctx.run.inputs or {}
    result = (job.payload or {}).get("result") or {}
    video = Path(result.get("video", ""))
    if not video.is_file():
        raise YouTubeError("the rendered video file is missing")
    script_file = Path(result.get("folder", "")) / "script.json"
    script = json.loads(script_file.read_text(encoding="utf-8")) if script_file.is_file() else {"title": result.get("title")}
    channel = db.get(YouTubeChannel, inputs.get("channel_db_id")) or default_channel(db)
    client = oauth.get_client(db)
    if channel is None or client is None:
        raise YouTubeError("YouTube is not connected (Settings → YouTube)")
    publish_at = datetime.fromisoformat(inputs["publish_at"]) if inputs.get("publish_at") else None
    ctx.log(f"uploading to '{channel.title}' ({inputs.get('privacy')}{', at ' + inputs['publish_at'] if publish_at else ''})")
    token = oauth.access_token(client, decrypt(channel.refresh_token_enc))
    meta = build_metadata(script, language=job.language or "en", privacy=inputs.get("privacy", "public"), publish_at=publish_at)
    vid = upload_video(token, video, meta)
    url = f"https://youtube.com/shorts/{vid}"
    thumb = Path(result.get("thumbnail") or "")
    if thumb.is_file():
        problem = set_thumbnail(token, vid, thumb)
        ctx.log("cover image set" if problem is None else f"cover image not accepted by YouTube ({problem})")
    job.payload = {**(job.payload or {}), "youtube": {
        "state": "scheduled" if publish_at else "published", "id": vid, "url": url, "channel": channel.title,
        "privacy": meta["status"]["privacyStatus"], "publish_at": inputs.get("publish_at"),
    }}  # fmt: skip
    ctx.log(f"done: {url}")
    from mediafactory.instagram.publish import after_youtube_stage

    return StageOutcome(next_status="scheduled" if publish_at else "published", outputs={"youtube_id": vid, "url": url},
                        next_stage=after_youtube_stage(job))  # fmt: skip
