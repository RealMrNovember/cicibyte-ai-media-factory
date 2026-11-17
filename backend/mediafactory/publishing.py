"""Publish a finished video to one or more platforms (YouTube, Instagram, TikTok) with one call.

When several are chosen they run one after another in this order, so the uploads never race to change the
job's status: YouTube first, then Instagram, then TikTok. A platform that fails for good still lets the next go.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from mediafactory.db.models import ProductionJob, YouTubeChannel

PLATFORMS = ("youtube", "instagram", "tiktok")


def publish_job(
    db: Session, job: ProductionJob, *, platforms: list[str] | tuple[str, ...] = ("youtube",), privacy: str = "public",
    publish_at: datetime | None = None, channel: YouTubeChannel | None = None,
) -> None:  # fmt: skip
    from mediafactory.instagram.publish import get_account, queue_instagram
    from mediafactory.tiktok.publish import get_account as tiktok_account
    from mediafactory.tiktok.publish import queue_tiktok
    from mediafactory.youtube.publish import queue_upload

    chosen = [p for p in PLATFORMS if p in platforms]
    if not chosen:
        raise ValueError("choose at least one platform")
    if "instagram" in chosen and get_account(db) is None:
        raise ValueError("connect an Instagram professional account in Settings first")
    if "tiktok" in chosen and tiktok_account(db) is None:
        raise ValueError("connect a TikTok account in Settings first")
    if "youtube" in chosen:
        queue_upload(db, job, privacy=privacy, publish_at=publish_at, channel=channel)
    if "instagram" in chosen:
        queue_instagram(db, job, publish_at=publish_at, after_youtube="youtube" in chosen)
    if "tiktok" in chosen:
        before = [p for p in chosen if p != "tiktok"]
        queue_tiktok(db, job, publish_at=publish_at, after=before[-1] if before else None)


def next_stage_after(job: ProductionJob, done: str) -> tuple[str, str] | None:
    """The stage to run once `done` ("youtube" or "instagram") has finished, successfully or for good."""
    p = job.payload or {}
    ig, tk = p.get("instagram") or {}, p.get("tiktok") or {}
    if done == "youtube" and ig.get("state") == "queued" and ig.get("after_youtube"):
        return ("upload_instagram", "io")
    if tk.get("state") == "queued" and tk.get("after") == done:
        return ("upload_tiktok", "io")
    return None
