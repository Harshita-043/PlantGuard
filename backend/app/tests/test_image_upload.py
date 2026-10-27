"""Authenticated scan lifecycle tests with a private local storage adapter."""

import io
import tempfile
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import SecretStr
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import analyze
from app.api.v1.auth import router as auth_router
from app.core.config import settings
from app.core.database import Base, get_db
from app.models.analysis import Analysis
from app.models.user import User
from app.ml.errors import InferenceErrorCode, ModelCapabilityError
from app.schemas.inference import FullScanResult, OverallHealthStatus, PlantHealthSummary
from app.storage import LocalFileObjectStorage, StorageError


def _png_bytes() -> bytes:
    image = Image.new("RGB", (3, 2), color=(10, 20, 30))
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


@pytest.fixture
def lifecycle_client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", SecretStr("scan-test-secret-" + "x" * 32))
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path / "temporary"))
    (tmp_path / "temporary").mkdir()

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

    storage = LocalFileObjectStorage(tmp_path / "objects")
    monkeypatch.setattr(analyze, "create_object_storage", lambda: storage)

    class FakeInference:
        def analyze_bytes(self, _image, *, analysis_id):
            return FullScanResult(
                analysis_id=analysis_id,
                status="completed",
                hardware_device="cpu",
                processing_time_ms=3,
                plant_summary=PlantHealthSummary(
                    overall_health_score=100,
                    health_status=OverallHealthStatus.HEALTHY,
                    total_leaves_detected=0,
                    valid_leaves_analyzed=0,
                    healthy_leaves_count=0,
                    diseased_leaves_count=0,
                    average_severity_percentage=0,
                ),
            )

    monkeypatch.setattr(
        analyze, "create_plant_analysis_service",
        lambda **_kwargs: SimpleNamespace(inference=FakeInference()),
    )
    test_app = FastAPI()
    test_app.include_router(auth_router, prefix="/api/v1")
    test_app.include_router(analyze.router, prefix="/api/v1")
    test_app.dependency_overrides[get_db] = override_get_db

    with TestClient(test_app) as client:
        yield client, sessions, storage, test_app, tmp_path / "temporary"
    test_app.dependency_overrides.clear()
    engine.dispose()


def _create_account(client: TestClient, email: str) -> tuple[str, str]:
    password = "a sufficiently long test password"
    registration = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registration.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return registration.json()["id"], login.json()["access_token"]


def _upload(
    client: TestClient,
    token: str,
    *,
    data: bytes | None = None,
    content_type="image/png",
    filename="leaf.png",
    extra_data: dict[str, str] | None = None,
):
    return client.post(
        "/api/v1/analyze/image",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, data if data is not None else _png_bytes(), content_type)},
        data=extra_data,
    )


def test_anonymous_scan_is_rejected_without_writing_image(lifecycle_client):
    client, sessions, storage, _app, temporary_root = lifecycle_client
    response = client.post("/api/v1/analyze/image", files={"file": ("leaf.png", _png_bytes(), "image/png")})

    assert response.status_code == 401
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Analysis)) == 0
    assert list(temporary_root.iterdir()) == []
    assert list(storage._root.iterdir()) == []


def test_authenticated_scan_persists_private_object_and_completed_model_result(lifecycle_client):
    client, sessions, storage, _app, temporary_root = lifecycle_client
    user_id, token = _create_account(client, "scan-owner@example.com")
    other_user_id, _other_token = _create_account(client, "scan-other@example.com")

    response = _upload(
        client,
        token,
        filename="../../unsafe-client-name.png",
        extra_data={"user_id": other_user_id},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["result_available"] is True
    assert payload["result"]["analysis_id"] == payload["analysis_id"]
    assert payload["failure"] is None
    assert payload["image_content_type"] == "image/png"
    assert payload["image_size_bytes"] == len(_png_bytes())
    assert "user_id" not in payload and "image_object_key" not in payload
    with sessions() as db:
        analysis = db.get(Analysis, UUID(payload["analysis_id"]))
        assert analysis is not None
        assert str(analysis.user_id) == user_id
        assert analysis.status == "completed"
        assert analysis.result_data["analysis_id"] == str(analysis.id)
        assert analysis.image_object_key.startswith(f"users/{user_id}/analyses/")
        assert "unsafe-client-name" not in analysis.image_object_key
        stored = storage.get(analysis.image_object_key)
        assert stored.content == _png_bytes()
        assert stored.content_type == "image/png"
    assert list(temporary_root.iterdir()) == []


def test_inference_capability_failure_is_persisted_as_failed(lifecycle_client, monkeypatch):
    client, sessions, _storage, _app, _temporary_root = lifecycle_client
    _user_id, token = _create_account(client, "inference-unavailable@example.com")

    class FailedInference:
        def analyze_bytes(self, *_args, **_kwargs):
            raise ModelCapabilityError(InferenceErrorCode.MISSING_ARTIFACT,
                                       "checkpoint unavailable", stage="variant_selection")

    monkeypatch.setattr(analyze, "create_plant_analysis_service",
                        lambda **_kwargs: SimpleNamespace(inference=FailedInference()))
    response = _upload(client, token)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "missing_artifact"
    failed_id = response.json()["detail"]["analysis_id"]
    with sessions() as db:
        failed = db.scalar(select(Analysis).where(Analysis.status == "failed"))
        assert failed is not None
        assert failed.status == "failed" and failed.result_data is None
        assert failed.failure_data["code"] == "missing_artifact"
        assert failed.failure_data["stage"] == "variant_selection"
        assert failed.failure_data["message"] == "The configured model or runtime is unavailable"
        assert "checkpoint unavailable" not in failed.failure_data["message"]

    retrieved = client.get(f"/api/v1/analysis/{failed_id}", headers={"Authorization": f"Bearer {token}"})
    assert retrieved.status_code == 200
    assert retrieved.json()["status"] == "failed"
    assert retrieved.json()["result"] is None
    assert retrieved.json()["failure"]["code"] == "missing_artifact"
    assert retrieved.json()["failure"]["stage"] == "variant_selection"


def test_unexpected_inference_failure_persists_only_safe_details(lifecycle_client, monkeypatch):
    client, sessions, _storage, _app, _temporary_root = lifecycle_client
    _user_id, token = _create_account(client, "inference-internal-error@example.com")

    class UnexpectedFailure:
        def analyze_bytes(self, *_args, **_kwargs):
            raise RuntimeError("internal implementation detail")

    monkeypatch.setattr(analyze, "create_plant_analysis_service",
                        lambda **_kwargs: SimpleNamespace(inference=UnexpectedFailure()))
    response = _upload(client, token)

    assert response.status_code == 500
    payload = response.json()["detail"]
    assert payload["code"] == "inference_internal_error"
    assert payload["message"] == "Plant analysis failed"
    assert "internal implementation detail" not in response.text
    with sessions() as db:
        failed = db.scalar(select(Analysis).where(Analysis.status == "failed"))
        assert failed is not None
        assert failed.failure_data["code"] == "inference_internal_error"
        assert failed.failure_data["stage"] == "pipeline"
        assert failed.failure_data["message"] == "Plant analysis failed"


def test_analysis_retrieval_and_history_are_owner_scoped(lifecycle_client):
    client, _sessions, _storage, _app, _temporary_root = lifecycle_client
    _user_a, token_a = _create_account(client, "scan-a@example.com")
    _user_b, token_b = _create_account(client, "scan-b@example.com")
    analysis_a = _upload(client, token_a).json()["analysis_id"]
    analysis_b = _upload(client, token_b).json()["analysis_id"]

    own = client.get(f"/api/v1/analysis/{analysis_a}", headers={"Authorization": f"Bearer {token_a}"})
    foreign = client.get(f"/api/v1/analysis/{analysis_a}", headers={"Authorization": f"Bearer {token_b}"})
    missing = client.get(f"/api/v1/analysis/{UUID(int=1)}", headers={"Authorization": f"Bearer {token_b}"})
    history_a = client.get("/api/v1/analyses", headers={"Authorization": f"Bearer {token_a}"})
    history_b = client.get("/api/v1/analyses", headers={"Authorization": f"Bearer {token_b}"})

    assert own.status_code == 200 and own.json()["analysis_id"] == analysis_a
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json() == {"detail": "Resource not found"}
    assert [item["analysis_id"] for item in history_a.json()] == [analysis_a]
    assert [item["analysis_id"] for item in history_b.json()] == [analysis_b]


@pytest.mark.parametrize(
    ("data", "content_type", "expected_status"),
    [
        (b"not an image", "image/png", 400),
        (_png_bytes(), "image/gif", 415),
        (b"x" * (analyze.MAX_IMAGE_BYTES + 1), "image/png", 413),
        (_png_bytes(), "image/jpeg", 415),
    ],
    ids=["malformed", "unsupported-mime", "oversized", "mismatched-content"],
)
def test_invalid_uploads_are_rejected_without_records_or_temp_files(
    lifecycle_client, data, content_type, expected_status
):
    client, sessions, storage, _app, temporary_root = lifecycle_client
    _user_id, token = _create_account(client, f"invalid-{expected_status}-{len(data)}@example.com")

    response = _upload(client, token, data=data, content_type=content_type)

    assert response.status_code == expected_status
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Analysis)) == 0
    assert list(temporary_root.iterdir()) == []
    assert not storage.exists("users/unrelated/analyses/object/image")


def test_storage_failure_does_not_create_analysis(lifecycle_client, monkeypatch):
    client, sessions, _storage, _app, _temporary_root = lifecycle_client
    _user_id, token = _create_account(client, "storage-failure@example.com")

    class FailingStorage:
        def put(self, *_args, **_kwargs):
            raise StorageError("safe test failure")

        def get(self, _key):
            raise AssertionError("unused")

        def exists(self, _key):
            return False

        def delete(self, _key):
            return None

    monkeypatch.setattr(analyze, "create_object_storage", FailingStorage)
    response = _upload(client, token)

    assert response.status_code == 503
    assert response.json() == {"detail": "Image storage is unavailable"}
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Analysis)) == 0


def test_database_failure_removes_stored_object(lifecycle_client):
    client, sessions, storage, test_app, _temporary_root = lifecycle_client
    _user_id, token = _create_account(client, "db-failure@example.com")

    def fail_commit():
        with sessions() as db:
            db.commit = lambda: (_ for _ in ()).throw(RuntimeError("test commit failure"))
            yield db

    test_app.dependency_overrides[get_db] = fail_commit
    response = _upload(client, token)
    test_app.dependency_overrides.pop(get_db)

    assert response.status_code == 500
    assert response.json() == {"detail": "Could not persist the uploaded analysis"}
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Analysis)) == 0
    assert list(storage._root.iterdir()) == []


def test_history_and_retrieval_reject_anonymous_requests(lifecycle_client):
    client, _sessions, _storage, _app, _temporary_root = lifecycle_client
    assert client.post(
        "/api/v1/analyze/image", files={"file": ("leaf.png", _png_bytes(), "image/png")}
    ).status_code == 401
    assert client.get("/api/v1/analyses").status_code == 401
    assert client.get(f"/api/v1/analysis/{UUID(int=2)}").status_code == 401


def test_missing_file_is_rejected(lifecycle_client):
    client, _sessions, _storage, _app, _temporary_root = lifecycle_client
    _user_id, token = _create_account(client, "missing-file@example.com")
    response = client.post("/api/v1/analyze/image", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422


def test_analysis_delete_removes_owned_objects_and_database_row(lifecycle_client):
    client, sessions, storage, _app, _temporary_root = lifecycle_client
    user_id, token = _create_account(client, "delete-owner@example.com")
    analysis_id = _upload(client, token).json()["analysis_id"]
    artifact_key = f"analyses/{analysis_id}/masks/leaf_0_mask.png"
    unrelated_key = "analyses/another-analysis/masks/keep.png"
    storage.put(b"mask", object_key=artifact_key, content_type="image/png")
    storage.put(b"keep", object_key=unrelated_key, content_type="image/png")
    with sessions() as db:
        analysis = db.get(Analysis, UUID(analysis_id))
        analysis.result_data = {
            **analysis.result_data,
            "leaves": [{"leaf_mask_asset": {"storage_key": artifact_key}}],
            "unexpected": {"storage_key": unrelated_key},
        }
        db.commit()
        original_key = analysis.image_object_key

    response = client.delete(
        f"/api/v1/analysis/{analysis_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204
    with sessions() as db:
        assert db.get(Analysis, UUID(analysis_id)) is None
    assert not storage.exists(original_key)
    assert not storage.exists(artifact_key)
    assert storage.exists(unrelated_key)


def test_analysis_delete_is_owner_scoped(lifecycle_client):
    client, sessions, storage, _app, _temporary_root = lifecycle_client
    owner_id, owner_token = _create_account(client, "delete-owner-scope@example.com")
    _other_id, other_token = _create_account(client, "delete-other-scope@example.com")
    analysis_id = _upload(client, owner_token).json()["analysis_id"]
    with sessions() as db:
        analysis = db.get(Analysis, UUID(analysis_id))
        original_key = analysis.image_object_key

    response = client.delete(
        f"/api/v1/analysis/{analysis_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404
    assert storage.exists(original_key)
    with sessions() as db:
        analysis = db.get(Analysis, UUID(analysis_id))
        assert str(analysis.user_id) == owner_id


def test_analysis_delete_retains_record_when_storage_cleanup_fails(lifecycle_client, monkeypatch):
    client, sessions, storage, _app, _temporary_root = lifecycle_client
    _user_id, token = _create_account(client, "delete-storage-failure@example.com")
    analysis_id = _upload(client, token).json()["analysis_id"]
    with sessions() as db:
        original_key = db.get(Analysis, UUID(analysis_id)).image_object_key

    def fail_delete(_key):
        raise StorageError("provider failure")

    monkeypatch.setattr(storage, "delete", fail_delete)
    response = client.delete(
        f"/api/v1/analysis/{analysis_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Analysis assets could not be deleted; retry the request"
    with sessions() as db:
        assert db.get(Analysis, UUID(analysis_id)) is not None
    assert storage.exists(original_key)

def test_owner_asset_links_and_local_proxy_stream_private_bytes(lifecycle_client):
    client, sessions, storage, _app, _temporary_root = lifecycle_client
    _user_id, token = _create_account(client, "asset-owner@example.com")
    analysis_id = _upload(client, token).json()["analysis_id"]
    artifact_key = f"analyses/{analysis_id}/masks/leaf_0_cam.png"
    storage.put(b"cam-image", object_key=artifact_key, content_type="image/png")
    with sessions() as db:
        analysis = db.get(Analysis, UUID(analysis_id))
        analysis.result_data = {
            **analysis.result_data,
            "leaves": [{"explainability": {"heatmap_asset": {"storage_key": artifact_key}}}],
        }
        db.commit()
        original_key = analysis.image_object_key

    links_response = client.get(
        f"/api/v1/analysis/{analysis_id}/assets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert links_response.status_code == 200
    links = links_response.json()["assets"]
    assert {item["storage_key"] for item in links} == {original_key, artifact_key}
    assert all(item["expires_in_seconds"] is None for item in links)

    artifact_link = next(item["download_url"] for item in links if item["storage_key"] == artifact_key)
    downloaded = client.get(artifact_link, headers={"Authorization": f"Bearer {token}"})

    assert downloaded.status_code == 200
    assert downloaded.content == b"cam-image"
    assert downloaded.headers["content-type"] == "image/png"
    assert downloaded.headers["cache-control"] == "private, no-store"
    assert downloaded.headers["x-content-type-options"] == "nosniff"


def test_asset_endpoint_rejects_unreferenced_or_foreign_assets(lifecycle_client):
    client, _sessions, storage, _app, _temporary_root = lifecycle_client
    _owner_id, owner_token = _create_account(client, "asset-owner-scope@example.com")
    _other_id, other_token = _create_account(client, "asset-other-scope@example.com")
    analysis_id = _upload(client, owner_token).json()["analysis_id"]
    foreign_key = "analyses/foreign-analysis/masks/secret.png"
    storage.put(b"secret", object_key=foreign_key, content_type="image/png")

    unreferenced = client.get(
        f"/api/v1/analysis/{analysis_id}/asset",
        params={"key": foreign_key},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    foreign_owner = client.get(
        f"/api/v1/analysis/{analysis_id}/assets",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert unreferenced.status_code == 404
    assert foreign_owner.status_code == 404
    assert storage.exists(foreign_key)