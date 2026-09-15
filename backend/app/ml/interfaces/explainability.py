"""
Explainability Model Interface
Defines the contract for explainability models (Grad-CAM).
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np


class ExplainabilityModel(ABC):
    """
    Abstract base class for explainability models.
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