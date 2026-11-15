"""YouTube API quota and per-channel daily upload limits.

Google gives each project a daily quota (10,000 units by default) that resets at midnight Pacific time.
An upload costs 1,600 units, a caption file 400, a cover image or playlist entry 50. We count what we spend
and hold uploads until the next reset instead of letting Google refuse them.
"""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from mediafactory.core.config import get_settings
from mediafactory.db.models import SystemSetting, YouTubeChannel

PACIFIC = ZoneInfo("America/Los_Angeles")
KEY = "youtube_quota"
COSTS = {"upload": 1600, "captions": 400, "thumbnail": 50, "playlist": 50}
UPLOAD_TOTAL = sum(COSTS.values())  # what one full publish may spend


def today(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).astimezone(PACIFIC).date().isoformat()


def next_reset(now: datetime | None = None) -> datetime:
    local = (now or datetime.now(timezone.utc)).astimezone(PACIFIC)
    return datetime.combine(local.date() + timedelta(days=1), time(0, 5), tzinfo=PACIFIC).astimezone(timezone.utc)


def usage(db: Session, now: datetime | None = None) -> dict:
    row = db.get(SystemSetting, KEY)
    value = row.value if row and isinstance(row.value, dict) else {}
    if value.get("date") != today(now):
        value = {"date": today(now), "units": 0, "uploads": {}}
    return {**value, "limit": get_settings().youtube_daily_quota}


def spend(db: Session, what: str, *, channel: YouTubeChannel | None = None, now: datetime | None = None) -> None:
    u = usage(db, now)
    u["units"] += COSTS[what]
    if what == "upload" and channel is not None:
        u["uploads"] = {**u["uploads"], channel.channel_id: u["uploads"].get(channel.channel_id, 0) + 1}
    value = {k: u[k] for k in ("date", "units", "uploads")}
    row = db.get(SystemSetting, KEY)
    if row is None:
        db.add(SystemSetting(key=KEY, value=value))
    else:
        row.value = value


def blocked(db: Session, channel: YouTubeChannel, now: datetime | None = None) -> str | None:
    """Why this channel cannot upload right now, or None."""
    u = usage(db, now)
    done = u["uploads"].get(channel.channel_id, 0)
    if channel.daily_limit and done >= channel.daily_limit:
        return f"daily upload limit reached for '{channel.title}' ({done}/{channel.daily_limit})"
    if u["units"] + UPLOAD_TOTAL > u["limit"]:
        return f"YouTube API quota for today is used up ({u['units']}/{u['limit']} units)"
    return None
