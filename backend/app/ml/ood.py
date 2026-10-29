"""
Out-of-Distribution (OOD) Detection Module.

Prevents silent false-positive classifications on non-leaf images, background noise,
or unseen disease types using statistical uncertainty estimation.
"""

import logging
import os
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional, Tuple, TypedDict, Union
import numpy as np

from app.schemas.inference import OODResult

logger = logging.getLogger(__name__)


class OODStatistics(TypedDict):
    means: np.ndarray
    inv_cov: np.ndarray
    threshold: float
    class_labels: np.ndarray


class OODDetector:
    """
    Statistical Out-of-Distribution (OOD) Detector and Uncertainty Estimator.

    Supports:
    - Calibrated class-conditional Mahalanobis distance from DINOv2 feature embeddings.
    - Normalized Shannon Entropy thresholding: high uncertainty across classes -> diffuse prediction.
    - Maximum Softmax Probability (MSP): low top-1 confidence.
    - Energy-score thresholding: high unnormalized free energy.
    """

    DEFAULT_ENTROPY_THRESHOLD = float(os.getenv("PLANTGUARD_UNCERTAINTY_THRESHOLD", "0.65"))
    DEFAULT_MIN_CONFIDENCE = float(os.getenv("PLANTGUARD_MIN_CLASSIFICATION_CONFIDENCE", "0.40"))

    _mahalanobis_cache: Dict[tuple[str, int, int], OODStatistics] = {}
    _cache_lock = RLock()

    def __init__(
        self,
        entropy_threshold: float = DEFAULT_ENTROPY_THRESHOLD,
        min_confidence_threshold: float = DEFAULT_MIN_CONFIDENCE,
        ood_artifact_path: Optional[Path] = None,
    ):
        self.entropy_threshold = entropy_threshold
        self.min_confidence_threshold = min_confidence_threshold
        self.ood_artifact_path = ood_artifact_path or self._resolve_ood_path()
        if not 0.0 <= entropy_threshold <= 1.0 or not 0.0 <= min_confidence_threshold <= 1.0:
            raise ValueError("Provisional reliability thresholds must be between 0 and 1")

    @classmethod
    def _resolve_ood_path(cls) -> Path:
        candidates = [
            Path("artifacts/dino_disease/ood.npz"),
            Path("../artifacts/dino_disease/ood.npz"),
            Path(__file__).resolve().parents[3] / "artifacts" / "dino_disease" / "ood.npz",
        ]
        for c in candidates:
            if c.exists():
                return c.resolve()
        return Path("artifacts/dino_disease/ood.npz")

    def _load_mahalanobis_data(self) -> Optional[OODStatistics]:
        try:
            stat = self.ood_artifact_path.stat()
        except OSError:
            return None
        cache_key = (str(self.ood_artifact_path.resolve()), stat.st_mtime_ns, stat.st_size)
        with self._cache_lock:
            cached = self._mahalanobis_cache.get(cache_key)
            if cached is not None:
                return cached

        try:
            with np.load(str(self.ood_artifact_path), allow_pickle=False) as data:
                means = np.asarray(data["means"], dtype=np.float32)
                inv_cov = np.asarray(data["inv_cov"], dtype=np.float32)
                class_labels = np.asarray(data["class_labels"])
                threshold_values = np.asarray(data["threshold"])
            if (
                means.shape != (38, 768)
                or inv_cov.shape != (768, 768)
                or class_labels.shape != (38,)
                or not np.issubdtype(class_labels.dtype, np.integer)
                or not np.array_equal(class_labels, np.arange(38))
                or threshold_values.size != 1
                or not np.isfinite(means).all()
                or not np.isfinite(inv_cov).all()
                or not np.allclose(inv_cov, inv_cov.T, rtol=1e-4, atol=1e-5)
            ):
                raise ValueError("OOD statistics do not match the DINOv2 ViT-B/14 contract")
            threshold = float(threshold_values.reshape(()))
            if not np.isfinite(threshold) or threshold <= 0:
                raise ValueError("OOD threshold must be positive and finite")

            validated: OODStatistics = {
                "means": means,
                "inv_cov": inv_cov,
                "threshold": threshold,
                "class_labels": class_labels,
            }
            means.setflags(write=False)
            inv_cov.setflags(write=False)
            class_labels.setflags(write=False)
            with self._cache_lock:
                self._mahalanobis_cache[cache_key] = validated
            return validated
        except (OSError, EOFError, KeyError, TypeError, ValueError) as exc:
            logger.warning(
                "OOD statistics could not be validated error_type=%s",
                type(exc).__name__,
            )
            return None

    def evaluate_features(
        self,
        features: np.ndarray | None,
        predicted_class: int,
        confidence: Optional[float] = None,
    ) -> OODResult:
        """
        Evaluate DINOv2 feature embedding using class-conditional Mahalanobis distance.
        """
        data = self._load_mahalanobis_data()
        if data is None:
            return OODResult(
                score=0.0,
                threshold=0.0,
                is_ood=False,
                method="ood_unavailable",
                status="ood_unavailable",
                classification_confidence=confidence,
                calibration_status="ood_unavailable",
            )

        if features is None:
            return OODResult(
                score=0.0,
                threshold=0.0,
                is_ood=False,
                method="features_unavailable",
                status="ood_unavailable",
                classification_confidence=confidence,
                calibration_status="ood_unavailable",
            )

        feat = np.asarray(features, dtype=np.float64)
        if feat.shape not in {(768,), (1, 768)} or not np.isfinite(feat).all():
            return OODResult(
                score=0.0,
                threshold=0.0,
                is_ood=False,
                method="invalid_feature_dimension",
                status="ood_unvalidated",
                classification_confidence=confidence,
                calibration_status="unvalidated",
            )
        feat = feat.reshape(768)

        means = data["means"]
        inv_cov = data["inv_cov"]
        threshold = data["threshold"]
        if not isinstance(means, np.ndarray) or not isinstance(inv_cov, np.ndarray) or not isinstance(threshold, float):
            return OODResult(
                score=0.0,
                threshold=0.0,
                is_ood=False,
                method="invalid_ood_artifact",
                status="ood_unavailable",
                classification_confidence=confidence,
                calibration_status="ood_unavailable",
            )

        if (
            isinstance(predicted_class, bool)
            or not isinstance(predicted_class, (int, np.integer))
            or predicted_class < 0
            or predicted_class >= means.shape[0]
        ):
            return OODResult(
                score=0.0,
                threshold=0.0,
                is_ood=False,
                method="class_out_of_range",
                status="ood_unvalidated",
                classification_confidence=confidence,
                calibration_status="unvalidated",
            )

        diff = feat - means[int(predicted_class)].astype(np.float64, copy=False)
        distance = float(diff @ inv_cov.astype(np.float64, copy=False) @ diff)
        if not np.isfinite(distance) or distance < -1e-6:
            return OODResult(
                score=0.0,
                threshold=0.0,
                is_ood=False,
                method="invalid_mahalanobis_distance",
                status="ood_unvalidated",
                classification_confidence=confidence,
                calibration_status="unvalidated",
            )
        distance = max(0.0, distance)
        is_ood = bool(distance > threshold)

        return OODResult(
            score=round(distance, 2),
            threshold=round(threshold, 2),
            is_ood=is_ood,
            method="class_conditional_mahalanobis",
            status="ood_unvalidated",
            classification_confidence=confidence,
            calibration_status="in_distribution_percentile_99_only",
        )

    def evaluate_probabilities(
        self,
        probabilities: Union[np.ndarray, List[float], Dict[str, float]],
    ) -> OODResult:
        """
        Evaluate class probabilities to determine whether input is out-of-distribution.

        Args:
            probabilities: Probability distribution across classes (sums to ~1.0).

        Returns:
            OODResult with decision flag, normalized score, and decision threshold.
        """
        if isinstance(probabilities, dict):
            probs = np.array(list(probabilities.values()), dtype=np.float64)
        else:
            probs = np.array(probabilities, dtype=np.float64)

        if probs.ndim != 1 or probs.size <= 1 or not np.isfinite(probs).all() or np.any(probs < 0):
            raise ValueError("Probabilities must be a finite, non-negative one-dimensional vector")
        if probs.size <= 1:
            return OODResult(
                score=0.0,
                threshold=self.entropy_threshold,
                is_ood=False,
                method="insufficient_classes_passthrough",
            )

        # Normalize probabilities in case of float precision drift
        prob_sum = np.sum(probs)
        if prob_sum > 0 and np.isfinite(prob_sum):
            probs = probs / prob_sum
        else:
            # All zeros -> completely anomalous
            return OODResult(
                score=1.0,
                threshold=self.entropy_threshold,
                is_ood=True,
                method="zero_energy_anomaly",
                classification_confidence=0.0,
                calibration_status="incomplete",
            )

        # 1. Calculate Shannon Entropy H(p)
        eps = 1e-12
        entropy = -np.sum(probs * np.log(probs + eps))
        max_entropy = np.log(float(probs.size))
        normalized_entropy = float(entropy / max(eps, max_entropy))

        # 2. Maximum Softmax Probability (MSP)
        top1_prob = float(np.max(probs))

        # Decision rule: either normalized entropy is too high OR top-1 confidence is below threshold
        is_ood = (normalized_entropy > self.entropy_threshold) or (top1_prob < self.min_confidence_threshold)

        return OODResult(
            score=round(normalized_entropy, 4),
            threshold=self.entropy_threshold,
            is_ood=is_ood,
            method="provisional_entropy_and_msp",
            status="ood_unvalidated",
            classification_confidence=round(top1_prob, 4),
            calibration_status="incomplete",
        )

    @classmethod
    def evaluate_energy(
        cls,
        logits: np.ndarray,
        temperature: float = 1.0,
        energy_threshold: float = -5.0,
    ) -> OODResult:
        """
        Energy-based OOD scoring: E(x) = -T * log(sum(exp(z_i / T))).
        """
        logits = np.asarray(logits, dtype=np.float64)
        if logits.ndim != 1 or logits.size < 2 or not np.isfinite(logits).all():
            raise ValueError("Logits must be a finite one-dimensional vector with at least two classes")
        if not np.isfinite(temperature) or temperature <= 0 or not np.isfinite(energy_threshold):
            raise ValueError("Energy temperature and threshold must be finite; temperature must be positive")
        scaled = logits / temperature
        # Log-sum-exp trick for numeric stability
        max_val = np.max(scaled)
        lse = max_val + np.log(np.sum(np.exp(scaled - max_val)))
        energy = -temperature * float(lse)

        is_ood = energy > energy_threshold
        return OODResult(
            score=round(energy, 4),
            threshold=energy_threshold,
            is_ood=is_ood,
            method="energy_score",
            status="ood_unvalidated",
            calibration_status="incomplete",
        )
