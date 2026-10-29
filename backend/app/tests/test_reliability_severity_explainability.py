import io

import numpy as np
import pytest
from PIL import Image

from app.ml.ood import OODDetector
from app.ml.service import PlantAnalysisService
from app.ml.severity import SeverityEstimator
from app.schemas.inference import SeverityLevel


def _masks(pixels: int):
    leaf = np.ones((100, 100), dtype=np.uint8)
    disease = np.zeros_like(leaf)
    disease.flat[:pixels] = 1
    return disease, leaf


@pytest.mark.parametrize(("pixels", "expected"), [
    (0, SeverityLevel.HEALTHY), (1500, SeverityLevel.LOW),
    (1501, SeverityLevel.MEDIUM), (3500, SeverityLevel.MEDIUM),
    (3501, SeverityLevel.HIGH), (10000, SeverityLevel.HIGH),
])
def test_severity_all_boundaries(pixels, expected):
    disease, leaf = _masks(pixels)
    result = SeverityEstimator.estimate_severity(disease, leaf)
    assert result.status == "available"
    assert result.level == expected
    assert result.valid_leaf_pixels == 10000
    assert result.diseased_leaf_pixels == pixels
    assert result.affected_percentage == pytest.approx(pixels / 100)


def test_severity_excludes_disease_outside_selected_leaf_and_overlaps_inside():
    leaf = np.zeros((10, 10), dtype=np.uint8)
    leaf[:, :5] = 1
    disease = np.ones((10, 10), dtype=np.uint8)
    result = SeverityEstimator.estimate_severity(disease, leaf)
    assert result.valid_leaf_pixels == 50
    assert result.diseased_leaf_pixels == 50
    assert result.affected_percentage == 100


def test_severity_empty_leaf_is_explicitly_unavailable():
    result = SeverityEstimator.estimate_severity(np.zeros((4, 4)), np.zeros((4, 4)))
    assert result.status == "unavailable"
    assert result.affected_percentage is None


def test_severity_categories_use_unrounded_area_and_do_not_erase_tiny_lesions():
    leaf = np.ones((100, 1000), dtype=np.uint8)
    disease = np.zeros_like(leaf)
    disease.flat[:15004] = 1
    boundary = SeverityEstimator.estimate_severity(disease, leaf)
    assert boundary.affected_percentage == 15.0
    assert boundary.level == SeverityLevel.MEDIUM

    tiny = np.zeros_like(leaf)
    tiny[0, 0] = 1
    result = SeverityEstimator.estimate_severity(tiny, leaf)
    assert result.affected_percentage == 0.0
    assert result.level == SeverityLevel.LOW
    assert result.score > 0


def test_missing_severity_is_not_aggregated_as_healthy():
    from app.ml.service import PlantAnalysisService
    from app.schemas.inference import ClassificationResult, SeverityResult, SingleLeafAnalysis

    leaf = SingleLeafAnalysis(
        leaf_id=0,
        bounding_box=[0.0, 0.0, 1.0, 1.0],
        leaf_filter_confidence=0.9,
        classification=ClassificationResult(
            primary_class="Tomato___healthy",
            confidence=0.9,
            is_healthy=True,
        ),
        severity=SeverityResult(
            status="unavailable",
            method="unavailable",
            assessment="Missing aligned masks",
        ),
    )

    summary = PlantAnalysisService._summary([leaf])

    assert summary.overall_health_score is None
    assert summary.average_severity_percentage is None
    assert summary.health_status.value == "unknown"


def test_severity_requires_aligned_two_dimensional_masks():
    misaligned = SeverityEstimator.estimate_severity(np.zeros((4, 4)), np.zeros((3, 4)))
    assert misaligned.status == "unavailable"
    with pytest.raises(ValueError):
        SeverityEstimator.estimate_severity(np.zeros((4, 4, 1)), np.ones((4, 4, 1)))


def test_reliability_separates_confidence_and_uncertainty_and_marks_uncalibrated():
    result = OODDetector(entropy_threshold=0.5, min_confidence_threshold=0.4).evaluate_probabilities(
        np.full(38, 1 / 38, dtype=np.float32)
    )
    assert result.classification_confidence == pytest.approx(1 / 38, abs=1e-4)
    assert result.score > result.threshold
    assert result.calibration_status == "incomplete"
    assert result.method.startswith("provisional_")


@pytest.mark.parametrize("values", [np.array([np.nan, 1.]), np.array([-0.1, 1.1]), np.array([[0.4, 0.6]])])
def test_reliability_rejects_unusual_probability_inputs(values):
    with pytest.raises(ValueError):
        OODDetector().evaluate_probabilities(values)


def test_explanation_resizes_to_exact_leaf_crop_and_reports_method():
    class CaptureStorage:
        def put(self, payload, **kwargs):
            self.payload = payload
            self.kwargs = kwargs
            return kwargs["object_key"]

    service = object.__new__(PlantAnalysisService)
    service.storage = CaptureStorage()
    values = np.zeros((224, 224), dtype=np.float32)
    values[20:50, 30:70] = 1
    result = service._persist_attention(values, (61, 83), "test", 0)
    assert result.status == "available"
    assert result.method == "dinov2_attention_rollout"
    assert (result.heatmap_asset.height, result.heatmap_asset.width) == (61, 83)
    with Image.open(io.BytesIO(service.storage.payload)) as image:
        assert image.size == (83, 61)
        assert image.mode == "L"


def test_explanation_without_storage_is_typed_unavailable():
    service = object.__new__(PlantAnalysisService)
    service.storage = None
    result = service._persist_attention(np.ones((224, 224), dtype=np.float32), (64, 64), "test", 0)
    assert result.status == "unavailable"
    assert result.heatmap_asset is None


def test_artifact_storage_failures_do_not_return_a_saved_asset_reference():
    from app.ml.errors import InferenceError, InferenceErrorCode
    from app.storage.errors import StorageError

    class BrokenStorage:
        def put(self, *_args, **_kwargs):
            raise StorageError("provider details must not escape")

    service = object.__new__(PlantAnalysisService)
    service.storage = BrokenStorage()

    with pytest.raises(InferenceError) as error:
        service._persist_mask(np.ones((8, 8), dtype=np.uint8), "scan", "mask.png")

    assert error.value.code == InferenceErrorCode.ARTIFACT_STORAGE_FAILURE
    assert error.value.stage == "artifact_storage"
    assert "provider details" not in str(error.value)


@pytest.mark.parametrize("values", [np.ones((16, 16)), np.full((224, 224), np.nan), -np.ones((224, 224))])
def test_explanation_invalid_or_wrong_shape_fails_gracefully_at_boundary(values):
    service = object.__new__(PlantAnalysisService)
    service.storage = None
    with pytest.raises(Exception):
        service._persist_attention(values, (64, 64), "test", 0)


def test_corrupt_image_is_typed_invalid_image():
    from app.ml.errors import InvalidImageError

    service = PlantAnalysisService(device="cpu")
    with pytest.raises(InvalidImageError):
        service.analyze_bytes(b"not an image")


def test_failed_explanation_does_not_discard_classification():
    from app.tests.test_inference_service import _image, _service

    service, _ = _service(masks=1)
    service.classifier.predict_with_attention = lambda _input: (_ for _ in ()).throw(RuntimeError("attribution failed"))
    result = service.analyze(_image())
    leaf = result.leaves[0]
    assert leaf.classification is not None
    assert leaf.explainability.status == "unavailable"
