"""
Mock Leaf Segmentation Service
"""
import logging
import numpy as np
from app.services.interfaces.leaf_segmentation import LeafSegmentationService

logger = logging.getLogger(__name__)


class MockLeafSegmentationService(LeafSegmentationService):
    """
    Mock implementation of LeafSegmentationService.
    Returns a fixed set of leaf detections for testing.
    """

    def __init__(self):
        logger.info("Initializing MOCK LeafSegmentationService")
        self._ready = True

    def initialize(self) -> None:
        """Initialize the mock service."""
        logger.info("MockLeafSegmentationService initialized")
        self._ready = True

    def is_ready(self) -> bool:
        """Check if the service is ready."""
        return self._ready

    def get_service_name(self) -> str:
        """Get the service name."""
        return "MockLeafSegmentationService"

    def segment_leaves(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Return mock leaf detections.

        Args:
            image: Input RGB image as numpy array (H, W, 3)

        Returns:
            List of mock leaf detections with fixed bounding boxes.
        """
        logger.debug("Using MOCK LeafSegmentationService")
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