from collections.abc import Callable

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def save_unique(db: Session, apply: Callable[[], None], conflict_detail: str) -> None:
    """Apply changes inside a SAVEPOINT and flush; a unique-constraint conflict becomes HTTP 409 and leaves the
    rest of the request's session usable (the change is rolled back, other work is kept).

    The changes must be made inside `apply`: begin_nested() flushes pending state before opening the
    savepoint, so anything added earlier would fail outside of it.
    """
    try:
        with db.begin_nested():
            apply()
            db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail=conflict_detail) from None
