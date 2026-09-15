"""
Mock Severity Calculator
Returns fixed mock severity calculations for development and testing.
"""
import logging
import numpy as np
from app.ml.interfaces.severity_calculator import SeverityCalculator

logger = logging.getLogger(__name__)


class MockSeverityCalculator(SeverityCalculator):
    """
    Mock implementation of SeverityCalculator.
    Returns fixed severity calculations for testing.
    """

    def __init__(self):
        logger.info("Initializing MOCK SeverityCalculator")

    def calculate_severity(
        self,
        leaf_image: np.ndarray,
        disease_mask: np.ndarray
    ) -> Dict[str, Any]:
        """
        Return mock severity calculation.

        Args:
            leaf_image: Original RGB leaf image as numpy array (H, W, 3)
            disease_mask: Binary mask of diseased regions as numpy array (H, W)

        Returns:
            Dictionary with mock severity results.
        """
        logger.debug("Using MOCK SeverityCalculator")
        h, w = leaf_image.shape[:2]

        # Calculate diseased area ratio from mask
        if disease_mask is not None and disease_mask.size > 0:
            diseased_area_ratio = np.sum(disease_mask) / (h * w)
        else:
            diseased_area_ratio = 0.0

        # Determine severity level based on diseased area ratio
        if diseased_area_ratio < 0.1:
            severity_level = "low"
            severity_score = diseased_area_ratio  # 0-0.1
        elif diseased_area_ratio < 0.3:
            severity_level = "medium"
            severity_score = 0.1 + (diseased_area_ratio - 0.1) * 0.5  # 0.1-0.2
        else:
            severity_level = "high"
            severity_score = 0.2 + (diseased_area_ratio - 0.3) * 0.8 / 0.7  # 0.2-1.0

        # Clamp severity score to 0-1 range
        severity_score = max(0.0, min(1.0, severity_score))

        return {
            "severity_score": float(severity_score),
            "affected_percentage": float(diseased_area_ratio * 100),
            "severity_level": severity_level,
            "metrics": {
                "diseased_pixels": int(np.sum(disease_mask)) if disease_mask is not None else 0,
                "total_pixels": int(h * w),
                "healthy_pixels": int(h * w - np.sum(disease_mask)) if disease_mask is not None else int(h * w)
            }
        }