from typing import Any

from sqlalchemy.orm import Session

from mediafactory.core.redact import redact
from mediafactory.db.models import AuditLog

_SENSITIVE_PARTS = ("secret", "password", "passwd", "token", "api_key", "apikey", "credential")


def _sensitive(key: str) -> bool:
    k = key.lower()
    return k == "key" or k.endswith("_key") or any(part in k for part in _SENSITIVE_PARTS)


def _clean(value: Any, key: str | None = None) -> Any:
    if key is not None and _sensitive(key) and value not in (None, ""):
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
