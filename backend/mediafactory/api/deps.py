import secrets
from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from mediafactory.db.models import User
from mediafactory.db.session import SessionLocal

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CLIENT_HEADER = "X-MF-Client"
OWNER_EMAIL = "owner@local"


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


def owner_user(db: Session) -> User:
    """The single owner of this installation; created on first use. There is no sign-in."""
    user = db.scalar(select(User).where(User.role == "admin", User.is_active.is_(True)).order_by(User.id).limit(1))
    if user is None:
        from sqlalchemy.exc import IntegrityError

        from mediafactory.auth.passwords import hash_password

        user = User(email=OWNER_EMAIL, role="admin", password_hash=hash_password(secrets.token_urlsafe(32)))
        try:
            with db.begin_nested():  # several first requests at once (the app's first start): one wins
                db.add(user)
                db.flush()
        except IntegrityError:
            user = db.scalar(select(User).where(User.email == OWNER_EMAIL))
    return user


def require_user(request: Request, db: Session = Depends(get_db, scope="function")) -> User:
    # A custom header cannot be sent cross-site without a CORS preflight (which this server never grants),
    # so requiring it on writes blocks drive-by requests from other web pages.
    if request.method in UNSAFE_METHODS and not request.headers.get(CLIENT_HEADER):
        raise HTTPException(status_code=403, detail=f"missing {CLIENT_HEADER} header")
    return owner_user(db)


def require_admin(user: User = Depends(require_user)) -> User:
    return user


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
