"""Require an owner for persisted analyses.

Revision ID: 0003_analysis_ownership
Revises: 0002_users
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0003_analysis_ownership"
down_revision: Union[str, None] = "0002_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_foreign_key(
        "fk_analyses_user_id_users",
        "analyses",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_index("ix_analyses_user_id", "analyses", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_analyses_user_id", table_name="analyses")
    op.drop_constraint("fk_analyses_user_id_users", "analyses", type_="foreignkey")
    op.drop_column("analyses", "user_id")
