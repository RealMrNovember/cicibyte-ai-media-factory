"""Polite fetching: minimum spacing between requests to the same host, and a cooldown after HTTP 429.

`MemoryHostThrottle` works inside one process. `DbHostThrottle` keeps the state in PostgreSQL so the api and
worker processes (and several workers) respect the same spacing and cooldown.
"""

import threading
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from mediafactory.core.net import FetchError
from mediafactory.db.base import utcnow

DEFAULT_INTERVAL_S = 2.0
# Hosts known to rate-limit anonymous clients aggressively.
HOST_INTERVALS_S = {"www.reddit.com": 10.0, "reddit.com": 10.0, "old.reddit.com": 10.0, "oauth.reddit.com": 2.0}
DEFAULT_RETRY_AFTER_S = 60
MAX_RETRY_AFTER_S = 3600


def parse_retry_after(value: str | None) -> int:
    """Seconds to wait from a Retry-After header (delta-seconds or HTTP-date); default 60, capped at 1 h."""
    if not value:
        return DEFAULT_RETRY_AFTER_S
    value = value.strip()
    if value.isdigit():
        seconds = int(value)
    else:
        try:
            seconds = int((parsedate_to_datetime(value) - utcnow()).total_seconds())
        except (TypeError, ValueError):
            return DEFAULT_RETRY_AFTER_S
    return max(1, min(seconds, MAX_RETRY_AFTER_S))


def _cooling(host: str, until: datetime) -> FetchError:
    return FetchError(
        f"{host} is rate limiting us; cooling down until {until:%H:%M:%S} UTC", status=429, retryable=True
    )


class MemoryHostThrottle:
    def __init__(
        self,
        *,
        default_interval_s: float = DEFAULT_INTERVAL_S,
        intervals: dict[str, float] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.default_interval_s = default_interval_s
        self.intervals = dict(HOST_INTERVALS_S if intervals is None else intervals)
        self._sleep, self._clock = sleep, clock
        self._last: dict[str, float] = {}
        self._blocked: dict[str, datetime] = {}
        self._lock = threading.Lock()

    def interval_for(self, host: str) -> float:
        return self.intervals.get(host, self.default_interval_s)

    def acquire(self, host: str) -> None:
        with self._lock:
            until = self._blocked.get(host)
            if until and until > utcnow():
                raise _cooling(host, until)
            last = self._last.get(host)
            wait = 0.0 if last is None else self.interval_for(host) - (self._clock() - last)
        if wait > 0:
            self._sleep(wait)
        with self._lock:
            self._last[host] = self._clock()

    def penalize(self, host: str, seconds: int) -> None:
        with self._lock:
            until = utcnow() + timedelta(seconds=seconds)
            self._blocked[host] = max(self._blocked.get(host, until), until)


class DbHostThrottle(MemoryHostThrottle):
    """Same contract, state in the host_rate_limits table (row-locked while deciding)."""

    def __init__(self, factory: Callable[[], Session], **kwargs):
        super().__init__(**kwargs)
        self._factory = factory

    def _row(self, session: Session, host: str):
        from mediafactory.db.models.net import HostRateLimit

        session.execute(insert(HostRateLimit).values(host=host).on_conflict_do_nothing(index_elements=["host"]))
        return session.get(HostRateLimit, host, with_for_update=True)

    def acquire(self, host: str) -> None:
        with self._factory() as s:
            row = self._row(s, host)
            now = utcnow()
            if row.blocked_until and row.blocked_until > now:
                until = row.blocked_until
                s.rollback()
                raise _cooling(host, until)
            if row.last_request_at is not None:
                wait = self.interval_for(host) - (now - row.last_request_at).total_seconds()
                if wait > 0:
                    self._sleep(wait)  # holding the row lock serialises other processes for this host
            row.last_request_at = utcnow()
            s.commit()

    def penalize(self, host: str, seconds: int) -> None:
        with self._factory() as s:
            row = self._row(s, host)
            until = utcnow() + timedelta(seconds=seconds)
            if row.blocked_until is None or row.blocked_until < until:
                row.blocked_until = until
            s.commit()
