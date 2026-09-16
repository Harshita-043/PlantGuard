"""
Severity Service Interface
Defines the contract for severity calculation services.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np
from ..schemas.plant_analysis import LeafResult


class SeverityService(BaseService):
    """
    Interface for severity calculation services.
    Responsible for calculating disease severity based on segmentation results.
    """

    @abstractmethod
    def calculate_severity(
        self,
        leaf_image: np.ndarray,
        disease_mask: np.ndarray
    ) -> Dict[str, Any]:
        """
        Calculate disease severity for a leaf based on disease segmentation.

        Args:
            leaf_image: Original RGB leaf image as numpy array (H, W, 3)
            disease_mask: Binary mask of diseased regions as numpy array (H, W)

        Returns:
            Dictionary with:
                - severity_score: Overall severity score (0-1, where 0 is healthy and 1 is severe)
                - affected_percentage: Percentage of leaf area affected (0-100)
                - severity_level: Categorical level (e.g., "low", "medium", "high")
                - metrics: Additional severity metrics (optional)
        """
        pass