"""Real artifact smoke test; deliberately blocked unless explicitly enabled in an ML environment."""

import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.ml.adapters.mobile_sam_adapter import MobileSamLeafSegmentationAdapter
from app.ml.adapters.sam_adapter import Sam2LeafSegmentationAdapter
from app.ml.runtime import collect_runtime_capabilities
from app.ml.service import PlantAnalysisService
from app.ml.variants import ModelVariantRegistry


pytestmark = pytest.mark.skipif(
    os.getenv("PLANTGUARD_RUN_REAL_MODEL_TESTS") != "1",
    reason="BLOCKED: real SAM2/DINO/SegFormer smoke requires compatible ML runtime and verified SAM config; opt in on a prepared host",
)


def test_real_sam_and_mobilesam_cpu_candidates_on_fixture():
    repository_root = Path(__file__).resolve().parents[3]
    with Image.open(repository_root / "IMAGE_APP.jpg") as source:
        image = np.asarray(source.convert("RGB"), dtype=np.uint8)
    registry = ModelVariantRegistry(repository_root)
    capabilities = collect_runtime_capabilities(profile="cpu")
    adapters = (
        (Sam2LeafSegmentationAdapter(execution_strategy="cpu_bounded"), "sam2_instance_segmentation",
         "sam2.1_automatic_mask_generator"),
        (MobileSamLeafSegmentationAdapter(), "mobile_sam_instance_segmentation",
         "mobilesam.point_grid_predictor"),
    )

    for adapter, model_key, expected_method in adapters:
        selection = registry.select(model_key, profile="cpu", capabilities=capabilities)
        adapter.artifact_path = selection["path"]
        adapter.artifact_version = selection["variant_id"]
        try:
            assert adapter.load("cpu"), f"{adapter.name} failed: {adapter.last_error}"
            candidates = adapter.predict(image)
            assert candidates
            assert all(candidate["method"] == expected_method for candidate in candidates)
            assert all(
                np.asarray(candidate["segmentation"]).shape == image.shape[:2]
                for candidate in candidates
            )
        finally:
            adapter.unload()


def test_real_artifact_pipeline_cpu():
    image_path = Path(__file__).resolve().parents[3] / "IMAGE_APP.jpg"
    assert image_path.is_file(), "real artifact smoke fixture IMAGE_APP.jpg is missing"
    service = PlantAnalysisService(device="cpu")
    result = service.analyze_bytes(image_path.read_bytes())
    assert result.status in {"completed", "partial"}
    assert result.leaves
    onnxruntime_supported = (
        service._runtime_capabilities is not None
        and service._runtime_capabilities.inference_backends.get("onnxruntime") is True
        and service._runtime_capabilities.package_version_compatibility.get("onnxruntime") is True
    )
    assert result.model_versions["dinov2_vitb14"] == "original-pytorch-fp32"
    assert result.model_versions["dinov2_vits14"] == (
        "v1-onnx-int8" if onnxruntime_supported else "v1-pytorch-fp32"
    )
    assert result.model_versions["segformer_b0_plantseg"] == (
        "onnx-int8" if onnxruntime_supported else "original-transformers-fp32"
    )
    assert all(leaf.ood is not None for leaf in result.leaves)
