from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mediafactory.db.base import Base, utcnow

# Spec §13 state machine.
JOB_STATUSES = (
    "discovered", "normalized", "classified", "rights_review", "script_draft", "script_approved",
    "voice_generated", "subtitles_generated", "visuals_ready", "rendering", "quality_check",
    "needs_review", "approved", "scheduled", "uploading", "published",
    "rejected", "failed", "retry_wait", "archived",
)  # fmt: skip
JOB_CLASSES = ("llm", "tts", "stt", "render", "io")
RUN_STATES = ("queued", "running", "succeeded", "failed", "retry_wait", "cancelled")


class ProductionJob(Base):
    __tablename__ = "production_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="discovered", index=True)
    concept_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    content_group: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class JobStageRun(Base):
    __tablename__ = "job_stage_runs"
    __table_args__ = (Index("ix_job_stage_runs_claim", "state", "job_class", "run_after"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("production_jobs.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(50))
    job_class: Mapped[str] = mapped_column(String(16))
    state: Mapped[str] = mapped_column(String(16), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inputs: Mapped[dict] = mapped_column(JSONB, default=dict)
    outputs: Mapped[dict] = mapped_column(JSONB, default=dict)
    log: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
