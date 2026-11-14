"""Login, with a per-process failed-attempt limiter."""

import threading
import time
from collections import defaultdict, deque

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mediafactory.auth.passwords import verify_password
from mediafactory.db.base import utcnow
from mediafactory.db.models import User

MAX_FAILURES = 5
WINDOW_S = 15 * 60

_failures: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


class RateLimited(Exception):
    pass


def reset_rate_limits() -> None:
    with _lock:
        _failures.clear()


def _key(ip: str | None, email: str) -> str:
    return f"{ip or '-'}|{email.lower()}"


def _recent(key: str, now: float) -> deque[float]:
    q = _failures[key]
    while q and now - q[0] > WINDOW_S:
        q.popleft()
    return q


def authenticate(session: Session, email: str, password: str, ip: str | None) -> User | None:
    """Return the user on success, None on bad credentials; raise RateLimited when blocked."""
    key = _key(ip, email)
    now = time.monotonic()
    with _lock:
        if len(_recent(key, now)) >= MAX_FAILURES:
            raise RateLimited()
    user = session.scalar(select(User).where(func.lower(User.email) == email.lower()))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        with _lock:
            _recent(key, now).append(now)
        return None
    with _lock:
        _failures.pop(key, None)
    user.last_login_at = utcnow()
    return user
