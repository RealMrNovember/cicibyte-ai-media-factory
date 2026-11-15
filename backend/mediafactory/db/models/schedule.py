from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
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
    daily_limit: Mapped[int] = mapped_column(Integer, default=6, server_default="6")  # uploads per (Pacific) day
    playlist_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # every upload is added to it
    needs_reconnect: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Concept(Base):
    """A channel concept: one recipe (language, topic, voice, look, where to publish) and a stock target.

    Autopilot and publishing schedules can follow a concept; with `ready_buffer` > 0 the server keeps that
    many videos of the concept ready (waiting for review or approved) by producing new ones when needed.
    """

    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
    topic: Mapped[str] = mapped_column(String(20), default="random")
    seconds: Mapped[int] = mapped_column(Integer, default=50)
    style: Mapped[dict] = mapped_column(JSONB, default=dict)
    voice: Mapped[dict] = mapped_column(JSONB, default=dict)
    music: Mapped[dict] = mapped_column(JSONB, default=dict)
    background: Mapped[str] = mapped_column(String(120), default="random")
    youtube_channel_id: Mapped[int | None] = mapped_column(
        ForeignKey("youtube_channels.id", ondelete="SET NULL"), nullable=True
    )
    platforms: Mapped[list] = mapped_column(JSONB, default=lambda: ["youtube"])
    privacy: Mapped[str] = mapped_column(String(10), default="public")
    ready_buffer: Mapped[int] = mapped_column(Integer, default=0)
    auto_approve: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
