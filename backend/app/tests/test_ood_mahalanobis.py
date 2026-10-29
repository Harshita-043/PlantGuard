"""Numerical and artifact-contract tests for Mahalanobis OOD scoring."""

import numpy as np

from app.ml.ood import OODDetector


def _write_statistics(path, *, threshold=2.0, labels=None):
    np.savez(
        path,
        means=np.zeros((38, 768), dtype=np.float32),
        inv_cov=np.eye(768, dtype=np.float32),
        threshold=np.asarray(threshold, dtype=np.float32),
        class_labels=np.arange(38, dtype=np.int64) if labels is None else labels,
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


def test_mahalanobis_uses_predicted_class_mean(tmp_path):
    artifact = tmp_path / "ood.npz"
    means = np.zeros((38, 768), dtype=np.float32)
    means[3, 0] = 2.0
    np.savez(
        artifact,
        means=means,
        inv_cov=np.eye(768, dtype=np.float32),
        threshold=np.asarray(0.5, dtype=np.float32),
        class_labels=np.arange(38, dtype=np.int64),
    )
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

    invalid_features = detector.evaluate_features(np.full(768, np.nan), predicted_class=0)
    assert invalid_features.status == "ood_unvalidated"
    assert invalid_features.is_ood is False

    unavailable_features = detector.evaluate_features(None, predicted_class=0)
    assert unavailable_features.status == "ood_unavailable"

    invalid_artifact = tmp_path / "bad.npz"
    _write_statistics(invalid_artifact, labels=np.arange(1, 39, dtype=np.int64))
    unavailable_artifact = OODDetector(ood_artifact_path=invalid_artifact).evaluate_features(
        np.zeros(768, dtype=np.float32),
        predicted_class=0,
    )
    assert unavailable_artifact.status == "ood_unavailable"
