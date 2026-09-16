"""
Disease Classification Service Interface
Defines the contract for disease classification services.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np
from ..schemas.plant_analysis import LeafResult


class DiseaseClassificationService(BaseService):
    """
    Interface for disease classification services.
    Responsible for classifying the disease of each leaf segment.
    """

    @abstractmethod
    def classify_disease(self, leaf_image: np.ndarray) -> Dict[str, Any]:
        """
        Classify the disease of a leaf image.

        Args:
            leaf_image: Cropped RGB image of a leaf as numpy array (H, W, 3)

        Returns:
            Dictionary with:
                - disease_class: String identifier of the disease (e.g., "healthy", "leaf_spot")
                - confidence: Confidence score for the prediction (0-1)
                - all_probabilities: Optional dictionary of all class probabilities
        """
        pass