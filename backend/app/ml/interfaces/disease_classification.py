"""
Disease Classification Model Interface
Defines the contract for disease classification models.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import numpy as np


class DiseaseClassificationModel(ABC):
    """
    Abstract base class for disease classification models.
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