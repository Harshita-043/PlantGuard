"""
Disease Segmentation Model Interface
Defines the contract for disease segmentation models.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np


class DiseaseSegmentationModel(ABC):
    """
    Abstract base class for disease segmentation models.
    Responsible for segmenting diseased regions within a leaf image.
    """

    @abstractmethod
    def segment_disease(self, leaf_image: np.ndarray) -> Dict[str, Any]:
        """
        Segment diseased regions in the leaf image.

        Args:
            leaf_image: Cropped RGB image of a leaf as numpy array (H, W, 3)

        Returns:
            Dictionary with:
                - mask: Segmentation mask as numpy array (H, W) with boolean values (True for diseased)
                - diseased_area_ratio: Ratio of diseased pixels to total leaf area (0-1)
                - bounding_box: Optional bounding box of diseased region [x_min, y_min, width, height] (normalized)
        """
        pass