"""
Unit tests for DINOv2 Attention Rollout Explainer.
"""

import numpy as np
import pytest

torch = pytest.importorskip("torch")
cv2 = pytest.importorskip("cv2")

from app.ml.architectures.dinov2 import build_dino_disease_classifier
from app.ml.cam import AttentionRolloutExplainer


def test_attention_rollout_explainer_initialization():
    explainer = AttentionRolloutExplainer()
    assert explainer.METHOD_NAME == "dinov2_attention_rollout"
    assert explainer.device == "cpu"


def test_compute_rollout_heatmap_contract_with_mock():
    explainer = AttentionRolloutExplainer()
    # Mock model that returns synthetic attention weights
    model = build_dino_disease_classifier()
    explainer._model = model

    crop = np.random.randint(0, 255, (100, 150, 3), dtype=np.uint8)
    heatmap_16 = explainer.compute_rollout_heatmap(crop)

    assert isinstance(heatmap_16, np.ndarray)
    assert heatmap_16.shape == (16, 16)
    assert heatmap_16.dtype == np.float32
    assert np.all(np.isfinite(heatmap_16))
    assert 0.0 <= heatmap_16.min() <= heatmap_16.max() <= 1.0


def test_crop_heatmap_and_overlay_dimensions():
    explainer = AttentionRolloutExplainer()
    model = build_dino_disease_classifier()
    explainer._model = model

    crop = np.zeros((80, 120, 3), dtype=np.uint8)
    crop_heatmap = explainer.generate_crop_heatmap(crop)

    assert crop_heatmap.shape == (80, 120)
    assert crop_heatmap.dtype == np.float32
    assert 0.0 <= crop_heatmap.min() <= crop_heatmap.max() <= 1.0

    overlay = explainer.create_overlay(crop, crop_heatmap)
    assert overlay.shape == (80, 120, 3)
    assert overlay.dtype == np.uint8


def test_map_to_original_geometry():
    explainer = AttentionRolloutExplainer()
    orig = np.zeros((200, 300, 3), dtype=np.uint8)
    crop_heat = np.ones((50, 60), dtype=np.float32) * 0.8
    bbox = (20, 30, 70, 90)

    full_heat, full_overlay = explainer.map_to_original(orig, crop_heat, bbox)

    assert full_heat.shape == (200, 300)
    assert full_overlay.shape == (200, 300, 3)
    # Outside bbox should be 0
    assert full_heat[0, 0] == 0.0
    # Inside bbox should be 0.8
    assert np.isclose(full_heat[30, 40], 0.8)
