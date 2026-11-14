from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from mediafactory.db.base import Base, utcnow

ROLES = ("admin", "editor")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role in ('admin','editor')", name="role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="editor")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Bumped on logout and password reset; sessions carrying an older epoch are rejected.
    session_epoch: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
