"""schedules: run every N minutes within an optional daily window

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-14 14:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("schedules", sa.Column("interval_min", sa.Integer(), nullable=True))
    op.add_column("schedules", sa.Column("window", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("schedules", "window")
    op.drop_column("schedules", "interval_min")
