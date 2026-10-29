"""Plant CRUD and scan associations enforce account ownership."""

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
from app.models import Analysis, User


@pytest.fixture
def plant_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    owner = User(email="plant-owner@example.test", password_hash="test-hash")
    other = User(email="plant-other@example.test", password_hash="test-hash")
    with session_factory() as session:
        session.add_all([owner, other])
        session.commit()

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: owner
    try:
        with TestClient(app) as client:
            yield client, owner, other, session_factory
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_plant_crud_and_nullable_metadata(plant_client):
    client, _, _, _ = plant_client
    created = client.post(
        "/api/v1/plants",
        json={"name": "Basil", "species": "Ocimum basilicum", "location": "Kitchen"},
    )

    assert created.status_code == 201
    plant = created.json()
    assert plant["name"] == "Basil"
    assert plant["total_scans"] == 0

    listed = client.get("/api/v1/plants")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [plant["id"]]

    updated = client.patch(
        f"/api/v1/plants/{plant['id']}",
        json={"name": "Kitchen basil", "species": None},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Kitchen basil"
    assert updated.json()["species"] is None

    detail = client.get(f"/api/v1/plants/{plant['id']}")
    assert detail.status_code == 200
    assert detail.json()["recent_scans"] == []

    deleted = client.delete(f"/api/v1/plants/{plant['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/plants/{plant['id']}").status_code == 404


def test_plant_scan_association_is_owner_scoped(plant_client):
    client, owner, other, session_factory = plant_client
    plant_response = client.post("/api/v1/plants", json={"name": "Tomato"})
    plant_id = plant_response.json()["id"]
    own_scan_id = uuid4()
    other_scan_id = uuid4()
    now = datetime.now(timezone.utc)
    with session_factory() as session:
        session.add_all(
            [
                Analysis(
                    id=own_scan_id,
                    user_id=owner.id,
                    image_object_key=f"test/{uuid4()}",
                    status="pending",
                    image_content_type="image/jpeg",
                    image_size_bytes=100,
                    created_at=now,
                ),
                Analysis(
                    id=other_scan_id,
                    user_id=other.id,
                    image_object_key=f"test/{uuid4()}",
                    status="pending",
                    image_content_type="image/jpeg",
                    image_size_bytes=100,
                    created_at=now,
                ),
            ]
        )
        session.commit()

    associated = client.post(
        f"/api/v1/plants/{plant_id}/scans/{own_scan_id}"
    )
    assert associated.status_code == 200
    assert associated.json()["plant_id"] == plant_id

    cross_user = client.post(
        f"/api/v1/plants/{plant_id}/scans/{other_scan_id}"
    )
    assert cross_user.status_code == 404

    unlinked = client.delete(
        f"/api/v1/plants/{plant_id}/scans/{own_scan_id}"
    )
    assert unlinked.status_code == 200
    assert unlinked.json()["plant_id"] is None


def test_foreign_plant_is_not_visible_or_mutable(plant_client):
    client, _, other, session_factory = plant_client
    from app.models import Plant

    foreign_id = uuid4()
    with session_factory() as session:
        session.add(Plant(id=foreign_id, user_id=other.id, name="Private plant"))
        session.commit()

    assert client.get(f"/api/v1/plants/{foreign_id}").status_code == 404
    assert client.patch(
        f"/api/v1/plants/{foreign_id}", json={"name": "Changed"}
    ).status_code == 404
    assert client.delete(f"/api/v1/plants/{foreign_id}").status_code == 404
    assert all(plant["id"] != str(foreign_id) for plant in client.get("/api/v1/plants").json())
