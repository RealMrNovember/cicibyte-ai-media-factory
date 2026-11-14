from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_admin, require_user
from mediafactory.audit.service import record_audit
from mediafactory.auth import sessions
from mediafactory.auth.service import RateLimited, authenticate, end_all_sessions
from mediafactory.db.models import User

router = APIRouter(prefix="/api", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


def user_out(user: User) -> dict:
    return {"id": user.id, "email": user.email, "role": user.role}


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db, scope="function")) -> dict:
    ip = client_ip(request)
    try:
        user = authenticate(db, body.email, body.password, ip)
    except RateLimited:
        record_audit(db, actor_id=None, action="auth.login_blocked", details={"email": body.email}, ip=ip)
        db.commit()
        raise HTTPException(status_code=429, detail="too many failed attempts, try again later") from None
    if user is None:
        record_audit(db, actor_id=None, action="auth.login_failed", details={"email": body.email}, ip=ip)
        db.commit()
        raise HTTPException(status_code=401, detail="invalid email or password")
    record_audit(db, actor_id=user.id, action="auth.login", ip=ip)
    sessions.issue(response, request, user.id, user.session_epoch or 0)
    return {"user": user_out(user)}


@router.post("/auth/logout")
def logout(
    request: Request, response: Response, user: User = Depends(require_user), db: Session = Depends(get_db, scope="function")
) -> dict:
    record_audit(db, actor_id=user.id, action="auth.logout", ip=client_ip(request))
    end_all_sessions(user)
    sessions.clear(response)
    return {"ok": True}


@router.get("/auth/me")
def me(user: User = Depends(require_user)) -> dict:
    return user_out(user)


@router.get("/admin/ping")
def admin_ping(user: User = Depends(require_admin)) -> dict:
    return {"ok": True}
