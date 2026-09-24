"""
Explainability Service Interface
Defines the contract for explainability services (Grad-CAM).
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from .base import BaseService
import numpy as np
from ...schemas.plant_analysis import LeafResult


class ExplainabilityService(BaseService):
    """
    Interface for explainability services.
    Responsible for generating visual explanations for model predictions.
    """

    @abstractmethod
    def generate_explanation(
        self,
        leaf_image: np.ndarray,
        disease_class: str
    ) -> Dict[str, Any]:
        """
        Generate explainability visualization for a leaf classification.

        Args:
            leaf_image: RGB leaf image as numpy array (H, W, 3)
            disease_class: Predicted disease class for the leaf

        Returns:
            Dictionary with:
                - heatmap: Normalized heatmap as numpy array (H, W) with values 0-1
                - overlay: Optional blended visualization (original image + heatmap)
                - activation_map: Raw activation values before normalization
        """
        pass