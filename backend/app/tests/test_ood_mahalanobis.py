"""Numerical and artifact-contract tests for Mahalanobis OOD scoring."""
import json
import numpy as np
import pytest

from app.ml.errors import InferenceError, InferenceErrorCode, ModelCapabilityError
from app.ml.ood import OODDetector


def _write_statistics(path, *, threshold=2.0, labels=None, means=None):
    np.savez(
        path,
        means=np.zeros((38, 768), dtype=np.float32) if means is None else means,
        inv_cov=np.eye(768, dtype=np.float32),
        threshold=np.asarray(threshold, dtype=np.float32),
        class_labels=np.arange(38, dtype=np.int64) if labels is None else labels,
    )
    path.with_suffix(".json").write_text(
        json.dumps({
            "method": "class_conditional_mahalanobis",
            "feature_dimension": 768,
            "calibration_percentile": 99.0,
            "class_labels": list(range(38)),
            "threshold": threshold,
        }),
        encoding="utf-8",
    )


def test_mahalanobis_distance_matches_reference_and_threshold(tmp_path):
    artifact = tmp_path / "ood.npz"
    _write_statistics(artifact)
    detector = OODDetector(ood_artifact_path=artifact)

    inside = np.zeros(768, dtype=np.float32)
    inside[0] = 1.0
    result = detector.evaluate_features(inside, predicted_class=7, confidence=0.9)
    expected_squared_distance = (inside.astype(np.float64) ** 2).sum()

    assert result.score == expected_squared_distance
    assert result.threshold == 2.0
    assert result.is_ood is False
    assert result.method == "class_conditional_mahalanobis"
    assert result.status == "ood_unvalidated"
    assert result.calibration_status == "in_distribution_percentile_99_only"

    outside = np.zeros(768, dtype=np.float32)
    outside[0] = 2.0
    result = detector.evaluate_features(outside, predicted_class=7)
    reference = float(outside.astype(np.float64) @ np.eye(768) @ outside.astype(np.float64))
    assert result.score == round(reference, 2)
    assert result.is_ood is True

    on_boundary = np.zeros(768, dtype=np.float32)
    on_boundary[:2] = 1.0
    result = detector.evaluate_features(on_boundary, predicted_class=7)
    assert result.score == 2.0
    assert result.is_ood is False


def test_mahalanobis_uses_predicted_class_mean(tmp_path):
    artifact = tmp_path / "ood.npz"
    means = np.zeros((38, 768), dtype=np.float32)
    means[3, 0] = 2.0
    _write_statistics(artifact, threshold=0.5, means=means)
    result = OODDetector(ood_artifact_path=artifact).evaluate_features(
        np.array([2.0] + [0.0] * 767, dtype=np.float32),
        predicted_class=3,
    )

    assert result.score == 0.0
    assert result.is_ood is False


def test_invalid_features_and_artifact_are_explicitly_unavailable_or_unvalidated(tmp_path):
    artifact = tmp_path / "ood.npz"
    _write_statistics(artifact)
    detector = OODDetector(ood_artifact_path=artifact)

    with pytest.raises(InferenceError) as invalid_features:
        detector.evaluate_features(np.full(768, np.nan), predicted_class=0)
    assert invalid_features.value.code == InferenceErrorCode.INVALID_MODEL_OUTPUT

    with pytest.raises(InferenceError) as unavailable_features:
        detector.evaluate_features(None, predicted_class=0)
    assert unavailable_features.value.code == InferenceErrorCode.INVALID_MODEL_OUTPUT

    invalid_artifact = tmp_path / "bad.npz"
    _write_statistics(invalid_artifact, labels=np.arange(1, 39, dtype=np.int64))
    with pytest.raises(ModelCapabilityError) as unavailable_artifact:
        OODDetector(ood_artifact_path=invalid_artifact).evaluate_features(
            np.zeros(768, dtype=np.float32),
            predicted_class=0,
        )
    assert unavailable_artifact.value.code == InferenceErrorCode.OOD_CALIBRATION_UNAVAILABLE


def test_missing_or_corrupt_calibration_fails_closed(tmp_path):
    with pytest.raises(ModelCapabilityError) as missing:
        OODDetector(ood_artifact_path=tmp_path / "missing.npz").validate_calibration()
    assert missing.value.code == InferenceErrorCode.OOD_CALIBRATION_UNAVAILABLE

    corrupt = tmp_path / "corrupt.npz"
    corrupt.write_bytes(b"not an npz file")
    corrupt.with_suffix(".json").write_text("{}", encoding="utf-8")
    with pytest.raises(ModelCapabilityError) as invalid:
        OODDetector(ood_artifact_path=corrupt).validate_calibration()
    assert invalid.value.code == InferenceErrorCode.OOD_CALIBRATION_UNAVAILABLE


def test_incompatible_feature_shape_fails_closed(tmp_path):
    artifact = tmp_path / "ood.npz"
    _write_statistics(artifact)
    with pytest.raises(InferenceError) as exc:
        OODDetector(ood_artifact_path=artifact).evaluate_features(
            np.zeros(384, dtype=np.float32),
            predicted_class=0,
        )
    assert exc.value.code == InferenceErrorCode.INVALID_MODEL_OUTPUT
