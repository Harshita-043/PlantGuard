"""Classifier attention rollout contracts without loading any model checkpoint."""

from types import SimpleNamespace

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from app.ml.adapters.disease_classifier import DinoDiseaseClassifierAdapter
from app.ml.interfaces.adapter import ModelLoadingStatus


class _AttentionStub:
    def __init__(self, *, token_count=257, depth=2):
        self.backbone = SimpleNamespace(
            blocks=[SimpleNamespace(attn=SimpleNamespace(num_heads=2)) for _ in range(depth)],
            patch_size=14,
        )
        self.token_count = token_count
        self.depth = depth

    def __call__(self, _image, *, return_all_attentions, return_features):
        assert return_all_attentions
        assert return_features
        attentions = [
            torch.full((1, 2, self.token_count, self.token_count), 1 / self.token_count)
            for _ in range(self.depth)
        ]
        return (
            torch.zeros((1, 38)),
            attentions,
            torch.ones((1, 768)),
        )


def _adapter(model):
    adapter = DinoDiseaseClassifierAdapter()
    adapter._model = model
    adapter.active_device = "cpu"
    adapter.loading_status = ModelLoadingStatus.READY
    return adapter


def test_rollout_uses_every_architecture_block_and_returns_aligned_heatmap():
    adapter = _adapter(_AttentionStub(depth=2))

    probabilities, attention, features = adapter.predict_with_attention(
        np.zeros((1, 3, 224, 224), dtype=np.float32),
        return_features=True,
    )

    assert probabilities.shape == (1, 38)
    assert attention.shape == (224, 224)
    assert np.isfinite(attention).all()
    assert attention.min() == 0
    assert attention.max() > 0
    assert features.shape == (768,)


def test_rollout_rejects_attention_shape_that_does_not_match_patch_grid():
    adapter = _adapter(_AttentionStub(token_count=256))

    with pytest.raises(ValueError, match="invalid attention tensors"):
        adapter.predict_with_attention(np.zeros((1, 3, 224, 224), dtype=np.float32))


def test_rollout_rejects_non_finite_model_input():
    adapter = _adapter(_AttentionStub())

    with pytest.raises(ValueError, match="finite float32"):
        adapter.predict_with_attention(np.full((1, 3, 224, 224), np.nan, dtype=np.float32))
