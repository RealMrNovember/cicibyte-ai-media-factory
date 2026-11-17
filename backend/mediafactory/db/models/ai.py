from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mediafactory.db.base import Base, utcnow

PROVIDER_KINDS = ("openai_compatible", "ollama_native")
LOCALITIES = ("local", "remote")
TASKS = ("script", "classify", "tts", "stt", "image")


class AIProvider(Base):
    __tablename__ = "ai_providers"
    __table_args__ = (
        CheckConstraint("kind in ('openai_compatible','ollama_native')", name="kind"),
        CheckConstraint("locality in ('local','remote')", name="locality"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    kind: Mapped[str] = mapped_column(String(32), default="openai_compatible")
    base_url: Mapped[str] = mapped_column(String(500))
    api_key_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    locality: Mapped[str] = mapped_column(String(8), default="remote")
    timeout_s: Mapped[int] = mapped_column(Integer, default=120)
    max_concurrency: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # Per-service tweaks: json_mode ("auto" | "prompt"), headers ({name: value}), check ("models" | "chat").
    options: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AITaskRoute(Base):
    __tablename__ = "ai_task_routes"
    __table_args__ = (CheckConstraint("task in ('script','classify','tts','stt','image')", name="task"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task: Mapped[str] = mapped_column(String(16), unique=True)
    steps: Mapped[list] = mapped_column(JSONB, default=list)  # [{"provider_id": int, "model": str}]
    rounds: Mapped[int] = mapped_column(Integer, default=3)
    retry_delay_s: Mapped[float] = mapped_column(Float, default=3.0)
