"""Record the private object key for each persisted analysis image.

Revision ID: 0004_analysis_storage_reference
Revises: 0003_analysis_ownership
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_analysis_storage_reference"
down_revision: Union[str, None] = "0003_analysis_ownership"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("image_object_key", sa.String(length=512), nullable=False))
    op.create_index("uq_analyses_image_object_key", "analyses", ["image_object_key"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_analyses_image_object_key", table_name="analyses")
    op.drop_column("analyses", "image_object_key")
