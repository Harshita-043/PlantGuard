"""
Mask-based quantitative disease severity estimation.

Calculates exact pixel-level lesion coverage, connected component lesion counts,
and categorical severity levels based on semantic segmentation masks.
"""

import os
from typing import List, Optional
import numpy as np

from app.schemas.inference import SeverityLevel, SeverityResult


class SeverityEstimator:
    """
    Computes disease severity from binary segmentation masks.

    Threshold standards:
    - HEALTHY: 0.0% affected
    - LOW:      (0.0%, 15.0%] affected
    - MEDIUM:   (15.0%, 35.0%] affected
    - HIGH:     > 35.0% affected
    """

    LOW_THRESHOLD_PCT = float(os.getenv("PLANTGUARD_SEVERITY_LOW_THRESHOLD_PCT", "15"))
    MEDIUM_THRESHOLD_PCT = float(os.getenv("PLANTGUARD_SEVERITY_MEDIUM_THRESHOLD_PCT", "35"))

    @classmethod
    def estimate_severity(
        cls,
        disease_mask: np.ndarray,
        leaf_mask: Optional[np.ndarray] = None,
    ) -> SeverityResult:
        """
        Compute quantitative severity metrics.

        Args:
            disease_mask: 2D array (H, W) where non-zero/True indicates diseased tissue.
            leaf_mask: Optional 2D array (H, W) indicating the leaf boundary.
                       If omitted, total image pixels are used as denominator.

        Returns:
            SeverityResult with continuous score, categorical level, and lesion count.
        """
        if disease_mask.ndim != 2:
            raise ValueError(f"disease_mask must be 2D, received shape {disease_mask.shape}")
        if disease_mask.size == 0 or not np.isfinite(disease_mask).all():
            return cls._unavailable("Disease mask is empty or contains invalid values")
        if leaf_mask is None:
            return cls._unavailable("Selected leaf mask is required to estimate severity")
        if leaf_mask.ndim != 2 or leaf_mask.shape != disease_mask.shape:
            return cls._unavailable("Selected leaf mask dimensions do not align with the disease mask")
        if leaf_mask.size == 0 or not np.isfinite(leaf_mask).all():
            return cls._unavailable("Selected leaf mask is empty or contains invalid values")
        if (not np.isfinite(cls.LOW_THRESHOLD_PCT) or not np.isfinite(cls.MEDIUM_THRESHOLD_PCT)
                or not 0 <= cls.LOW_THRESHOLD_PCT < cls.MEDIUM_THRESHOLD_PCT <= 100):
            raise ValueError("Severity thresholds must satisfy 0 <= low < medium <= 100")

        valid_leaf = leaf_mask > 0
        leaf_pixels = int(np.count_nonzero(valid_leaf))
        if leaf_pixels == 0:
            return cls._unavailable("Selected leaf mask contains no valid leaf pixels")
        binary_disease = (disease_mask > 0) & valid_leaf
        diseased_pixels = int(np.count_nonzero(binary_disease))
        ratio = diseased_pixels / float(leaf_pixels)
        affected_percentage = round(ratio * 100.0, 2)

        # Categorical rating
        if diseased_pixels == 0 or affected_percentage == 0.0:
            level = SeverityLevel.HEALTHY
            score = 0.0
            assessment = "No pathological lesions detected on the leaf surface."
            lesion_count = 0
        elif affected_percentage <= cls.LOW_THRESHOLD_PCT:
            level = SeverityLevel.LOW
            score = float(ratio)
            assessment = f"Mild infection detected affecting {affected_percentage}% of leaf area."
            lesion_count = cls._count_lesions(binary_disease)
        elif affected_percentage <= cls.MEDIUM_THRESHOLD_PCT:
            level = SeverityLevel.MEDIUM
            score = float(ratio)
            assessment = f"Moderate infection detected affecting {affected_percentage}% of leaf area."
            lesion_count = cls._count_lesions(binary_disease)
        else:
            level = SeverityLevel.HIGH
            score = float(ratio)
            assessment = f"Severe widespread infection detected affecting {affected_percentage}% of leaf area."
            lesion_count = cls._count_lesions(binary_disease)

        return SeverityResult(
            score=round(score, 4),
            level=level,
            affected_percentage=affected_percentage,
            lesion_count=lesion_count,
            assessment=assessment,
            status="available",
            method="diseased_pixels_intersect_leaf_mask_over_valid_leaf_pixels",
            diseased_leaf_pixels=diseased_pixels,
            valid_leaf_pixels=leaf_pixels,
            thresholds_validated=False,
        )

    @staticmethod
    def _unavailable(reason: str) -> SeverityResult:
        return SeverityResult(status="unavailable", assessment=reason, method="unavailable",
                              thresholds_validated=False)

    @classmethod
    def compute_disease_bounding_box(
        cls,
        disease_mask: np.ndarray,
    ) -> Optional[List[float]]:
        """
        Compute normalized bounding box [ymin, xmin, ymax, xmax] of diseased region.
        Returns None if no diseased pixels exist.
        """
        binary = disease_mask > 0
        if not np.any(binary):
            return None

        h, w = binary.shape
        rows = np.any(binary, axis=1)
        cols = np.any(binary, axis=0)
        ymin, ymax = np.where(rows)[0][[0, -1]]
        xmin, xmax = np.where(cols)[0][[0, -1]]

        return [
            round(float(ymin) / h, 4),
            round(float(xmin) / w, 4),
            round(float(ymax + 1) / h, 4),
            round(float(xmax + 1) / w, 4),
        ]

    @staticmethod
    def _count_lesions(binary_mask: np.ndarray, min_lesion_size: int = 4) -> int:
        """
        Count distinct connected lesion components using flood-fill (4-connectivity).
        Filters out noise clusters smaller than min_lesion_size pixels.
        """
        h, w = binary_mask.shape
        visited = np.zeros((h, w), dtype=bool)
        count = 0

        # Downsample if mask is excessively large to keep latency under 5ms on CPU
        if h > 256 or w > 256:
            step_y = max(1, h // 256)
            step_x = max(1, w // 256)
            small = binary_mask[::step_y, ::step_x]
            h, w = small.shape
            visited = np.zeros((h, w), dtype=bool)
            target = small
            min_size = max(1, min_lesion_size // (step_y * step_x))
        else:
            target = binary_mask
            min_size = min_lesion_size

        for r in range(h):
            for c in range(w):
                if target[r, c] and not visited[r, c]:
                    # BFS component discovery
                    cluster_size = 0
                    queue = [(r, c)]
                    visited[r, c] = True

                    while queue:
                        cr, cc = queue.pop()
                        cluster_size += 1

                        for nr, nc in ((cr - 1, cc), (cr + 1, cc), (cr, cc - 1), (cr, cc + 1)):
                            if 0 <= nr < h and 0 <= nc < w:
                                if target[nr, nc] and not visited[nr, nc]:
                                    visited[nr, nc] = True
                                    queue.append((nr, nc))

                    if cluster_size >= min_size:
                        count += 1

        return count
