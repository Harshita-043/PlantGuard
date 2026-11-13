"""Unit and integration tests for the Application-level Plant Analysis Service."""

import io
from types import SimpleNamespace
from uuid import UUID, uuid4

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import SecretStr
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import analyze
from app.api.v1.auth import router as auth_router
from app.core.config import settings
from app.core.database import Base, get_db
from app.models.analysis import Analysis
from app.ml.errors import (
    InferenceError,
    InferenceErrorCode,
    InvalidImageError,
    ModelCapabilityError,
)
from app.schemas.inference import (
    ClassificationResult,
    FullScanResult,
    OODResult,
    OverallHealthStatus,
    PlantHealthSummary,
    SingleLeafAnalysis,
)
from app.schemas.plant_analysis import PlantAnalysisResponse
from app.services.plant_analysis_service import (
    ApplicationPlantAnalysisService,
    create_plant_analysis_service,
)
from app.storage import LocalFileObjectStorage


def _create_sample_png_bytes(width: int = 10, height: int = 10) -> bytes:
    image = Image.new("RGB", (width, height), color=(30, 140, 60))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _create_sample_scan_result(analysis_id: str | None = None) -> FullScanResult:
    aid = analysis_id or str(uuid4())
    return FullScanResult(
        analysis_id=aid,
        status="completed",
        hardware_device="cpu",
        processing_time_ms=42,
        sam_variant="sam2.1_hiera_base_plus",
        sam_fallback_applied=False,
        model_versions={
            "sam2": "2.1",
            "leaf_filter": "v1",
            "classifier": "vit-b14",
            "segmenter": "plantseg-b0",
        },
        leaves=[
            SingleLeafAnalysis(
                leaf_id=0,
                bounding_box=[0.1, 0.1, 0.5, 0.5],
                is_leaf=True,
                leaf_filter_confidence=0.98,
                classification=ClassificationResult(
                    primary_class="Tomato___healthy",
                    confidence=0.95,
                    is_healthy=True,
                    crop_type="Tomato",
                    disease_name="healthy",
                    top_k_probabilities={"Tomato___healthy": 0.95},
                ),
                ood=OODResult(
                    score=120.0,
                    threshold=2474.64,
                    is_ood=False,
                    status="ood_not_detected",
                ),
            )
        ],
        plant_summary=PlantHealthSummary(
            overall_health_score=98.0,
            health_status=OverallHealthStatus.HEALTHY,
            total_leaves_detected=1,
            valid_leaves_analyzed=1,
            healthy_leaves_count=1,
            diseased_leaves_count=0,
            primary_diagnosis="Tomato___healthy",
            average_severity_percentage=0.0,
            recommendations=["Routine inspection recommended."],
        ),
    )


class MockInferenceEngine:
    """Mock ML inference engine tracking calls and returning predictable outputs."""

    def __init__(self, result: FullScanResult | None = None, exc_to_raise: Exception | None = None):
        self.result = result or _create_sample_scan_result()
        self.exc_to_raise = exc_to_raise
        self.analyze_bytes_calls: list[dict] = []
        self.analyze_calls: list[dict] = []

    def analyze_bytes(self, image_bytes: bytes, *, analysis_id: str | None = None) -> FullScanResult:
        self.analyze_bytes_calls.append({"bytes": image_bytes, "analysis_id": analysis_id})
        if self.exc_to_raise:
            raise self.exc_to_raise
        # return a copy with the provided analysis_id if given
        if analysis_id:
            return self.result.model_copy(update={"analysis_id": analysis_id})
        return self.result

    def analyze(self, image: np.ndarray, *, analysis_id: str | None = None) -> FullScanResult:
        self.analyze_calls.append({"image": image, "analysis_id": analysis_id})
        if self.exc_to_raise:
            raise self.exc_to_raise
        if analysis_id:
            return self.result.model_copy(update={"analysis_id": analysis_id})
        return self.result


# ==============================================================================
# UNIT TESTS
# ==============================================================================

def test_unit_successful_analyze_bytes():
    """Verify application service coordinates analyze_bytes and propagates FullScanResult."""
    mock_inf = MockInferenceEngine()
    service = ApplicationPlantAnalysisService(inference=mock_inf)

    sample_bytes = _create_sample_png_bytes()
    scan_id = "test-scan-123"
    result = service.analyze_bytes(sample_bytes, analysis_id=scan_id)

    assert isinstance(result, FullScanResult)
    assert result.analysis_id == scan_id
    assert result.status == "completed"
    assert len(mock_inf.analyze_bytes_calls) == 1
    assert mock_inf.analyze_bytes_calls[0]["bytes"] == sample_bytes
    assert mock_inf.analyze_bytes_calls[0]["analysis_id"] == scan_id


def test_unit_successful_analyze_numpy():
    """Verify application service coordinates analyze(np.ndarray) and propagates FullScanResult."""
    mock_inf = MockInferenceEngine()
    service = ApplicationPlantAnalysisService(inference=mock_inf)

    sample_img = np.zeros((32, 32, 3), dtype=np.uint8)
    scan_id = "test-scan-numpy"
    result = service.analyze(sample_img, analysis_id=scan_id)

    assert isinstance(result, FullScanResult)
    assert result.analysis_id == scan_id
    assert len(mock_inf.analyze_calls) == 1
    assert np.array_equal(mock_inf.analyze_calls[0]["image"], sample_img)


def test_unit_empty_image_bytes_raises_invalid_image_error():
    """Verify empty image bytes reject with typed InvalidImageError."""
    service = ApplicationPlantAnalysisService(inference=MockInferenceEngine())
    with pytest.raises(InvalidImageError) as exc_info:
        service.analyze_bytes(b"")
    assert "empty" in str(exc_info.value).lower()


def test_unit_non_bytes_payload_raises_invalid_image_error():
    """Verify non-bytes payload rejects with typed InvalidImageError."""
    service = ApplicationPlantAnalysisService(inference=MockInferenceEngine())
    with pytest.raises(InvalidImageError) as exc_info:
        service.analyze_bytes("not bytes string")  # type: ignore
    assert "bytes" in str(exc_info.value).lower()


def test_unit_invalid_numpy_array_raises_invalid_image_error():
    """Verify 2D or non-RGB numpy arrays reject with typed InvalidImageError."""
    service = ApplicationPlantAnalysisService(inference=MockInferenceEngine())

    # 2D grayscale
    with pytest.raises(InvalidImageError):
        service.analyze(np.zeros((10, 10), dtype=np.uint8))

    # 4-channel RGBA
    with pytest.raises(InvalidImageError):
        service.analyze(np.zeros((10, 10, 4), dtype=np.uint8))

    # Empty 0-dimension
    with pytest.raises(InvalidImageError):
        service.analyze(np.zeros((0, 0, 3), dtype=np.uint8))


def test_unit_inference_error_propagation():
    """Verify typed InferenceError propagates without mutation."""
    inf_err = InferenceError(
        InferenceErrorCode.OUT_OF_DISTRIBUTION,
        "Sample OOD detected",
        stage="ood_detection",
    )
    mock_inf = MockInferenceEngine(exc_to_raise=inf_err)
    service = ApplicationPlantAnalysisService(inference=mock_inf)

    with pytest.raises(InferenceError) as exc_info:
        service.analyze_bytes(_create_sample_png_bytes())

    assert exc_info.value.code == InferenceErrorCode.OUT_OF_DISTRIBUTION
    assert exc_info.value.stage == "ood_detection"
    assert "Sample OOD detected" in str(exc_info.value)


def test_unit_model_capability_error_propagation():
    """Verify ModelCapabilityError propagates cleanly."""
    cap_err = ModelCapabilityError(
        InferenceErrorCode.MISSING_ARTIFACT,
        "DINOv2 weights missing",
        stage="variant_selection",
    )
    mock_inf = MockInferenceEngine(exc_to_raise=cap_err)
    service = ApplicationPlantAnalysisService(inference=mock_inf)

    with pytest.raises(ModelCapabilityError) as exc_info:
        service.analyze_bytes(_create_sample_png_bytes())

    assert exc_info.value.code == InferenceErrorCode.MISSING_ARTIFACT
    assert exc_info.value.stage == "variant_selection"


def test_unit_unexpected_exception_propagation():
    """Verify unexpected internal errors propagate without being swallowed."""
    mock_inf = MockInferenceEngine(exc_to_raise=RuntimeError("Unexpected CUDA OOM"))
    service = ApplicationPlantAnalysisService(inference=mock_inf)

    with pytest.raises(RuntimeError) as exc_info:
        service.analyze_bytes(_create_sample_png_bytes())

    assert "Unexpected CUDA OOM" in str(exc_info.value)


def test_unit_legacy_analyze_image_compatibility():
    """Verify analyze_image returns legacy PlantAnalysisResponse when in-distribution."""
    mock_inf = MockInferenceEngine()
    service = ApplicationPlantAnalysisService(inference=mock_inf)

    img = np.zeros((16, 16, 3), dtype=np.uint8)
    legacy_res = service.analyze_image(img, analysis_id="legacy-123")

    assert isinstance(legacy_res, PlantAnalysisResponse)
    assert legacy_res.analysis_id == "legacy-123"
    assert legacy_res.status == "completed"
    assert len(legacy_res.leaf_results) == 1
    assert legacy_res.leaf_results[0].disease_class == "Tomato___healthy"


def test_unit_legacy_analyze_image_fails_closed_on_ood():
    """Verify legacy analyze_image raises OUT_OF_DISTRIBUTION if leaf is OOD."""
    ood_result = _create_sample_scan_result()
    # update leaf ood to True
    ood_result.leaves[0] = ood_result.leaves[0].model_copy(
        update={"ood": OODResult(score=3000.0, threshold=2474.64, is_ood=True, status="ood_detected")}
    )
    mock_inf = MockInferenceEngine(result=ood_result)
    service = ApplicationPlantAnalysisService(inference=mock_inf)

    with pytest.raises(InferenceError) as exc_info:
        service.analyze_image(np.zeros((16, 16, 3), dtype=np.uint8))

    assert exc_info.value.code == InferenceErrorCode.OUT_OF_DISTRIBUTION
    assert exc_info.value.stage == "ood_detection"


def test_unit_dependency_injection_factory():
    """Verify create_plant_analysis_service respects injected inference and storage."""
    mock_inf = MockInferenceEngine()
    dummy_storage = LocalFileObjectStorage(root="dummy-dir")
    service = create_plant_analysis_service(inference=mock_inf, storage=dummy_storage)

    assert isinstance(service, ApplicationPlantAnalysisService)
    assert service.inference is mock_inf
    assert service.storage is dummy_storage


# ==============================================================================
# INTEGRATION TESTS (FastAPI API boundary)
# ==============================================================================

@pytest.fixture
def service_test_app(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", SecretStr("test-service-secret-" + "s" * 32))
    storage = LocalFileObjectStorage(tmp_path / "objects")
    monkeypatch.setattr(analyze, "create_object_storage", lambda: storage)

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
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        with session_factory() as db:
            yield db

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(analyze.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client, session_factory, storage

    app.dependency_overrides.clear()
    engine.dispose()


def _register_and_login(client: TestClient, email: str = "service_test@example.com") -> str:
    password = "a-secure-testing-password-123"
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return login_resp.json()["access_token"]


def test_integration_api_calls_application_service_and_persists(service_test_app, monkeypatch):
    """Verify /api/v1/analyze/image calls application service analyze_bytes and persists results."""
    client, session_factory, _storage = service_test_app
    token = _register_and_login(client, "integration_success@example.com")

    mock_inf = MockInferenceEngine()
    test_service = ApplicationPlantAnalysisService(inference=mock_inf)

    # Monkeypatch the factory to return our test application service instance
    monkeypatch.setattr(analyze, "create_plant_analysis_service", lambda **_kwargs: test_service)

    image_bytes = _create_sample_png_bytes(20, 20)
    response = client.post(
        "/api/v1/analyze/image",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("leaf.png", image_bytes, "image/png")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["result_available"] is True
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["sam_variant"] == "sam2.1_hiera_base_plus"

    analysis_id = UUID(payload["analysis_id"])

    # Verify database persistence
    with session_factory() as db:
        saved = db.scalar(select(Analysis).where(Analysis.id == analysis_id))
        assert saved is not None
        assert saved.status == "completed"
        assert saved.result_data is not None
        assert saved.result_data["analysis_id"] == str(analysis_id)
        assert saved.failure_data is None

    # Verify application service was invoked with raw bytes
    assert len(mock_inf.analyze_bytes_calls) == 1
    assert mock_inf.analyze_bytes_calls[0]["bytes"] == image_bytes
    assert mock_inf.analyze_bytes_calls[0]["analysis_id"] == str(analysis_id)


def test_integration_api_failed_inference_persists_failure_status(service_test_app, monkeypatch):
    """Verify typed inference errors update analysis status to failed and return 503."""
    client, session_factory, _storage = service_test_app
    token = _register_and_login(client, "integration_failure@example.com")

    err = ModelCapabilityError(
        InferenceErrorCode.MISSING_ARTIFACT,
        "Checkpoint not hydrated",
        stage="variant_selection",
    )
    mock_inf = MockInferenceEngine(exc_to_raise=err)
    test_service = ApplicationPlantAnalysisService(inference=mock_inf)
    monkeypatch.setattr(analyze, "create_plant_analysis_service", lambda **_kwargs: test_service)

    image_bytes = _create_sample_png_bytes(20, 20)
    response = client.post(
        "/api/v1/analyze/image",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("leaf.png", image_bytes, "image/png")},
    )

    assert response.status_code == 503
    body = response.json()["detail"]
    assert body["code"] == "missing_artifact"
    assert body["stage"] == "variant_selection"
    analysis_id = UUID(body["analysis_id"])

    # Verify database recorded the failed state
    with session_factory() as db:
        failed_row = db.scalar(select(Analysis).where(Analysis.id == analysis_id))
        assert failed_row is not None
        assert failed_row.status == "failed"
        assert failed_row.result_data is None
        assert failed_row.failure_data["code"] == "missing_artifact"
        assert failed_row.failure_data["stage"] == "variant_selection"


def test_integration_api_unexpected_error_sanitizes_message(service_test_app, monkeypatch):
    """Verify internal unhandled errors return 500 without leaking stack traces."""
    client, session_factory, _storage = service_test_app
    token = _register_and_login(client, "integration_oom@example.com")

    mock_inf = MockInferenceEngine(exc_to_raise=RuntimeError("internal stack detail secret"))
    test_service = ApplicationPlantAnalysisService(inference=mock_inf)
    monkeypatch.setattr(analyze, "create_plant_analysis_service", lambda **_kwargs: test_service)

    image_bytes = _create_sample_png_bytes(20, 20)
    response = client.post(
        "/api/v1/analyze/image",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("leaf.png", image_bytes, "image/png")},
    )

    assert response.status_code == 500
    assert "internal stack detail secret" not in response.text
    body = response.json()["detail"]
    assert body["code"] == "inference_internal_error"
    assert body["message"] == "Plant analysis failed"
