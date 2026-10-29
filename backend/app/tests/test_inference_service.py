"""CPU-safe contract tests with controlled adapters; these are not model accuracy tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.ml.adapters.disease_segmentation import SegFormerDiseaseSegmentationAdapter
from app.ml.adapters.leaf_filter import DinoLeafFilterAdapter
from app.ml.adapters.disease_classifier import DinoDiseaseClassifierAdapter
from app.ml.adapters.sam_adapter import Sam2LeafSegmentationAdapter
from app.ml.errors import (
    InferenceError,
    InferenceErrorCode,
    InferenceTimeoutError,
    InvalidImageError,
    ModelCapabilityError,
    NoLeafFoundError,
)
from app.ml.contracts import DiseasePrediction, LeafCandidate, LeafFilterScore, SegmentationPrediction, StageMetadata, StageOutput
from app.ml.service import PlantAnalysisService
from app.schemas.inference import OODResult
from app.ml.ood import OODDetector


class FakeAdapter:
    def __init__(self, name, events, predict):
        self.name = name
        self.events = events
        self._predict = predict
        self.artifact_path = Path(__file__)  # present: no filesystem/model setup needed
        self.artifact_version = f"test-{name}"
        self.loading_status = "ready"
        self.active_device = "cpu"
        self.last_error = None
        self.load_error_code = None
        self.unloaded = False

    def is_ready(self):
        return True

    def load(self, device):
        self.events.append(("load", self.name))
        return True

    def unload(self):
        self.unloaded = True

    def preprocess(self, image):
        assert image.dtype == np.uint8 and image.ndim == 3 and image.shape[2] == 3
        size = 512 if self.name == "segmenter" else 224
        return np.zeros((1, 3, size, size), dtype=np.float32)

    def predict(self, value, **kwargs):
        self.events.append(("predict", self.name))
        return self._predict(value, **kwargs)


class FakeOODDetector:
    def __init__(self, result):
        self.result = result

    def evaluate_probabilities(self, probabilities):
        return OODDetector().evaluate_probabilities(probabilities)

    def evaluate_features(self, features, predicted_class, confidence=None):
        if features is None:
            raise ValueError("test classifier did not provide features")
        return self.result


def _service(*, masks=2, no_filter=False, segment_mask=None, timeout=2.0, ood_result=None):
    events = []
    h, w = 80, 100
    leaf_mask = np.zeros((h, w), dtype=bool)
    leaf_mask[10:70, 10:45] = True
    leaf_mask2 = np.zeros((h, w), dtype=bool)
    leaf_mask2[10:70, 55:90] = True
    candidate_items = []
    if masks >= 1:
        candidate_items.append({"segmentation": leaf_mask, "bbox": [0.125, 0.1, 0.875, 0.45], "area": int(leaf_mask.sum()), "score": .9, "method": "sam2.1_automatic_mask_generator"})
    if masks >= 2:
        candidate_items.append({"segmentation": leaf_mask2, "bbox": [0.125, 0.55, 0.875, 0.9], "area": int(leaf_mask2.sum()), "score": .8, "method": "sam2.1_automatic_mask_generator"})
    sam = FakeAdapter("sam", events, lambda *_a, **_k: candidate_items)
    leaf = FakeAdapter("leaf", events, lambda *_a, **_k: np.array([[1., 0.]], dtype=np.float32) if no_filter else np.array([[.05, .95]], dtype=np.float32))
    classifier = FakeAdapter("classifier", events, lambda *_a, **_k: np.eye(1, 38, 3, dtype=np.float32))
    classifier.get_class_mapping = lambda: {i: f"Crop___class_{i}" for i in range(38)}
    def classify_with_attention(_x, return_features=False):
        events.append(("predict", "classifier"))
        probabilities = np.eye(1, 38, 3, dtype=np.float32)
        attention = np.ones((224, 224), dtype=np.float32)
        if return_features:
            return probabilities, attention, np.zeros(768, dtype=np.float32)
        return probabilities, attention
    classifier.predict_with_attention = classify_with_attention
    classifier.predict_with_features = lambda _x: (
        np.eye(1, 38, 3, dtype=np.float32),
        np.zeros(768, dtype=np.float32),
    )
    seg = FakeAdapter("segmenter", events, lambda _input, **kwargs: (segment_mask((kwargs["original_shape"][0], kwargs["original_shape"][1])) if callable(segment_mask)
                          else segment_mask if segment_mask is not None
                          else np.zeros(kwargs["original_shape"], dtype=np.uint8)))
    seg.get_class_mapping = lambda: {0: "background", 1: "diseased_region"}
    ood = ood_result or OODResult(
        score=0.0,
        threshold=2.0,
        is_ood=False,
        method="class_conditional_mahalanobis",
        status="ood_unvalidated",
        calibration_status="in_distribution_percentile_99_only",
    )
    service = PlantAnalysisService(sam=sam, leaf_filter=leaf, classifier=classifier,
                                   segmenter=seg, ood_detector=FakeOODDetector(ood),
                                   device="cpu", timeout_seconds=timeout)
    return service, events


def _image():
    return np.full((80, 100, 3), 120, dtype=np.uint8)


def test_pipeline_order_contracts_and_timing():
    service, events = _service(masks=1)
    result = service.analyze(_image(), analysis_id="contract-test")
    stages = [name for op, name in events if op == "predict"]
    assert stages == ["sam", "leaf", "classifier", "segmenter"]
    assert result.analysis_id == "contract-test"
    assert result.leaves[0].candidate_source == "test-sam"
    assert result.leaves[0].classification.primary_class == "Crop___class_3"
    assert result.leaves[0].segmentation.total_leaf_pixels > 0
    assert set(result.stage_timings_ms) == {
        "leaf_candidate_generation",
        "leaf_filter",
        "classifier",
        "ood_detection",
        "segmentation_and_severity",
    }
    assert result.sam_variant == "test-sam"
    assert result.sam_fallback_applied is False
    assert result.candidate_counts.model_dump() == {
        "generated": 1,
        "valid": 1,
        "deduplicated": 1,
        "leaf_filter_accepted": 1,
        "disease_analysis_eligible": 1,
    }
    assert result.leaves[0].explainability.method == "dinov2_attention_rollout"
    assert result.leaves[0].prediction_uncertainty.calibration_status == "incomplete"
    assert result.plant_summary.recommendations == []


def test_segmentation_failure_preserves_classification_as_partial_result():
    service, _ = _service(masks=1)

    def fail_segmentation(*_args, **_kwargs):
        raise RuntimeError("segmentation unavailable")

    service.segmenter.predict = fail_segmentation

    result = service.analyze(_image())

    assert result.status == "partial"
    assert len(result.leaves) == 1
    assert result.leaves[0].classification.primary_class == "Crop___class_3"
    assert result.leaves[0].segmentation is None
    assert result.leaves[0].severity.status == "unavailable"
    assert result.plant_summary.valid_leaves_analyzed == 1
    assert result.plant_summary.average_severity_percentage is None
    assert result.partial_failures[0].component == "disease_segmentation"
    assert result.partial_failures[0].fallback_applied is True


def test_partial_segmentation_keeps_completed_leaf_masks_without_claiming_overall_severity():
    service, _ = _service(masks=2)
    calls = 0

    def fail_second_segmentation(_input, *, original_shape):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("segmentation unavailable")
        return np.zeros(original_shape, dtype=np.uint8)

    service.segmenter._predict = fail_second_segmentation

    result = service.analyze(_image())

    assert result.status == "partial"
    assert len(result.leaves) == 2
    assert result.leaves[0].segmentation is not None
    assert result.leaves[1].segmentation is None
    assert all(leaf.classification is not None for leaf in result.leaves)
    assert result.plant_summary.average_severity_percentage is None
    assert result.plant_summary.overall_health_score is None


def test_pipeline_makes_readonly_rgb_input_safe_for_model_adapters():
    service, _ = _service(masks=1)
    original = _image()
    original.setflags(write=False)
    received = []
    service.sam.predict = lambda image: received.append((image.flags.writeable, image.flags.c_contiguous)) or [
        {
            "segmentation": np.pad(np.ones((60, 35), dtype=bool), ((10, 10), (10, 55))),
            "bbox": [0.125, 0.1, 0.875, 0.45],
            "area": 2100,
            "score": 0.9,
            "method": "sam2.1_automatic_mask_generator",
        }
    ]

    service.analyze(original)

    assert received == [(True, True)]


def test_multiple_leaf_candidates_are_analyzed():
    service, _ = _service(masks=2)
    result = service.analyze(_image())
    assert len(result.leaves) == 2


def test_duplicate_candidates_are_removed_before_leaf_filtering():
    service, _ = _service(masks=2)
    first_mask = np.zeros((80, 100), dtype=bool)
    first_mask[10:70, 10:45] = True
    second_mask = np.zeros((80, 100), dtype=bool)
    second_mask[10:70, 55:90] = True
    service.sam._predict = lambda *_args, **_kwargs: [
        {
            "segmentation": first_mask,
            "bbox": [0.125, 0.1, 0.875, 0.45],
            "score": 0.9,
            "method": "sam2.1_automatic_mask_generator",
        },
        {
            "segmentation": first_mask.copy(),
            "bbox": [0.125, 0.1, 0.875, 0.45],
            "score": 0.8,
            "method": "sam2.1_automatic_mask_generator",
        },
        {
            "segmentation": second_mask,
            "bbox": [0.125, 0.55, 0.875, 0.9],
            "score": 0.7,
            "method": "sam2.1_automatic_mask_generator",
        },
    ]

    result = service.analyze(_image())

    assert len(result.leaves) == 2
    assert result.candidate_counts.generated == 3
    assert result.candidate_counts.valid == 3
    assert result.candidate_counts.deduplicated == 2
    assert result.candidate_counts.leaf_filter_accepted == 2
    assert result.candidate_counts.disease_analysis_eligible == 2


def test_ood_threshold_exceedance_withholds_class_and_plant_diagnosis():
    ood = OODResult(
        score=3.0,
        threshold=2.0,
        is_ood=True,
        method="class_conditional_mahalanobis",
        status="ood_unvalidated",
        calibration_status="in_distribution_percentile_99_only",
    )
    service, _ = _service(masks=1, ood_result=ood)

    result = service.analyze(_image())

    assert result.leaves[0].classification is None
    assert result.leaves[0].ood.is_ood is True
    assert any(w.code == "OOD_ABSTENTION_UNVALIDATED" for w in result.leaves[0].warnings)
    assert result.plant_summary.health_status.value == "unknown"
    assert result.plant_summary.valid_leaves_analyzed == 0
    assert result.plant_summary.primary_diagnosis is None


def test_ood_scoring_failure_fails_the_inference_request():
    class FailedOODDetector(FakeOODDetector):
        def evaluate_features(self, *_args, **_kwargs):
            raise InferenceError(
                InferenceErrorCode.INVALID_MODEL_OUTPUT,
                "OOD scoring failed",
                stage="ood_detection",
            )

    service, _ = _service(
        masks=1,
        ood_result=OODResult(
            score=0.0,
            threshold=2.0,
            is_ood=False,
            method="class_conditional_mahalanobis",
            status="ood_unvalidated",
            calibration_status="in_distribution_percentile_99_only",
        ),
    )
    service.ood_detector = FailedOODDetector(service.ood_detector.result)

    with pytest.raises(InferenceError) as exc:
        service.analyze(_image())

    assert exc.value.stage == "ood_detection"
    assert exc.value.code == InferenceErrorCode.INVALID_MODEL_OUTPUT


def test_no_sam_candidates_raises_typed_error_without_fabricating_leaf():
    service, events = _service(masks=0)
    service.mobile_sam = FakeAdapter("mobile_sam", events, lambda *_a, **_k: [])
    with pytest.raises(NoLeafFoundError) as exc:
        service.analyze(_image())
    assert exc.value.code == InferenceErrorCode.NO_LEAF_FOUND
    assert [name for op, name in events if op == "predict"] == ["sam", "mobile_sam"]


def test_candidates_rejected_by_filter_raise_no_leaf():
    service, _ = _service(masks=1, no_filter=True)
    with pytest.raises(NoLeafFoundError):
        service.analyze(_image())


@pytest.mark.parametrize("image", [np.zeros((0, 10, 3), dtype=np.uint8), np.zeros((10, 10), dtype=np.uint8), np.zeros((10, 10, 3), dtype=np.float32)])
def test_invalid_image_contract(image):
    service, _ = _service()
    with pytest.raises(InvalidImageError):
        service.analyze(image)


def test_corrupt_encoded_image_raises_typed_error():
    service, _ = _service()
    with pytest.raises(InvalidImageError):
        service.analyze_bytes(b"not an image")

def test_encoded_image_exif_orientation_is_applied_before_inference(monkeypatch):
    service, _ = _service()
    original = Image.new("RGB", (2, 3), color=(20, 40, 60))
    exif = original.getexif()
    exif[274] = 6  # Rotate 90 degrees clockwise for display.
    encoded = __import__("io").BytesIO()
    original.save(encoded, format="JPEG", exif=exif)
    captured = []
    monkeypatch.setattr(service, "analyze", lambda image, analysis_id=None: captured.append(image.copy()) or "decoded")

    result = service.analyze_bytes(encoded.getvalue(), analysis_id="orientation-test")

    assert result == "decoded"
    assert len(captured) == 1
    assert captured[0].shape == (2, 3, 3)
    assert captured[0].dtype == np.uint8


def test_missing_model_artifact_is_a_capability_error():
    service, _ = _service(masks=1)
    service.sam.is_ready = lambda: False
    service.sam.artifact_path = Path("missing-sam-checkpoint.pt")
    service.mobile_sam = FakeAdapter("mobile_sam", [], lambda *_a, **_k: [])
    service.mobile_sam.is_ready = lambda: False
    service.mobile_sam.artifact_path = Path("missing-mobile-sam-checkpoint.pt")
    with pytest.raises(ModelCapabilityError) as exc:
        service.analyze(_image())
    assert exc.value.code == InferenceErrorCode.UNSUPPORTED_RUNTIME
    assert "sam2:" in str(exc.value)
    assert "mobilesam:" in str(exc.value)


def test_model_loader_failure_is_reported_when_fallback_also_fails():
    service, events = _service(masks=1)
    service.sam.is_ready = lambda: False
    service.sam.load = lambda _device: False
    service.sam.last_error = "CUDA runtime unsupported"
    service.sam.load_error_code = InferenceErrorCode.UNSUPPORTED_RUNTIME
    service.mobile_sam = FakeAdapter("mobile_sam", events, lambda *_a, **_k: [])
    service.mobile_sam.is_ready = lambda: False
    service.mobile_sam.load = lambda _device: False
    service.mobile_sam.last_error = "PyTorch package unavailable"
    service.mobile_sam.load_error_code = InferenceErrorCode.UNSUPPORTED_RUNTIME
    with pytest.raises(ModelCapabilityError) as exc:
        service.analyze(_image())
    assert exc.value.code == InferenceErrorCode.UNSUPPORTED_RUNTIME
    assert "sam2:" in str(exc.value)
    assert "mobilesam:" in str(exc.value)
    assert [event for event in events if event[0] == "predict"] == []


def test_sam2_unavailable_falls_back_to_mobilesam_and_marks_result(monkeypatch):
    service, events = _service(masks=1)
    mobile_items = [{
        "segmentation": np.pad(np.ones((60, 35), dtype=bool), ((10, 10), (10, 55))),
        "bbox": [0.125, 0.125, 0.875, 0.45],
        "score": .9,
        "method": "mobilesam.point_grid_predictor",
    }]
    service.mobile_sam = FakeAdapter("mobile_sam_instance_segmentation", events, lambda *_a, **_k: mobile_items)
    original_with_model = service._with_model

    def fail_sam2_then_run_fallback(adapter, stage, operation):
        if adapter is service.sam:
            raise ModelCapabilityError(
                InferenceErrorCode.UNSUPPORTED_RUNTIME,
                "SAM2 runtime is blocked",
                stage="variant_selection",
            )
        return original_with_model(adapter, stage, operation)

    monkeypatch.setattr(service, "_with_model", fail_sam2_then_run_fallback)
    result = service.analyze(_image(), analysis_id="mobilesam-fallback-test")

    assert result.status == "completed"
    assert result.sam_variant == "test-mobile_sam_instance_segmentation"
    assert result.sam_fallback_applied is True
    assert result.model_versions["leaf_proposals"] == "test-mobile_sam_instance_segmentation"
    assert result.warnings[0].code == "MODEL_FALLBACK_APPLIED"
    assert [name for op, name in events if op == "predict"] == [
        "mobile_sam_instance_segmentation", "leaf", "classifier", "segmenter",
    ]


def test_sam2_success_does_not_load_or_run_mobilesam():
    service, events = _service(masks=1)
    service.mobile_sam = FakeAdapter(
        "mobile_sam_instance_segmentation",
        events,
        lambda *_a, **_k: pytest.fail("MobileSAM must not run when SAM2 succeeds"),
    )

    result = service.analyze(_image())

    assert result.sam_variant == "test-sam"
    assert result.sam_fallback_applied is False
    assert [name for op, name in events if op == "predict"] == ["sam", "leaf", "classifier", "segmenter"]


def test_both_proposal_models_unavailable_returns_actionable_variant_list():
    service, _ = _service(masks=1)
    service.mobile_sam = FakeAdapter("mobile_sam_instance_segmentation", [], lambda *_a, **_k: [])

    def unavailable(adapter, stage, _operation):
        raise ModelCapabilityError(
            InferenceErrorCode.UNSUPPORTED_RUNTIME,
            f"{stage} runtime requirement is unavailable",
            stage="variant_selection",
        )

    service._with_model = unavailable
    with pytest.raises(ModelCapabilityError) as exc:
        service._sam_candidates(_image(), {})

    assert exc.value.stage == "variant_selection"
    assert "requested runtime 'cpu'" in str(exc.value)
    assert "sam2: sam2 runtime requirement is unavailable" in str(exc.value)
    assert "mobilesam: mobilesam runtime requirement is unavailable" in str(exc.value)


def test_incompatible_segformer_config_fails_closed_without_model_import():
    adapter = SegFormerDiseaseSegmentationAdapter(
        artifact_path=Path("present-but-not-loaded.safetensors"),
        config_path=Path("missing-config.json"),
    )
    assert adapter.get_class_mapping() == {0: "background", 1: "diseased_region"}
    assert adapter.load("cpu") is False
    assert "configuration" in adapter.last_error.lower()


def test_invalid_stage_distribution_cannot_become_prediction():
    service, _ = _service(masks=1)
    service.leaf_filter._predict = lambda *_a, **_k: np.array([[np.nan, np.nan]])
    with pytest.raises(Exception) as exc:
        service.analyze(_image())
    assert getattr(exc.value, "code", None) == InferenceErrorCode.INVALID_MODEL_OUTPUT


def test_inference_capacity_timeout_is_explicit():
    service, _ = _service(timeout=0.01)
    assert service._inference_slot.acquire(timeout=0.1)
    try:
        with pytest.raises(InferenceTimeoutError):
            service.analyze(_image())
    finally:
        service._inference_slot.release()


def test_unloaded_adapters_do_not_return_mock_predictions():
    service, _ = _service(masks=1)
    service.leaf_filter.is_ready = lambda: False
    service.leaf_filter.artifact_path = Path("unavailable-filter.pt")
    with pytest.raises(ModelCapabilityError):
        service.analyze(_image())


def test_each_unloaded_adapter_fails_without_heuristic_or_mock_success():
    with pytest.raises(RuntimeError):
        DinoLeafFilterAdapter().predict(np.zeros((1, 3, 224, 224), dtype=np.float32))
    with pytest.raises(RuntimeError):
        DinoDiseaseClassifierAdapter().predict(np.zeros((1, 3, 224, 224), dtype=np.float32))
    with pytest.raises(RuntimeError):
        SegFormerDiseaseSegmentationAdapter().predict(np.zeros((1, 3, 512, 512), dtype=np.float32))
    with pytest.raises(ModelCapabilityError):
        Sam2LeafSegmentationAdapter().predict(_image())


def test_unmapped_segmentation_class_preserves_partial_classification():
    service, _ = _service(masks=1, segment_mask=lambda shape: np.full(shape, 2, dtype=np.uint8))
    result = service.analyze(_image())
    assert result.status == "partial"
    assert result.leaves[0].classification.primary_class == "Crop___class_3"
    assert result.leaves[0].segmentation is None
    assert result.leaves[0].severity.status == "unavailable"
    assert result.partial_failures[0].error_type == InferenceErrorCode.INVALID_MODEL_OUTPUT.value


def test_missing_disease_mask_preserves_partial_classification():
    service, _ = _service(masks=1, segment_mask=None)
    # Override the default fake empty mask with an absent model output.
    service.segmenter._predict = lambda *_args, **_kwargs: None
    result = service.analyze(_image())
    assert result.status == "partial"
    assert result.leaves[0].classification.primary_class == "Crop___class_3"
    assert result.leaves[0].segmentation is None
    assert result.leaves[0].severity.status == "unavailable"
    assert result.partial_failures[0].error_type == "no_disease_mask"


def test_segformer_mapping_matches_present_training_metadata():
    adapter = SegFormerDiseaseSegmentationAdapter()
    assert adapter._configuration_error is None
    assert adapter.get_class_mapping() == {0: "background", 1: "diseased_region"}
    assert adapter.get_preprocessing_spec().target_size == (512, 512)


def test_typed_stage_outputs_reject_invalid_scores_mappings_and_dimensions():
    mask = np.ones((2, 3), dtype=bool)
    candidate = LeafCandidate(mask, (0.0, 0.0, 1.0, 1.0), .8, 6, "sam-test")
    assert candidate.mask.shape == (2, 3)
    with pytest.raises(ValueError):
        LeafFilterScore(float("nan"), False, "filter-test")
    with pytest.raises(ValueError):
        DiseasePrediction(38, "invalid", 1.0, tuple([1.0] + [0.0] * 37), "classifier-test")
    with pytest.raises(ValueError):
        SegmentationPrediction(np.full((2, 3), 2, dtype=np.uint8), {0: "background", 1: "diseased_region"}, "seg-test")


def test_stage_output_carries_runtime_version_and_elapsed_time():
    metadata = StageMetadata("sam2", "sam-test", "cpu", 17)
    output = StageOutput(value=("candidate",), metadata=metadata)
    assert output.metadata.runtime == "cpu"
    assert output.metadata.duration_ms == 17
