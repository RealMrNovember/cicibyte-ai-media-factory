from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mediafactory.db.base import Base, utcnow

SCHEDULE_KINDS = ("produce", "publish", "autopilot")


class Schedule(Base):
    """A recurring task: produce videos, or publish approved ones to YouTube, at given times of day."""

    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(16))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    times: Mapped[list] = mapped_column(JSONB, default=list)  # ["09:00", "18:30"]
    weekdays: Mapped[list] = mapped_column(JSONB, default=lambda: [0, 1, 2, 3, 4, 5, 6])  # Monday = 0
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    # Either fixed `times`, or every `interval_min` minutes inside an optional daily `window` ["09:00", "23:00"].
    interval_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    window: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    params: Mapped[dict] = mapped_column(JSONB, default=dict)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class YouTubeChannel(Base):
    __tablename__ = "youtube_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    thumbnail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    refresh_token_enc: Mapped[str] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
