"""youtube channels: daily upload limit, playlist, reconnect flag

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-15 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("youtube_channels", sa.Column("daily_limit", sa.Integer(), server_default="6", nullable=False))
    op.add_column("youtube_channels", sa.Column("playlist_id", sa.String(length=64), nullable=True))
    op.add_column("youtube_channels", sa.Column("needs_reconnect", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("youtube_channels", sa.Column("last_error", sa.Text(), nullable=True))


def downgrade() -> None:
    for col in ("last_error", "needs_reconnect", "playlist_id", "daily_limit"):
        op.drop_column("youtube_channels", col)
