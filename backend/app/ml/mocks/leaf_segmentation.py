"""
Mock Leaf Segmentation Model
Returns fixed mock leaf detections for development and testing.
"""
import logging
import numpy as np
from app.ml.interfaces.leaf_segmentation import LeafSegmentationModel

logger = logging.getLogger(__name__)


class MockLeafSegmentationModel(LeafSegmentationModel):
    """
    Mock implementation of LeafSegmentationModel.
    Returns a fixed set of leaf detections for testing.
    """

    def __init__(self):
        logger.info("Initializing MOCK LeafSegmentationModel")

    def segment_leaves(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Return mock leaf detections.

        Args:
            image: Input RGB image as numpy array (H, W, 3)

        Returns:
            List of mock leaf detections with fixed bounding boxes.
        """
        logger.debug("Using MOCK LeafSegmentationModel")
        h, w = image.shape[:2]

        # Return 3 mock leaves with fixed positions (normalized coordinates)
        return [
            {
                "bbox": [0.2, 0.3, 0.4, 0.5],  # [x_min, y_min, width, height]
                "mask": None,  # In a real implementation, this would be a numpy array
                "confidence": 0.95
            },
            {
                "bbox": [0.5, 0.2, 0.3, 0.4],
                "mask": None,
                "confidence": 0.90
            },
            {
                "bbox": [0.1, 0.6, 0.35, 0.3],
                "mask": None,
                "confidence": 0.88
            }
        ]