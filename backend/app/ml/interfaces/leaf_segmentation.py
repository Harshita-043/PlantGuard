"""
Leaf Segmentation Model Interface
Defines the contract for leaf segmentation models.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import numpy as np


class LeafSegmentationModel(ABC):
    """
    Abstract base class for leaf segmentation models.
    Responsible for segmenting individual leaves from a whole plant image.
    """

    @abstractmethod
    def segment_leaves(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Segment leaves from the input plant image.

        Args:
            image: Input RGB image as numpy array (H, W, 3)

        Returns:
            List of dictionaries, each representing a detected leaf with:
                - bbox: Bounding box [x_min, y_min, width, height] (normalized 0-1)
                - mask: Optional segmentation mask as numpy array (H, W) with boolean values
                - confidence: Detection confidence score (0-1)
        """
        pass