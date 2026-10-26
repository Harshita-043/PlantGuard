"""Real artifact smoke test; deliberately blocked unless explicitly enabled in an ML environment."""

import os
from pathlib import Path

import pytest

from app.ml.service import PlantAnalysisService


pytestmark = pytest.mark.skipif(
    os.getenv("PLANTGUARD_RUN_REAL_MODEL_TESTS") != "1",
    reason="BLOCKED: real SAM2/DINO/SegFormer smoke requires compatible ML runtime and verified SAM config; opt in on a prepared host",
)


def test_real_artifact_pipeline_cpu():
    image_path = Path(__file__).resolve().parents[3] / "plant.jpg"
    assert image_path.is_file(), "real artifact smoke fixture plant.jpg is missing"
    result = PlantAnalysisService(device="cpu").analyze_bytes(image_path.read_bytes())
    assert result.status in {"completed", "partial"}
    assert result.leaves
