"""Dashboard metrics are derived only from persisted records owned by the user."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.auth import get_current_user
from app.core.database import Base, get_db
from app.main import app
from app.models import Analysis, Plant, User


def _result(analysis_id, status, score, breakdown=None):
    return {
        "schema_version": "2.0.0",
        "analysis_id": str(analysis_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "hardware_device": "cpu",
        "processing_time_ms": 1,
        "model_versions": {},
        "stage_timings_ms": {},
        "model_load_timings_ms": {},
        "leaves": [],
        "plant_summary": {
            "overall_health_score": score,
            "health_status": status,
            "total_leaves_detected": 1,
            "valid_leaves_analyzed": 1,
            "healthy_leaves_count": 1 if status == "healthy" else 0,
            "diseased_leaves_count": 1 if status in {"mildly_diseased", "severely_diseased"} else 0,
            "primary_diagnosis": next(iter(breakdown), None) if breakdown else None,
            "disease_breakdown": breakdown or {},
            "average_severity_percentage": 0.0,
            "recommendations": [],
        },
        "warnings": [],
        "partial_failures": [],
    }


@pytest.fixture
def dashboard_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    owner = User(email="owner@example.test", password_hash="test-hash")
    other = User(email="other@example.test", password_hash="test-hash")
    with session_factory() as session:
        session.add_all([owner, other])
        session.flush()
        plant = Plant(user_id=owner.id, name="Window basil")
        session.add(plant)
        session.flush()
        now = datetime.now(timezone.utc)
        rows = [
            Analysis(
                user_id=owner.id,
                plant_id=plant.id,
                image_object_key=f"test/{uuid4()}",
                status="completed",
                image_content_type="image/jpeg",
                image_size_bytes=100,
                result_data=_result(uuid4(), "healthy", 90.0),
                created_at=now,
            ),
            Analysis(
                user_id=owner.id,
                image_object_key=f"test/{uuid4()}",
                status="completed",
                image_content_type="image/jpeg",
                image_size_bytes=100,
                result_data=_result(uuid4(), "mildly_diseased", 70.0, {"leaf spot": 2}),
                created_at=now,
            ),
            Analysis(
                user_id=owner.id,
                image_object_key=f"test/{uuid4()}",
                status="completed",
                image_content_type="image/jpeg",
                image_size_bytes=100,
                result_data=None,
                created_at=now,
            ),
            Analysis(
                user_id=owner.id,
                image_object_key=f"test/{uuid4()}",
                status="completed",
                image_content_type="image/jpeg",
                image_size_bytes=100,
                result_data=_result(uuid4(), "unknown", 50.0),
                created_at=now,
            ),
            Analysis(
                user_id=owner.id,
                image_object_key=f"test/{uuid4()}",
                status="failed",
                image_content_type="image/jpeg",
                image_size_bytes=100,
                failure_data={
                    "code": "model_unavailable",
                    "stage": "classifier",
                    "message": "Inference unavailable",
                    "occurred_at": now.isoformat(),
                },
                created_at=now,
            ),
            Analysis(
                user_id=other.id,
                image_object_key=f"test/{uuid4()}",
                status="completed",
                image_content_type="image/jpeg",
                image_size_bytes=100,
                result_data=_result(uuid4(), "healthy", 100.0),
                created_at=now,
            ),
        ]
        session.add_all(rows)
        session.commit()

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: owner
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_dashboard_metrics_are_real_and_user_scoped(dashboard_client):
    response = dashboard_client.get("/api/v1/dashboard/metrics")

    assert response.status_code == 200
    metrics = response.json()
    assert metrics["total_analyses"] == 5
    assert metrics["healthy_analyses"] == 1
    assert metrics["diseased_analyses"] == 1
    assert metrics["inconclusive_analyses"] == 2
    assert metrics["failed_analyses"] == 1
    assert metrics["total_plants"] == 1
    assert metrics["average_health_score"] == pytest.approx(70.0)
    assert metrics["disease_distribution"] == {"leaf spot": 2}
    assert len(metrics["recent_scans"]) == 5
    assert len(metrics["health_trend"]) == 3


def test_dashboard_metrics_have_safe_empty_values():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    owner = User(email="empty@example.test", password_hash="test-hash")
    with session_factory() as session:
        session.add(owner)
        session.commit()

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: owner
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/dashboard/metrics")
        assert response.status_code == 200
        assert response.json()["total_analyses"] == 0
        assert response.json()["average_health_score"] is None
        assert response.json()["recent_scans"] == []
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
