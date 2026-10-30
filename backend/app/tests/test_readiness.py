"""CPU-safe operational health/readiness contract tests."""

from types import SimpleNamespace

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api import readiness
from app.main import app
from app.core.config import Settings, settings
from app.ml.remote import RemoteInferenceClient
from app.services.plant_analysis_service import ApplicationPlantAnalysisService
from app.ml.service import PlantAnalysisService


class _Adapter:
    def __init__(self, name, ready=True):
        self.name = name
        self._ready = ready

    def is_ready(self):
        return self._ready


def test_empty_ood_calibration_path_is_treated_as_unset():
    assert Settings(PLANTGUARD_OOD_CALIBRATION_PATH="").PLANTGUARD_OOD_CALIBRATION_PATH is None


def _inference(*, loaded=True):
    return PlantAnalysisService(
        sam=_Adapter("sam2_instance_segmentation", loaded),
        leaf_filter=_Adapter("dino_leaf_filter", loaded),
        classifier=_Adapter("dino_disease_classifier", loaded),
        segmenter=_Adapter("segformer_disease_segmentation", loaded),
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
        model_readiness=lambda: {
            "model_prerequisites": True,
            "sam2_primary": True,
            "mobilesam_fallback": True,
        },
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


def test_readiness_is_ready_with_lazy_models_not_resident(monkeypatch):
    _ready_dependencies(monkeypatch, loaded=True)
    response = TestClient(app).get("/api/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {
            "database": True,
            "storage": True,
            "model_prerequisites": True,
            "sam2_primary": True,
            "mobilesam_fallback": True,
            "models_resident": True,
        },
    }


def test_readiness_does_not_require_lazy_models_to_be_resident(monkeypatch):
    _ready_dependencies(monkeypatch, loaded=False, storage_ok=True)
    response = TestClient(app).get("/api/ready")

    assert response.status_code == 200
    assert response.json()["checks"] == {
        "database": True,
        "storage": True,
        "model_prerequisites": True,
        "sam2_primary": True,
        "mobilesam_fallback": True,
        "models_resident": False,
    }


def test_readiness_is_unavailable_when_a_required_dependency_fails(monkeypatch):
    _ready_dependencies(monkeypatch, loaded=False, storage_ok=False)
    response = TestClient(app).get("/api/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["checks"]["storage"] is False
    assert response.json()["detail"]["checks"]["models_resident"] is False


def test_readiness_requires_ood_calibration(monkeypatch):
    _ready_dependencies(monkeypatch)
    inference = _inference()
    inference.ood_detector.validate_calibration = lambda: (_ for _ in ()).throw(
        RuntimeError("calibration unavailable")
    )
    monkeypatch.setattr(
        readiness,
        "create_plant_analysis_service",
        lambda: ApplicationPlantAnalysisService(inference=inference),
    )

    response = TestClient(app).get("/api/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["checks"]["model_prerequisites"] is False
    assert response.json()["detail"]["checks"]["models_resident"] is False


def test_readiness_accepts_verified_optional_mobilesam_fallback(monkeypatch, tmp_path):
    from app.ml.errors import InferenceErrorCode, ModelCapabilityError
    from app.services import plant_analysis_service as service_module

    inference = _inference(loaded=False)
    inference.sam.config_name = "configs/sam2.1/sam2.1_hiera_b+.yaml"
    inference.classifier.get_class_mapping = lambda: {index: str(index) for index in range(38)}
    inference.segmenter._configuration_error = None
    inference.ood_detector.validate_calibration = lambda: None
    for adapter in (inference.sam, inference.mobile_sam, inference.leaf_filter,
                    inference.classifier, inference.segmenter):
        adapter.artifact_path = tmp_path / "checkpoint"
        adapter.artifact_path.touch()

    def select_variant(adapter, _model_id):
        if adapter is inference.sam:
            raise ModelCapabilityError(
                InferenceErrorCode.INVALID_CONFIGURATION,
                "SAM2 config unavailable",
                stage="variant_selection",
            )

    inference._select_variant = select_variant
    package_root = tmp_path / "sam2"
    package_root.mkdir()
    monkeypatch.setattr(
        service_module.importlib.util,
        "find_spec",
        lambda _name: SimpleNamespace(origin=str(package_root / "__init__.py")),
    )

    result = ApplicationPlantAnalysisService(inference=inference).model_readiness()

    assert result == {
        "model_prerequisites": True,
        "sam2_primary": False,
        "mobilesam_fallback": True,
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


def test_local_readiness_checks_sam_config_inside_installed_package(monkeypatch, tmp_path):
    from app.services import plant_analysis_service as service_module

    package_root = tmp_path / "sam2"
    config = package_root / "configs" / "sam2.1" / "sam2.1_hiera_b+.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("test config", encoding="utf-8")
    inference = _inference()
    for adapter in (inference.sam, inference.leaf_filter, inference.classifier, inference.segmenter):
        adapter.artifact_path = tmp_path / "checkpoint"
        adapter.artifact_path.touch()
    inference.sam.config_name = "configs/sam2.1/sam2.1_hiera_b+.yaml"
    inference.segmenter._configuration_error = None
    inference.classifier.get_class_mapping = lambda: {index: str(index) for index in range(38)}
    inference._select_variant = lambda *_args: None
    inference.ood_detector.validate_calibration = lambda: None

    def find_spec(name):
        return SimpleNamespace(origin=str(package_root / "__init__.py"))

    monkeypatch.setattr(service_module.importlib.util, "find_spec", find_spec)

    assert ApplicationPlantAnalysisService(inference=inference).is_ready()


def test_local_readiness_fails_when_a_configured_checkpoint_fails_integrity(monkeypatch, tmp_path):
    from app.ml.errors import InferenceErrorCode, ModelCapabilityError
    from app.services import plant_analysis_service as service_module

    package_root = tmp_path / "sam2"
    config = package_root / "configs" / "sam2.1" / "sam2.1_hiera_b+.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("test config", encoding="utf-8")
    inference = _inference()
    for adapter in (inference.sam, inference.leaf_filter, inference.classifier, inference.segmenter):
        adapter.artifact_path = tmp_path / "checkpoint"
        adapter.artifact_path.touch()
    inference.sam.config_name = "configs/sam2.1/sam2.1_hiera_b+.yaml"
    inference.segmenter._configuration_error = None
    inference.classifier.get_class_mapping = lambda: {index: str(index) for index in range(38)}
    inference._select_variant = lambda *_args: (_ for _ in ()).throw(
        ModelCapabilityError(
            InferenceErrorCode.ARTIFACT_INTEGRITY,
            "invalid checkpoint",
            stage="variant_selection",
        )
    )
    monkeypatch.setattr(
        service_module.importlib.util,
        "find_spec",
        lambda name: SimpleNamespace(origin=str(package_root / "__init__.py")),
    )

    assert not ApplicationPlantAnalysisService(inference=inference).is_ready()