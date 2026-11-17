from sqlalchemy import select

from mediafactory.api import deps
from mediafactory.db.models import User


def test_owner_creation_survives_a_parallel_first_request(db, monkeypatch):
    """Two first requests at once: the one that loses the insert race must use the winner's row, not fail."""
    real_scalar = db.scalar
    calls = {"n": 0}

    def scalar(stmt, *a, **kw):
        calls["n"] += 1
        if calls["n"] == 1:  # our first look sees no owner, but another request inserts it right now
            other = User(email=deps.OWNER_EMAIL, role="admin", password_hash="x")
            with db.begin_nested():
                db.add(other)
            return None
        return real_scalar(stmt, *a, **kw)

    monkeypatch.setattr(db, "scalar", scalar)
    user = deps.owner_user(db)
    monkeypatch.undo()
    assert user.email == deps.OWNER_EMAIL
    assert len(db.scalars(select(User).where(User.email == deps.OWNER_EMAIL)).all()) == 1
