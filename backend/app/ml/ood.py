"""
Out-of-Distribution (OOD) Detection Module.

Prevents silent false-positive classifications on non-leaf images, background noise,
or unseen disease types using statistical uncertainty estimation.
"""

import os
from typing import Dict, List, Union
import numpy as np

from app.schemas.inference import OODResult


class OODDetector:
    """
    Provisional uncertainty summary. It is not a calibrated OOD detector.

    Supports:
    - Normalized Shannon Entropy thresholding: high uncertainty across classes -> OOD.
    - Maximum Softmax Probability (MSP): low top-1 confidence -> OOD.
    - Energy-score thresholding: high unnormalized free energy -> OOD.
    """

    DEFAULT_ENTROPY_THRESHOLD = float(os.getenv("PLANTGUARD_UNCERTAINTY_THRESHOLD", "0.65"))
    DEFAULT_MIN_CONFIDENCE = float(os.getenv("PLANTGUARD_MIN_CLASSIFICATION_CONFIDENCE", "0.40"))

    def __init__(
        self,
        entropy_threshold: float = DEFAULT_ENTROPY_THRESHOLD,
        min_confidence_threshold: float = DEFAULT_MIN_CONFIDENCE,
    ):
        self.entropy_threshold = entropy_threshold
        self.min_confidence_threshold = min_confidence_threshold
        if not 0.0 <= entropy_threshold <= 1.0 or not 0.0 <= min_confidence_threshold <= 1.0:
            raise ValueError("Provisional reliability thresholds must be between 0 and 1")

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
            calibration_status="incomplete",
        )
