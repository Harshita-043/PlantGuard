"""Create the analyses table.

Revision ID: 0001_initial_analysis
Revises:
Create Date: 2026-09-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial_analysis"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("image_content_type", sa.String(length=32), nullable=False),
        sa.Column("image_size_bytes", sa.Integer(), nullable=False),
        sa.Column("result_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("image_size_bytes > 0 AND image_size_bytes <= 10485760", name="ck_analyses_image_size"),
        sa.CheckConstraint(
            "image_content_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_analyses_image_content_type",
        ),
        sa.CheckConstraint("status IN ('pending', 'completed', 'failed')", name="ck_analyses_status"),
        sa.PrimaryKeyConstraint("id", name="pk_analyses"),
    )
    op.create_index("ix_analyses_created_at", "analyses", ["created_at"], unique=False)
    op.create_index("ix_analyses_status_created_at", "analyses", ["status", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_analyses_status_created_at", table_name="analyses")
    op.drop_index("ix_analyses_created_at", table_name="analyses")
    op.drop_table("analyses")
