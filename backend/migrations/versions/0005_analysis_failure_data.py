"""Retain structured safe failure details for completed scan attempts.

Revision ID: 0005_analysis_failure_data
Revises: 0004_analysis_storage_reference
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0005_analysis_failure_data"
down_revision: Union[str, None] = "0004_analysis_storage_reference"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column(
            "failure_data",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("analyses", "failure_data")
