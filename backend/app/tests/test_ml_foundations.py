"""
Unit tests for PlantGuard AI ML Foundations (Phase B & C).

Tests:
1. Versioned Pydantic schemas and mask asset separation.
2. Mask-based severity estimation and lesion counting.
3. Out-of-Distribution (OOD) statistical detection.
4. Model registry artifact discovery and readiness reporting.
5. Device selection and CPU fallback on Vivobook.
6. Pipeline orchestration and missing-model degradation behavior.
"""

import io
from pathlib import Path
from uuid import uuid4
import numpy as np
import pytest
from PIL import Image

from app.ml.device import DeviceManager, device_manager
from app.ml.interfaces.adapter import (
    BaseModelAdapter,
    EvaluationStatus,
    FailureBehavior,
    ModelLoadingStatus,
)
from app.ml.ood import OODDetector
from app.ml.pipeline import PlantAnalysisPipeline
from app.ml.registry import ModelRegistry, model_registry
from app.ml.severity import SeverityEstimator
from app.schemas.inference import (
    ClassificationResult,
    FullScanResult,
    MaskAsset,
    OODResult,
    OverallHealthStatus,
    PartialFailure,
    PipelineWarning,
    PlantHealthSummary,
    SegmentationResult,
    SeverityLevel,
    SeverityResult,
    SingleLeafAnalysis,
    WarningSeverity,
)
from app.storage.local import LocalFileObjectStorage


# ---------------------------------------------------------------------------
# 1. Schema & Asset Tests
# ---------------------------------------------------------------------------

def test_mask_asset_schema_separation():
    """Verify mask assets use pointers rather than serializing 2D pixel grids."""
    asset = MaskAsset(
        storage_key="users/123/analyses/abc/masks/leaf_0_disease.png",
        content_type="image/png",
        width=512,
        height=512,
        byte_size=14200,
    )
    dumped = asset.model_dump()
    assert dumped["storage_key"].endswith(".png")
    assert dumped["width"] == 512
    assert dumped["height"] == 512
    assert "mask" not in dumped  # No inline pixel grid


def test_full_scan_result_schema_validation():
    """Validate full scan response with nested models."""
    scan = FullScanResult(
        analysis_id=str(uuid4()),
        status="completed",
        hardware_device="cpu",
        processing_time_ms=145,
        model_versions={"dino_classifier": "v1"},
        leaves=[
            SingleLeafAnalysis(
                leaf_id=0,
                bounding_box=[0.1, 0.1, 0.9, 0.9],
                is_leaf=True,
                leaf_filter_confidence=0.98,
                classification=ClassificationResult(
                    primary_class="Tomato___Late_blight",
                    confidence=0.94,
                    is_healthy=False,
                    crop_type="Tomato",
                    disease_name="Late blight",
                    top_k_probabilities={"Tomato___Late_blight": 0.94, "Tomato___healthy": 0.04},
                ),
                ood=OODResult(score=0.15, threshold=0.65, is_ood=False, method="entropy"),
                severity=SeverityResult(
                    score=0.12,
                    level=SeverityLevel.LOW,
                    affected_percentage=12.0,
                    lesion_count=3,
                    assessment="Mild infection",
                ),
                warnings=[],
            )
        ],
        plant_summary=PlantHealthSummary(
            overall_health_score=82.0,
            health_status=OverallHealthStatus.MILDLY_DISEASED,
            total_leaves_detected=1,
            valid_leaves_analyzed=1,
            healthy_leaves_count=0,
            diseased_leaves_count=1,
            primary_diagnosis="Late blight",
            disease_breakdown={"Late blight": 1},
            average_severity_percentage=12.0,
            recommendations=["Isolate plant", "Prune lower foliage"],
        ),
        warnings=[],
        partial_failures=[],
    )
    assert scan.schema_version == "2.0.0"
    assert len(scan.leaves) == 1
    assert scan.leaves[0].classification.primary_class == "Tomato___Late_blight"


# ---------------------------------------------------------------------------
# 2. Mask-Based Severity Estimator Tests
# ---------------------------------------------------------------------------

def test_severity_estimator_healthy():
    """Zero diseased pixels yields HEALTHY categorical rating."""
    mask = np.zeros((100, 100), dtype=np.uint8)
    sev = SeverityEstimator.estimate_severity(disease_mask=mask, leaf_mask=np.ones_like(mask))
    assert sev.level == SeverityLevel.HEALTHY
    assert sev.score == 0.0
    assert sev.affected_percentage == 0.0
    assert sev.lesion_count == 0


def test_severity_estimator_low_infection():
    """Lesion area <= 15% yields LOW categorical rating."""
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[20:30, 20:30] = 1  # 100 pixels out of 10,000 = 1.0%
    sev = SeverityEstimator.estimate_severity(disease_mask=mask, leaf_mask=np.ones_like(mask))
    assert sev.level == SeverityLevel.LOW
    assert sev.affected_percentage == 1.0
    assert sev.lesion_count == 1


def test_severity_estimator_medium_infection():
    """Lesion area between 15% and 35% yields MEDIUM categorical rating."""
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[:20, :] = 1  # 2000 pixels out of 10,000 = 20.0%
    sev = SeverityEstimator.estimate_severity(disease_mask=mask, leaf_mask=np.ones_like(mask))
    assert sev.level == SeverityLevel.MEDIUM
    assert sev.affected_percentage == 20.0


def test_severity_estimator_high_infection():
    """Lesion area > 35% yields HIGH categorical rating."""
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[:50, :] = 1  # 5000 pixels out of 10,000 = 50.0%
    sev = SeverityEstimator.estimate_severity(disease_mask=mask, leaf_mask=np.ones_like(mask))
    assert sev.level == SeverityLevel.HIGH
    assert sev.affected_percentage == 50.0


def test_severity_bounding_box_computation():
    """Test normalized bounding box extraction from mask."""
    mask = np.zeros((100, 200), dtype=np.uint8)
    mask[10:50, 20:80] = 1  # rows 10-49, cols 20-79
    bbox = SeverityEstimator.compute_disease_bounding_box(mask)
    assert bbox is not None
    ymin, xmin, ymax, xmax = bbox
    assert ymin == pytest.approx(0.10, abs=0.01)
    assert xmin == pytest.approx(0.10, abs=0.01)
    assert ymax == pytest.approx(0.50, abs=0.01)
    assert xmax == pytest.approx(0.40, abs=0.01)


# ---------------------------------------------------------------------------
# 3. Out-of-Distribution (OOD) Detector Tests
# ---------------------------------------------------------------------------

def test_ood_detector_confident_in_distribution():
    """Highly peaked probability vector is evaluated as In-Distribution."""
    probs = np.zeros(38, dtype=np.float32)
    probs[5] = 0.95
    probs[6] = 0.05
    detector = OODDetector(entropy_threshold=0.65, min_confidence_threshold=0.40)
    result = detector.evaluate_probabilities(probs)
    assert result.is_ood is False
    assert result.score < 0.30


def test_ood_detector_high_entropy_uniform_distribution():
    """Uniform probabilities denote extreme uncertainty, flagged as OOD."""
    probs = np.ones(38, dtype=np.float32) / 38.0
    detector = OODDetector(entropy_threshold=0.65, min_confidence_threshold=0.40)
    result = detector.evaluate_probabilities(probs)
    assert result.is_ood is True
    assert result.score > 0.90


def test_ood_detector_low_confidence_flag():
    """Peak probability below minimum confidence threshold is flagged as OOD."""
    probs = np.zeros(38, dtype=np.float32)
    probs[:4] = 0.25  # Max confidence is 0.25 < 0.40
    detector = OODDetector(min_confidence_threshold=0.40)
    result = detector.evaluate_probabilities(probs)
    assert result.is_ood is True


# ---------------------------------------------------------------------------
# 4. Model Registry & Artifact Discovery Tests
# ---------------------------------------------------------------------------

def test_model_registry_artifact_discovery():
    """Verify model registry discovers existing checkpoints on disk."""
    reg = ModelRegistry()
    inventory = reg.get_artifact_inventory(force_refresh=True)

    assert "leaf_filter" in inventory
    assert "disease_classifier" in inventory
    assert "disease_segmentation" in inventory
    assert "leaf_instance_segmentation" in inventory

    # Check physical paths and validity
    lf = inventory["leaf_filter"]
    assert lf.resolved_path is not None
    assert lf.size_bytes > 50_000_000

    dc = inventory["disease_classifier"]
    assert dc.resolved_path is not None
    assert dc.metadata.get("num_classes") == 38

    ds = inventory["disease_segmentation"]
    assert ds.resolved_path is not None
    assert ds.format_type == "safetensors"


def test_model_registry_efficientnet_rule_enforced():
    """Confirm EfficientNet is strictly absent from the model registry."""
    report = model_registry.get_readiness_report()
    assert report["efficientnet_rule_enforced"] is True
    for comp_key, comp_val in report["components"].items():
        assert "efficientnet" not in comp_key.lower()
        assert "efficientnet" not in comp_val["name"].lower()


# ---------------------------------------------------------------------------
# 5. Hardware Device Selection Tests
# ---------------------------------------------------------------------------

def test_device_manager_resolution():
    """Verify device manager resolves safely to CPU on Vivobook without CUDA."""
    dm = DeviceManager(preferred_device="cpu")
    assert dm.active_device == "cpu"
    assert dm.is_cuda() is False
    summary = dm.get_hardware_summary()
    assert "active_device" in summary
    assert "disk_free_gb" in summary


# ---------------------------------------------------------------------------
# 6. Pipeline Orchestration & Degraded Behavior Tests
# ---------------------------------------------------------------------------

def test_pipeline_fails_closed_when_sam_config_is_missing():
    """A green synthetic image must not trigger heuristic success without SAM2."""
    from app.ml.errors import InferenceErrorCode, ModelCapabilityError

    pipeline = PlantAnalysisPipeline()
    img = Image.new("RGB", (128, 128), color=(45, 130, 45))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    with pytest.raises(ModelCapabilityError) as exc:
        pipeline.execute_scan(buf.getvalue())
    assert exc.value.code in {InferenceErrorCode.MISSING_ARTIFACT, InferenceErrorCode.UNSUPPORTED_RUNTIME}
