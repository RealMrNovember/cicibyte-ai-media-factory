"""shared per-host rate limits

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-14 08:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "host_rate_limits",
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("last_request_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("host", name=op.f("pk_host_rate_limits")),
    )


def downgrade() -> None:
    op.drop_table("host_rate_limits")
