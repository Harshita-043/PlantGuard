"""Database metadata tests; live PostgreSQL check is opt-in."""
import os

import pytest
from sqlalchemy import create_engine, text

from app.core.database import Base
from app.models import Analysis, Plant, User


def test_database_model_metadata_has_only_justified_tables():
    assert set(Base.metadata.tables) == {"analyses", "plants", "users"}
    table = Analysis.__table__
    required_columns = {
        "id",
        "user_id",
        "image_object_key",
        "status",
        "image_content_type",
        "image_size_bytes",
        "result_data",
        "created_at",
        "updated_at",
    }
    assert required_columns <= set(table.columns.keys())
    assert {"ck_analyses_status", "ck_analyses_image_size", "ck_analyses_image_content_type"} <= {
        constraint.name for constraint in table.constraints
    }
    assert {"ix_analyses_created_at", "ix_analyses_status_created_at"} <= {
        index.name for index in table.indexes
    }
    assert "ix_analyses_user_id" in {index.name for index in table.indexes}
    assert "uq_analyses_image_object_key" in {index.name for index in table.indexes}
    owner_fk = next(fk for fk in table.foreign_keys if fk.parent.name == "user_id")
    assert owner_fk.target_fullname == "users.id"
    assert not table.c.user_id.nullable
    assert Analysis.user.property.back_populates == "analyses"
    assert User.analyses.property.back_populates == "user"
    assert Analysis.plant.property.back_populates == "analyses"
    assert Plant.analyses.property.back_populates == "plant"
    assert Plant.user.property.back_populates == "plants"
    assert {"id", "user_id", "name", "species", "location", "notes"} <= set(
        Plant.__table__.columns.keys()
    )


def test_analysis_ids_and_result_use_postgresql_types():
    from sqlalchemy.dialects import postgresql

    assert isinstance(Analysis.__table__.c.id.type.dialect_impl(postgresql.dialect()), postgresql.UUID)
    assert isinstance(Analysis.__table__.c.result_data.type.dialect_impl(postgresql.dialect()), postgresql.JSONB)


def test_user_model_has_authentication_fields_and_unique_email():
    assert {"id", "email", "password_hash", "created_at", "updated_at"} == set(User.__table__.columns.keys())
    assert "uq_users_email" in {constraint.name for constraint in User.__table__.constraints}


def test_postgresql_connection_when_test_database_is_configured():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to verify a live PostgreSQL connection")

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT 1")) == 1
    finally:
        engine.dispose()
