from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_admin
from mediafactory.audit.service import record_audit
from mediafactory.db.models import User
from mediafactory.sources.credentials import delete_reddit_credentials, get_reddit_credentials, set_reddit_credentials

router = APIRouter(prefix="/api/source-credentials", tags=["sources"])


class RedditCredentialsIn(BaseModel):
    client_id: str = Field(min_length=3, max_length=200)
    client_secret: str = Field(min_length=3, max_length=500)


def _status(db: Session) -> dict:
    creds = get_reddit_credentials(db)
    return {"reddit": {"configured": creds is not None, "client_id": creds["client_id"] if creds else None}}


@router.get("")
def get_status(db: Session = Depends(get_db, scope="function"), user: User = Depends(require_admin)) -> dict:
    return _status(db)


@router.put("/reddit")
def put_reddit(
    body: RedditCredentialsIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_admin),
) -> dict:
    set_reddit_credentials(db, body.client_id, body.client_secret)
    record_audit(
        db, actor_id=user.id, action="source_credentials.update", target_type="source_credentials",
        target_id="reddit", details={"client_id": body.client_id}, ip=client_ip(request),
    )  # fmt: skip
    return _status(db)


@router.delete("/reddit", status_code=204)
def delete_reddit(
    request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_admin)
) -> Response:
    delete_reddit_credentials(db)
    record_audit(
        db, actor_id=user.id, action="source_credentials.delete", target_type="source_credentials",
        target_id="reddit", ip=client_ip(request),
    )  # fmt: skip
    return Response(status_code=204)
