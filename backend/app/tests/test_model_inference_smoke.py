"""
Integration Smoke Tests & Output-Shape Validation for Model Adapters.

Tests:
1. DINOv2 Leaf Filter loading, contracts, output shape (1, 2), probability bounds.
2. DINOv2 Disease Classifier loading, contracts, 38-class distribution, top-k formatting.
3. SegFormer-B0 Safetensors loading, contract, binary mask values, and custom target resizing.
4. SAM 2.1 candidate ranking, geometric filtering (excluding whole-image background).
5. End-to-end sequential pipeline on real image with FullScanResult verification.
"""

import math
import os
from pathlib import Path
from uuid import uuid4
import numpy as np
import pytest

from app.ml.adapters.disease_classifier import DinoDiseaseClassifierAdapter
from app.ml.adapters.disease_segmentation import SegFormerDiseaseSegmentationAdapter
from app.ml.adapters.leaf_filter import DinoLeafFilterAdapter
from app.ml.adapters.sam_adapter import Sam2LeafSegmentationAdapter
from app.ml.interfaces.adapter import ModelLoadingStatus
from app.ml.pipeline import PlantAnalysisPipeline
from app.schemas.inference import FullScanResult, SeverityLevel
from app.storage.local import LocalFileObjectStorage


# ---------------------------------------------------------------------------
# 1. DINOv2 Leaf Filter Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(os.getenv("PLANTGUARD_RUN_REAL_MODEL_TESTS") != "1", reason="BLOCKED: requires compatible ML runtime and explicit real-artifact opt-in")
def test_dino_leaf_filter_contracts_and_shapes():
    """Verify DINOv2 leaf filter contracts and forward pass output shape."""
    adapter = DinoLeafFilterAdapter()

    # Contract checks
    in_contract = adapter.get_input_contract()
    out_contract = adapter.get_output_contract()
    assert in_contract.shape == (1, 3, 224, 224)
    assert out_contract.shape == (1, 2)
    assert adapter.get_class_mapping() == {0: "negative", 1: "positive"}

    # Load weights
    loaded = adapter.load(target_device="cpu")
    assert loaded is True
    assert adapter.loading_status == ModelLoadingStatus.READY

    # Forward pass
    dummy_crop = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    preprocessed = adapter.preprocess(dummy_crop)
    assert preprocessed.shape == (1, 3, 224, 224)

    probs = adapter.predict(preprocessed)
    assert probs.shape == (1, 2)
    prob_neg, prob_pos = probs[0, 0], probs[0, 1]
    assert 0.0 <= prob_neg <= 1.0
    assert 0.0 <= prob_pos <= 1.0
    assert math.isclose(prob_neg + prob_pos, 1.0, abs_tol=1e-4)


# ---------------------------------------------------------------------------
# 2. DINOv2 Disease Classifier Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(os.getenv("PLANTGUARD_RUN_REAL_MODEL_TESTS") != "1", reason="BLOCKED: requires compatible ML runtime and explicit real-artifact opt-in")
def test_dino_disease_classifier_38_classes_and_shapes():
    """Verify DINOv2 disease classifier loads 38 classes and produces valid distributions."""
    adapter = DinoDiseaseClassifierAdapter()

    # Contract checks
    in_contract = adapter.get_input_contract()
    out_contract = adapter.get_output_contract()
    assert in_contract.shape == (1, 3, 224, 224)
    assert out_contract.shape == (1, 38)
    assert len(adapter._class_names) == 38

    # Load weights
    loaded = adapter.load(target_device="cpu")
    assert loaded is True
    assert adapter.loading_status == ModelLoadingStatus.READY

    # Forward pass
    dummy_crop = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    preprocessed = adapter.preprocess(dummy_crop)
    probs = adapter.predict(preprocessed)

    assert probs.shape == (1, 38)
    assert math.isclose(float(np.sum(probs)), 1.0, abs_tol=1e-3)

    # Format top-k prediction
    primary_class, conf, top_k, is_healthy = adapter.format_prediction(probs, top_k=5)
    assert primary_class in adapter._class_names
    assert 0.0 <= conf <= 1.0
    assert len(top_k) == 5
    assert primary_class in top_k


# ---------------------------------------------------------------------------
# 3. SegFormer-B0 Disease Segmentation Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(os.getenv("PLANTGUARD_RUN_REAL_MODEL_TESTS") != "1", reason="BLOCKED: requires compatible ML runtime and explicit real-artifact opt-in")
def test_segformer_b0_safetensors_loading_and_resizing():
    """Verify local SegFormer safetensors loads without network and upsamples cleanly."""
    adapter = SegFormerDiseaseSegmentationAdapter()

    # Contract checks
    in_contract = adapter.get_input_contract()
    out_contract = adapter.get_output_contract()
    assert in_contract.shape == (1, 3, 512, 512)
    assert adapter.get_class_mapping() == {0: "background", 1: "diseased_region"}

    # Load weights
    loaded = adapter.load(target_device="cpu")
    assert loaded is True
    assert adapter.loading_status == ModelLoadingStatus.READY

    # Default output resolution
    dummy_img = np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8)
    preprocessed = adapter.preprocess(dummy_img)
    mask_default = adapter.predict(preprocessed)
    assert mask_default.shape == (512, 512)
    assert set(np.unique(mask_default)).issubset({0, 1})

    # Custom target shape upsampling (e.g. non-square original leaf crop)
    custom_target = (300, 450)
    mask_resized = adapter.predict(preprocessed, original_shape=custom_target)
    assert mask_resized.shape == custom_target
    assert set(np.unique(mask_resized)).issubset({0, 1})


# ---------------------------------------------------------------------------
# 4. SAM 2.1 Candidate Pruning Tests
# ---------------------------------------------------------------------------

def test_sam2_candidate_filtering_rejects_full_image_background():
    """Verify SAM2 adapter geometric pruning rejects masks that swallow the entire canvas."""
    adapter = Sam2LeafSegmentationAdapter()

    h, w = 600, 800
    total = h * w

    # Synthesize two raw masks:
    # 1. Background mask covering 96% of the canvas (should be discarded)
    # 2. Central leaf candidate covering 25% of canvas (should be kept)
    bg_mask = np.ones((h, w), dtype=bool)
    leaf_mask = np.zeros((h, w), dtype=bool)
    leaf_mask[150:450, 200:600] = True

    mock_masks = [
        {"segmentation": bg_mask, "bbox": [0, 0, w, h], "area": int(total * 0.96), "predicted_iou": 0.99},
        {"segmentation": leaf_mask, "bbox": [200, 150, 400, 300], "area": int(total * 0.25), "predicted_iou": 0.92},
    ]

    filtered = adapter._filter_and_rank_leaf_candidates(mock_masks, (h, w))

    # Background canvas MUST be rejected
    assert len(filtered) == 1
    assert filtered[0]["area"] == int(total * 0.25)
    # Bounding box must be normalized [ymin, xmin, ymax, xmax]
    ymin, xmin, ymax, xmax = filtered[0]["bbox"]
    assert 0.0 <= ymin < ymax <= 1.0
    assert 0.0 <= xmin < xmax <= 1.0


# ---------------------------------------------------------------------------
# 5. End-to-End Pipeline Execution Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(os.getenv("PLANTGUARD_RUN_REAL_MODEL_TESTS") != "1", reason="BLOCKED: requires compatible ML runtime, SAM2 config, and explicit real-artifact opt-in")
def test_end_to_end_pipeline_with_real_weights(tmp_path):
    """Run full sequential pipeline on real sample image with model weights active."""
    storage = LocalFileObjectStorage(root=tmp_path)
    pipeline = PlantAnalysisPipeline(storage=storage)

    # Load actual weights
    pipeline.leaf_filter.load("cpu")
    pipeline.classifier.load("cpu")
    pipeline.segmenter.load("cpu")

    # Locate sample image
    repository_root = Path(__file__).resolve().parents[3]
    image_path = repository_root / "IMAGE_APP.jpg"
    if not image_path.exists():
        image_path = Path("plant.jpg")
    if not image_path.exists():
        image_path = Path("../plant.jpg")

    assert image_path.exists(), "IMAGE_APP.jpg or plant.jpg required for integration test"
    with open(image_path, "rb") as f:
        img_bytes = f.read()

    scan_result: FullScanResult = pipeline.execute_scan(
        image_bytes=img_bytes,
        analysis_id=uuid4(),
        user_id=uuid4(),
    )

    assert scan_result.status in {"completed", "partial"}
    assert scan_result.hardware_device == "cpu"
    assert scan_result.processing_time_ms > 0
    assert len(scan_result.leaves) >= 1

    leaf = scan_result.leaves[0]
    assert leaf.is_leaf is True
    assert leaf.leaf_filter_confidence > 0.50
    assert leaf.classification is not None
    assert leaf.classification.primary_class is not None
    assert leaf.segmentation is not None
    assert leaf.severity is not None

    summary = scan_result.plant_summary
    assert summary.health_status is not None
    if summary.overall_health_score is not None:
        assert summary.overall_health_score >= 0.0
