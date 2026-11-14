from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from mediafactory.db.base import Base


class HostRateLimit(Base):
    """Per-host request spacing and 429 cooldown, shared by every process (api, worker)."""

    __tablename__ = "host_rate_limits"

    host: Mapped[str] = mapped_column(String(255), primary_key=True)
    last_request_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
