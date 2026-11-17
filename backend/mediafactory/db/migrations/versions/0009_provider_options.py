"""ai providers: per-service options (JSON mode, extra headers, how to check a key)

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-17 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ai_providers", sa.Column("options", JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False))


def downgrade() -> None:
    op.drop_column("ai_providers", "options")
