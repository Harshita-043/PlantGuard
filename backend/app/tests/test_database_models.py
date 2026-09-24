"""Database metadata tests; live PostgreSQL check is opt-in."""
import os

import pytest
from sqlalchemy import create_engine, text

from app.core.database import Base
from app.models import Analysis


def test_analysis_model_metadata_has_only_justified_table():
    assert set(Base.metadata.tables) == {"analyses"}
    table = Analysis.__table__
    required_columns = {
        "id",
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


def test_analysis_ids_and_result_use_postgresql_types():
    from sqlalchemy.dialects import postgresql

    assert isinstance(Analysis.__table__.c.id.type.dialect_impl(postgresql.dialect()), postgresql.UUID)
    assert isinstance(Analysis.__table__.c.result_data.type.dialect_impl(postgresql.dialect()), postgresql.JSONB)


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
