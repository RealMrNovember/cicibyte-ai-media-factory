from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from mediafactory.auth import sessions
from mediafactory.db.models import User
from mediafactory.db.session import SessionLocal

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def require_user(request: Request, db: Session = Depends(get_db, scope="function")) -> User:
    found = sessions.read_session(request)
    user = db.get(User, found[0]) if found is not None else None
    if user is None or not user.is_active or user.session_epoch != found[1]:
        raise HTTPException(status_code=401, detail="not authenticated")
    if request.method in UNSAFE_METHODS and not sessions.csrf_ok(request):
        raise HTTPException(status_code=403, detail="csrf token missing or invalid")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")
    return user


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
