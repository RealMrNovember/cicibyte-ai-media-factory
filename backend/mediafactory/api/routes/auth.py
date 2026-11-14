"""There is no sign-in: the panel always acts as the installation's owner (see api.deps.owner_user)."""

from fastapi import APIRouter, Depends

from mediafactory.api.deps import require_user
from mediafactory.db.models import User

router = APIRouter(prefix="/api", tags=["auth"])


def user_out(user: User) -> dict:
    return {"id": user.id, "email": user.email, "role": user.role}


@router.get("/auth/me")
def me(user: User = Depends(require_user)) -> dict:
    return user_out(user)
