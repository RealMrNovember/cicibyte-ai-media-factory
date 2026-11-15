"""Publish a finished video to one or more platforms (YouTube, Instagram) with one call.

When both are chosen, YouTube uploads first and Instagram follows right after, so the two uploads never
race to change the job's status.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from mediafactory.db.models import ProductionJob, YouTubeChannel

PLATFORMS = ("youtube", "instagram")


def publish_job(
    db: Session, job: ProductionJob, *, platforms: list[str] | tuple[str, ...] = ("youtube",), privacy: str = "public",
    publish_at: datetime | None = None, channel: YouTubeChannel | None = None,
) -> None:  # fmt: skip
    from mediafactory.instagram.publish import get_account, queue_instagram
    from mediafactory.youtube.publish import queue_upload

    chosen = [p for p in PLATFORMS if p in platforms]
    if not chosen:
        raise ValueError("choose at least one platform")
    if "instagram" in chosen and get_account(db) is None:
        raise ValueError("connect an Instagram professional account in Settings first")
    if "youtube" in chosen:
        queue_upload(db, job, privacy=privacy, publish_at=publish_at, channel=channel)
    if "instagram" in chosen:
        queue_instagram(db, job, publish_at=publish_at, after_youtube="youtube" in chosen)
