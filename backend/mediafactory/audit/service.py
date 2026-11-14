from typing import Any

from sqlalchemy.orm import Session

from mediafactory.core.redact import redact
from mediafactory.db.models import AuditLog

_SENSITIVE_KEYS = {"api_key", "apikey", "key", "token", "access_token", "refresh_token", "secret", "password"}


def _clean(value: Any, key: str | None = None) -> Any:
    if key is not None and key.lower() in _SENSITIVE_KEYS and value not in (None, ""):
        return "****"
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {k: _clean(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


def record_audit(
    session: Session,
    *,
    actor_id: int | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict | None = None,
    ip: str | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=None if target_id is None else str(target_id),
            details=_clean(details) if details else None,
            ip=ip,
        )
    )
