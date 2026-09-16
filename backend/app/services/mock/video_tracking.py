"""
Mock Video Tracking Service
"""
import logging
import numpy as np
from app.services.interfaces.video_tracking import VideoTrackingService

logger = logging.getLogger(__name__)


class MockVideoTrackingService(VideoTrackingService):
    """
    Mock implementation of VideoTrackingService.
    Returns fixed leaf tracking results for testing.
    """

    def __init__(self):
        logger.info("Initializing MOCK VideoTrackingService")
        self._ready = True

    def initialize(self) -> None:
        """Initialize the mock service."""
        logger.info("MockVideoTrackingService initialized")
        self._ready = True

    def is_ready(self) -> bool:
        """Check if the service is ready."""
        return self._ready

    def get_service_name(self) -> str:
        """Get the service name."""
        return "MockVideoTrackingService"

    def track_leaves(self, prev_leaves: List[Dict[str, Any]], current_frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Track leaves from previous frame to current frame.

        Args:
            prev_leaves: List of leaf detections from previous frame
            current_frame: Current video frame as numpy array (H, W, 3)

        Returns:
            List of tracked leaf detections in current frame.
        """
        logger.debug("Using MOCK VideoTrackingService")
        # In mock, just return the previous leaves with slight random drift
        tracked_leaves = []
        for i, leaf in enumerate(prev_leaves):
            # Apply small random drift to bounding box
            bbox = leaf["bbox"].copy()
            # Add small random offset (-0.01 to 0.01) to each coordinate
            drift = np.random.uniform(-0.01, 0.01, 4)
            bbox = [max(0, min(1, coord + d)) for coord, d in zip(bbox, drift)]
            # Ensure width and height remain positive
            bbox[2] = max(0.01, bbox[2])
            bbox[3] = max(0.01, bbox[3])

            tracked_leaves.append({
                "bbox": bbox,
                "mask": leaf.get("mask"),  # Keep same mask (not updated in mock)
                "confidence": leaf.get("confidence", 0.9),
                "leaf_id": leaf.get("leaf_id", i)  # Maintain leaf ID across frames
            })
        return tracked_leaves