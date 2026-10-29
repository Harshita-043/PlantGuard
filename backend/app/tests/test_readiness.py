"""CPU-safe operational health/readiness contract tests."""

from types import SimpleNamespace

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api import readiness
from app.main import app
from app.core.config import settings
from app.ml.remote import RemoteInferenceClient
from app.services.plant_analysis_service import ApplicationPlantAnalysisService
from app.ml.service import PlantAnalysisService


class _Adapter:
    def __init__(self, name, ready=True):
        self.name = name
        self._ready = ready

    def is_ready(self):
        return self._ready


def _inference(*, loaded=True):
    return PlantAnalysisService(
        sam=_Adapter("sam", loaded),
        leaf_filter=_Adapter("leaf", loaded),
        classifier=_Adapter("classifier", loaded),
        segmenter=_Adapter("segmenter", loaded),
        device="cpu",
    )


def _ready_dependencies(monkeypatch, *, loaded=True, db_ok=True, storage_ok=True):
    class Result:
        def scalar_one(self):
            if not db_ok:
                raise RuntimeError("test database unavailable")
            return 1

    class Database:
        def execute(self, _query):
            return Result()

    class Context:
        def __enter__(self):
            return Database()
        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(readiness, "SessionLocal", lambda: Context())
    monkeypatch.setattr(readiness, "create_object_storage", lambda: SimpleNamespace(check_ready=lambda: storage_ok))
    inference = _inference(loaded=loaded)
    monkeypatch.setattr(readiness, "create_plant_analysis_service", lambda: SimpleNamespace(
        inference=inference,
        is_ready=lambda: True,
    ))


def test_health_is_liveness_only():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_models_endpoint_reports_versions_without_paths_or_credentials(monkeypatch):
    monkeypatch.setattr(settings, "PLANTGUARD_INFERENCE_PROFILE", "cpu")
    response = TestClient(app).get("/api/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"]
    assert payload["device"]
    assert payload["precision"] == "fp32"
    assert len(payload["models"]) == 5
    serialized = response.text.lower()
    for forbidden in ("artifact_path", "remote_inference_url", "access_key", "secret_access_key"):
        assert forbidden not in serialized


def test_readiness_requires_database_storage_and_loaded_models(monkeypatch):
    _ready_dependencies(monkeypatch, loaded=True)
    response = TestClient(app).get("/api/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {
            "database": True,
            "storage": True,
            "model_prerequisites": True,
            "models_loaded": True,
        },
    }


def test_readiness_is_unavailable_if_any_required_dependency_is_not_ready(monkeypatch):
    _ready_dependencies(monkeypatch, loaded=False, storage_ok=True)
    response = TestClient(app).get("/api/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["checks"] == {
        "database": True,
        "storage": True,
        "model_prerequisites": True,
        "models_loaded": False,
    }

def test_remote_models_endpoint_does_not_claim_local_checkpoint_versions(monkeypatch):
    monkeypatch.setattr(settings, "PLANTGUARD_INFERENCE_PROFILE", "remote")
    response = TestClient(app).get("/api/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["device"] == "remote"
    assert payload["precision"] == "profile_managed"
    assert payload["models"] == {
        "remote_pipeline": {
            "configured_variant": "remote_managed",
            "manifest_checksum": "not_applicable",
            "checkpoint_status": "managed_by_remote_service",
            "runtime_validation": "reported_per_prediction",
        }
    }


def test_readiness_returns_structured_unavailable_when_database_is_unconfigured(monkeypatch):
    _ready_dependencies(monkeypatch, loaded=False, storage_ok=True)
    monkeypatch.setattr(readiness, "SessionLocal", None)

    response = TestClient(app).get("/api/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["checks"]["database"] is False

def test_remote_readiness_accepts_only_available_status(monkeypatch):
    from app.services import plant_analysis_service as service_module

    monkeypatch.setattr(settings, "PLANTGUARD_REMOTE_INFERENCE_URL", "https://inference.example")
    monkeypatch.setattr(settings, "PLANTGUARD_REMOTE_INFERENCE_TOKEN", SecretStr("test-token"))
    client = RemoteInferenceClient(
        base_url="https://inference.example",
        token="test-token",
        deployment_authorized=True,
    )
    service = ApplicationPlantAnalysisService(inference=client)

    for status, expected in (("available", True), ("unavailable", False), ("unauthorized", False)):
        monkeypatch.setattr(service_module, "probe_remote_health", lambda *_args, **_kwargs: status)
        assert service.is_ready() is expected