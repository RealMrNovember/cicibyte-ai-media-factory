"""Signed session cookie + double-submit CSRF token."""

import secrets

from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from mediafactory.core.config import get_settings

SESSION_COOKIE = "mf_session"
CSRF_COOKIE = "mf_csrf"
CSRF_HEADER = "X-CSRF-Token"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key.get_secret_value(), salt="mf-session")


def issue(response: Response, request: Request, user_id: int, epoch: int = 0) -> None:
    settings = get_settings()
    max_age = settings.session_ttl_hours * 3600
    secure = request.url.scheme == "https"
    token = _serializer().dumps({"uid": user_id, "ep": epoch})
    response.set_cookie(SESSION_COOKIE, token, max_age=max_age, httponly=True, samesite="strict", secure=secure)
    response.set_cookie(
        CSRF_COOKIE, secrets.token_urlsafe(32), max_age=max_age, httponly=False, samesite="strict", secure=secure
    )


def clear(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie(CSRF_COOKIE)


def read_session(request: Request) -> tuple[int, int] | None:
    """Return (user_id, epoch) from a valid session cookie, else None."""
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    try:
        data = _serializer().loads(raw, max_age=get_settings().session_ttl_hours * 3600)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(data, dict):
        return None
    uid, epoch = data.get("uid"), data.get("ep", 0)
    if not isinstance(uid, int) or not isinstance(epoch, int):
        return None
    return uid, epoch


def csrf_ok(request: Request) -> bool:
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get(CSRF_HEADER)
    return bool(cookie) and bool(header) and secrets.compare_digest(cookie, header)
