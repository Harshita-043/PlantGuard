"""Analysis ownership tests using the real auth and ownership dependencies."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.auth import router as auth_router
from app.api.v1.auth import get_db
from app.api.v1.ownership import get_owned_analysis
from app.core.config import settings
from app.core.database import Base
from app.models.analysis import Analysis
from app.models.user import User


@pytest.fixture
def ownership_client(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", SecretStr("ownership-test-secret-" + "x" * 32))
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        with sessions() as db:
            yield db

    test_app = FastAPI()
    test_app.include_router(auth_router, prefix="/api/v1")

    @test_app.get("/test/analyses/{analysis_id}")
    def read_analysis(analysis: Analysis = Depends(get_owned_analysis)):
        return {"id": str(analysis.id)}

    test_app.dependency_overrides[get_db] = override_get_db
    with TestClient(test_app) as client:
        yield client, sessions
    test_app.dependency_overrides.clear()
    engine.dispose()


def create_account(client: TestClient, email: str) -> tuple[str, str]:
    password = "a test password with enough length"
    registration = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registration.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return registration.json()["id"], login.json()["access_token"]


def create_analysis(sessions, owner_id: str) -> Analysis:
    with sessions() as db:
        analysis = Analysis(
            user_id=UUID(owner_id),
            image_object_key=f"users/{owner_id}/analyses/{uuid4()}/image",
            image_content_type="image/png",
            image_size_bytes=100,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis


def test_authenticated_owner_can_resolve_analysis_and_other_user_cannot(ownership_client):
    client, sessions = ownership_client
    user_a_id, token_a = create_account(client, "owner-a@example.com")
    _user_b_id, token_b = create_account(client, "owner-b@example.com")
    analysis = create_analysis(sessions, user_a_id)

    own_response = client.get(
        f"/test/analyses/{analysis.id}", headers={"Authorization": f"Bearer {token_a}"}
    )
    foreign_response = client.get(
        f"/test/analyses/{analysis.id}", headers={"Authorization": f"Bearer {token_b}"}
    )
    missing_response = client.get(
        f"/test/analyses/{uuid4()}", headers={"Authorization": f"Bearer {token_b}"}
    )

    assert own_response.status_code == 200
    assert own_response.json() == {"id": str(analysis.id)}
    assert foreign_response.status_code == missing_response.status_code == 404
    assert foreign_response.json() == missing_response.json() == {"detail": "Resource not found"}
    assert "user_id" not in own_response.text


def test_analysis_ownership_requires_authentication(ownership_client):
    client, sessions = ownership_client
    user_id, _token = create_account(client, "anonymous-check@example.com")
    analysis = create_analysis(sessions, user_id)

    response = client.get(f"/test/analyses/{analysis.id}")

    assert response.status_code == 401


def test_analysis_owner_foreign_key_rejects_missing_user_and_prevents_orphaning(ownership_client):
    _client, sessions = ownership_client
    with sessions() as db:
        orphan = Analysis(
            user_id=uuid4(),
            image_object_key=f"users/orphan/analyses/{uuid4()}/image",
            image_content_type="image/png",
            image_size_bytes=100,
        )
        db.add(orphan)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        owner = User(email="delete-owner@example.com", password_hash="test-only-hash")
        db.add(owner)
        db.commit()
        analysis = Analysis(
            user_id=owner.id,
            image_object_key=f"users/{owner.id}/analyses/{uuid4()}/image",
            image_content_type="image/png",
            image_size_bytes=100,
        )
        db.add(analysis)
        db.commit()

        db.delete(owner)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert db.get(User, owner.id) is not None
        assert db.get(Analysis, analysis.id) is not None
