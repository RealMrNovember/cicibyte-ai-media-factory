"""When does a schedule run next? Times of day on chosen weekdays, in the schedule's own time zone."""

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def parse_times(times: list[str]) -> list[tuple[int, int]]:
    out = []
    for t in times:
        m = TIME_RE.match(t.strip())
        if not m:
            raise ValueError(f"time must look like 09:30, got {t!r}")
        out.append((int(m.group(1)), int(m.group(2))))
    if not out:
        raise ValueError("at least one time of day is required")
    return sorted(set(out))


def zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError(f"unknown time zone {name!r}") from None


def next_run(times: list[str], weekdays: list[int], tz: str, after: datetime) -> datetime:
    """The first slot strictly after `after` (UTC result)."""
    slots, days, z = parse_times(times), set(weekdays or range(7)), zone(tz)
    if not days <= set(range(7)):
        raise ValueError("weekdays are 0 (Monday) to 6 (Sunday)")
    local = after.astimezone(z)
    for offset in range(8):
        day = (local + timedelta(days=offset)).date()
        if day.weekday() not in days:
            continue
        for h, m in slots:
            cand = datetime(day.year, day.month, day.day, h, m, tzinfo=z)
            if cand > local:
                return cand.astimezone(timezone.utc)
    raise ValueError("no upcoming slot")  # unreachable with at least one weekday
