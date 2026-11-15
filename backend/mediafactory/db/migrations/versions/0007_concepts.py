"""concepts: per-channel recipes with a ready-video stock target

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-15 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "concepts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("topic", sa.String(length=20), nullable=False),
        sa.Column("seconds", sa.Integer(), nullable=False),
        sa.Column("style", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("voice", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("music", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("background", sa.String(length=120), nullable=False),
        sa.Column("youtube_channel_id", sa.Integer(), nullable=True),
        sa.Column("platforms", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("privacy", sa.String(length=10), nullable=False),
        sa.Column("ready_buffer", sa.Integer(), nullable=False),
        sa.Column("auto_approve", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["youtube_channel_id"], ["youtube_channels.id"], name=op.f("fk_concepts_youtube_channel_id_youtube_channels"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_concepts")),
        sa.UniqueConstraint("name", name=op.f("uq_concepts_name")),
    )


def downgrade() -> None:
    op.drop_table("concepts")
