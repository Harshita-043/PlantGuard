"""Add plants entity and plant association on analyses.

Revision ID: 0006_plants
Revises: 0005_analysis_failure_data
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_plants"
down_revision: Union[str, None] = "0005_analysis_failure_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plants",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_plants_user_id_users", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("species", sa.String(128), nullable=True),
        sa.Column("location", sa.String(128), nullable=True),
        sa.Column("notes", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_plants_user_id", "plants", ["user_id"])
    op.create_index("ix_plants_created_at", "plants", ["created_at"])

    op.add_column(
        "analyses",
        sa.Column(
            "plant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("plants.id", name="fk_analyses_plant_id_plants", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_analyses_plant_id", "analyses", ["plant_id"])


def downgrade() -> None:
    op.drop_index("ix_analyses_plant_id", table_name="analyses")
    op.drop_constraint("fk_analyses_plant_id_plants", "analyses", type_="foreignkey")
    op.drop_column("analyses", "plant_id")
    op.drop_index("ix_plants_created_at", table_name="plants")
    op.drop_index("ix_plants_user_id", table_name="plants")
    op.drop_table("plants")

