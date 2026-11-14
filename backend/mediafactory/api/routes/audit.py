from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from mediafactory.api.deps import get_db, require_admin
from mediafactory.db.models import AuditLog, User

router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/audit")
def list_audit(
    limit: int = Query(50, ge=1, le=500),
    before_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    q = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    if before_id is not None:
        q = q.where(AuditLog.id < before_id)
    rows = db.scalars(q).all()
    return {
        "items": [
            {
                "id": r.id,
                "at": r.at.isoformat(),
                "actor_id": r.actor_id,
                "action": r.action,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "details": r.details,
                "ip": r.ip,
            }
            for r in rows
        ]
    }
