from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_admin, require_user
from mediafactory.auth import sessions
from mediafactory.auth.service import RateLimited, authenticate
from mediafactory.db.models import User

router = APIRouter(prefix="/api", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


def user_out(user: User) -> dict:
    return {"id": user.id, "email": user.email, "role": user.role}


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    try:
        user = authenticate(db, body.email, body.password, client_ip(request))
    except RateLimited:
        raise HTTPException(status_code=429, detail="too many failed attempts, try again later") from None
    if user is None:
        raise HTTPException(status_code=401, detail="invalid email or password")
    sessions.issue(response, request, user.id)
    return {"user": user_out(user)}


@router.post("/auth/logout")
def logout(response: Response, user: User = Depends(require_user)) -> dict:
    sessions.clear(response)
    return {"ok": True}


@router.get("/auth/me")
def me(user: User = Depends(require_user)) -> dict:
    return user_out(user)


@router.get("/admin/ping")
def admin_ping(user: User = Depends(require_admin)) -> dict:
    return {"ok": True}
