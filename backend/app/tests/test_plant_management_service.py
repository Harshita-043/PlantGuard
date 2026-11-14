"""Dedicated unit and integration tests for ApplicationPlantManagementService."""
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.analysis import Analysis
from app.models.plant import Plant
from app.models.user import User
from app.schemas.plant import PlantCreate, PlantUpdate
from app.services.interfaces.plant_management import (
    AnalysisScanNotFoundError,
    PlantNotFoundError,
    ScanNotAssociatedWithPlantError,
)
from app.services.plant_management_service import ApplicationPlantManagementService


@pytest.fixture
def service_db_session():
    """In-memory SQLite session with full metadata."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def service_users(service_db_session):
    """Two persisted test users."""
    user_a = User(id=uuid4(), email="user-a@example.test", password_hash="hash-a")
    user_b = User(id=uuid4(), email="user-b@example.test", password_hash="hash-b")
    service_db_session.add_all([user_a, user_b])
    service_db_session.commit()
    return user_a, user_b


def test_create_plant_successfully(service_db_session, service_users):
    user_a, _ = service_users
    service = ApplicationPlantManagementService(db=service_db_session)

    payload = PlantCreate(
        name="Monstera Deliciosa",
        species="Monstera deliciosa",
        location="Living Room",
        notes="Water once a week",
    )
    result = service.create_plant(user_id=user_a.id, payload=payload)

    assert result.id is not None
    assert result.user_id == user_a.id
    assert result.name == "Monstera Deliciosa"
    assert result.species == "Monstera deliciosa"
    assert result.location == "Living Room"
    assert result.notes == "Water once a week"
    assert result.total_scans == 0
    assert result.latest_analysis is None
    assert result.health_status is None


def test_retrieve_plant_successfully(service_db_session, service_users):
    user_a, _ = service_users
    service = ApplicationPlantManagementService(db=service_db_session)

    created = service.create_plant(
        user_id=user_a.id,
        payload=PlantCreate(name="Ficus", species="Ficus lyrata"),
    )

    retrieved = service.get_plant(plant_id=created.id, user_id=user_a.id)
    assert retrieved.id == created.id
    assert retrieved.name == "Ficus"
    assert retrieved.species == "Ficus lyrata"


def test_list_only_plants_owned_by_requesting_user(service_db_session, service_users):
    user_a, user_b = service_users
    service = ApplicationPlantManagementService(db=service_db_session)

    # User A creates 2 plants
    plant_a1 = service.create_plant(user_id=user_a.id, payload=PlantCreate(name="Plant A1"))
    plant_a2 = service.create_plant(user_id=user_a.id, payload=PlantCreate(name="Plant A2"))

    # User B creates 1 plant
    plant_b1 = service.create_plant(user_id=user_b.id, payload=PlantCreate(name="Plant B1"))

    plants_a = service.list_user_plants(user_id=user_a.id)
    assert len(plants_a) == 2
    ids_a = [p.id for p in plants_a]
    assert plant_a1.id in ids_a
    assert plant_a2.id in ids_a
    assert plant_b1.id not in ids_a

    plants_b = service.list_user_plants(user_id=user_b.id)
    assert len(plants_b) == 1
    assert plants_b[0].id == plant_b1.id


def test_update_plant_successfully(service_db_session, service_users):
    user_a, _ = service_users
    service = ApplicationPlantManagementService(db=service_db_session)

    created = service.create_plant(
        user_id=user_a.id,
        payload=PlantCreate(name="Fern", location="Bathroom"),
    )

    updated = service.update_plant(
        plant_id=created.id,
        user_id=user_a.id,
        payload=PlantUpdate(name="Boston Fern", location="Balcony"),
    )

    assert updated.id == created.id
    assert updated.name == "Boston Fern"
    assert updated.location == "Balcony"


def test_partial_update_preserves_unspecified_fields(service_db_session, service_users):
    user_a, _ = service_users
    service = ApplicationPlantManagementService(db=service_db_session)

    created = service.create_plant(
        user_id=user_a.id,
        payload=PlantCreate(
            name="Snake Plant",
            species="Sansevieria",
            location="Bedroom",
            notes="Requires low light",
        ),
    )

    # Only update name; species, location and notes must be preserved
    updated = service.update_plant(
        plant_id=created.id,
        user_id=user_a.id,
        payload=PlantUpdate(name="Sansevieria Trifasciata"),
    )

    assert updated.name == "Sansevieria Trifasciata"
    assert updated.species == "Sansevieria"
    assert updated.location == "Bedroom"
    assert updated.notes == "Requires low light"


def test_delete_plant_successfully(service_db_session, service_users):
    user_a, _ = service_users
    service = ApplicationPlantManagementService(db=service_db_session)

    created = service.create_plant(
        user_id=user_a.id,
        payload=PlantCreate(name="Pothos"),
    )

    service.delete_plant(plant_id=created.id, user_id=user_a.id)

    with pytest.raises(PlantNotFoundError):
        service.get_plant(plant_id=created.id, user_id=user_a.id)


def test_retrieve_nonexistent_plant(service_db_session, service_users):
    user_a, _ = service_users
    service = ApplicationPlantManagementService(db=service_db_session)

    with pytest.raises(PlantNotFoundError):
        service.get_plant(plant_id=uuid4(), user_id=user_a.id)


def test_update_nonexistent_plant(service_db_session, service_users):
    user_a, _ = service_users
    service = ApplicationPlantManagementService(db=service_db_session)

    with pytest.raises(PlantNotFoundError):
        service.update_plant(
            plant_id=uuid4(),
            user_id=user_a.id,
            payload=PlantUpdate(name="Ghost Plant"),
        )


def test_delete_nonexistent_plant(service_db_session, service_users):
    user_a, _ = service_users
    service = ApplicationPlantManagementService(db=service_db_session)

    with pytest.raises(PlantNotFoundError):
        service.delete_plant(plant_id=uuid4(), user_id=user_a.id)


def test_prevent_access_to_another_users_plant(service_db_session, service_users):
    user_a, user_b = service_users
    service = ApplicationPlantManagementService(db=service_db_session)

    plant_a = service.create_plant(
        user_id=user_a.id,
        payload=PlantCreate(name="User A Secret Plant"),
    )

    # User B cannot retrieve User A's plant
    with pytest.raises(PlantNotFoundError):
        service.get_plant(plant_id=plant_a.id, user_id=user_b.id)

    # User B cannot get detail of User A's plant
    with pytest.raises(PlantNotFoundError):
        service.get_plant_detail(plant_id=plant_a.id, user_id=user_b.id)

    # User B cannot update User A's plant
    with pytest.raises(PlantNotFoundError):
        service.update_plant(
            plant_id=plant_a.id,
            user_id=user_b.id,
            payload=PlantUpdate(name="Hijacked Plant"),
        )

    # User B cannot delete User A's plant
    with pytest.raises(PlantNotFoundError):
        service.delete_plant(plant_id=plant_a.id, user_id=user_b.id)


def test_prevent_changing_ownership_through_request_input(service_db_session, service_users):
    user_a, user_b = service_users
    service = ApplicationPlantManagementService(db=service_db_session)

    created = service.create_plant(
        user_id=user_a.id,
        payload=PlantCreate(name="Original Owner Plant"),
    )

    # PlantUpdate has no user_id field; even if caller attempts to update, user_id remains user_a
    service.update_plant(
        plant_id=created.id,
        user_id=user_a.id,
        payload=PlantUpdate(name="Renamed Plant"),
    )

    plant_entity = service_db_session.scalar(
        select(Plant).where(Plant.id == created.id)
    )
    assert plant_entity is not None
    assert plant_entity.user_id == user_a.id
    assert plant_entity.user_id != user_b.id


def test_handle_database_errors_correctly(service_db_session, service_users):
    user_a, _ = service_users
    # Mock a session where commit fails
    mock_session = MagicMock()
    mock_session.commit.side_effect = RuntimeError("Database connection lost")

    service = ApplicationPlantManagementService(db=mock_session)
    with pytest.raises(RuntimeError, match="Database connection lost"):
        service.create_plant(user_id=user_a.id, payload=PlantCreate(name="Fail Plant"))


def test_delete_plant_preserves_associated_analysis_records(service_db_session, service_users):
    user_a, _ = service_users
    service = ApplicationPlantManagementService(db=service_db_session)

    plant = service.create_plant(user_id=user_a.id, payload=PlantCreate(name="Rose"))

    scan1_id = uuid4()
    scan2_id = uuid4()
    now = datetime.now(timezone.utc)

    scan1 = Analysis(
        id=scan1_id,
        user_id=user_a.id,
        plant_id=plant.id,
        image_object_key=f"scans/{scan1_id}",
        status="completed",
        image_content_type="image/jpeg",
        image_size_bytes=1024,
        result_data={"plant_summary": {"health_status": "Healthy", "overall_health_score": 95.0}},
        created_at=now,
    )
    scan2 = Analysis(
        id=scan2_id,
        user_id=user_a.id,
        plant_id=plant.id,
        image_object_key=f"scans/{scan2_id}",
        status="completed",
        image_content_type="image/jpeg",
        image_size_bytes=2048,
        result_data={"plant_summary": {"health_status": "Diseased", "overall_health_score": 45.0}},
        created_at=now,
    )
    service_db_session.add_all([scan1, scan2])
    service_db_session.commit()

    # Verify detail shows 2 scans and trend
    detail = service.get_plant_detail(plant_id=plant.id, user_id=user_a.id)
    assert detail.total_scans == 2
    assert len(detail.recent_scans) == 2
    assert len(detail.health_trend) == 2

    # Delete plant
    service.delete_plant(plant_id=plant.id, user_id=user_a.id)

    # Verify plant is gone
    with pytest.raises(PlantNotFoundError):
        service.get_plant(plant_id=plant.id, user_id=user_a.id)

    # Crucial check: verify both analysis scans still exist and plant_id is null
    persisted_scan1 = service_db_session.scalar(select(Analysis).where(Analysis.id == scan1_id))
    persisted_scan2 = service_db_session.scalar(select(Analysis).where(Analysis.id == scan2_id))
    assert persisted_scan1 is not None
    assert persisted_scan1.plant_id is None
    assert persisted_scan2 is not None
    assert persisted_scan2.plant_id is None


def test_scan_association_and_disassociation_flow(service_db_session, service_users):
    user_a, user_b = service_users
    service = ApplicationPlantManagementService(db=service_db_session)

    plant = service.create_plant(user_id=user_a.id, payload=PlantCreate(name="Aloe"))
    scan_id = uuid4()
    foreign_scan_id = uuid4()
    now = datetime.now(timezone.utc)

    scan_a = Analysis(
        id=scan_id,
        user_id=user_a.id,
        image_object_key=f"scans/{scan_id}",
        status="pending",
        image_content_type="image/jpeg",
        image_size_bytes=500,
        created_at=now,
    )
    scan_b = Analysis(
        id=foreign_scan_id,
        user_id=user_b.id,
        image_object_key=f"scans/{foreign_scan_id}",
        status="pending",
        image_content_type="image/jpeg",
        image_size_bytes=500,
        created_at=now,
    )
    service_db_session.add_all([scan_a, scan_b])
    service_db_session.commit()

    # User A cannot link User B's scan
    with pytest.raises(AnalysisScanNotFoundError):
        service.associate_scan(plant_id=plant.id, analysis_id=foreign_scan_id, user_id=user_a.id)

    # Link own scan
    linked = service.associate_scan(plant_id=plant.id, analysis_id=scan_id, user_id=user_a.id)
    assert linked.plant_id == plant.id

    # Disassociate own scan
    unlinked = service.disassociate_scan(plant_id=plant.id, analysis_id=scan_id, user_id=user_a.id)
    assert unlinked.plant_id is None

    # Disassociating when not associated raises ScanNotAssociatedWithPlantError
    with pytest.raises(ScanNotAssociatedWithPlantError):
        service.disassociate_scan(plant_id=plant.id, analysis_id=scan_id, user_id=user_a.id)
