"""
Mock Leaf Tracker
Returns fixed mock leaf tracking for development and testing.
"""
import logging
import numpy as np
from app.ml.interfaces.leaf_tracker import LeafTracker

logger = logging.getLogger(__name__)


class MockLeafTracker(LeafTracker):
    """
    Mock implementation of LeafTracker.
    Returns fixed leaf tracking results for testing.
    """

    def __init__(self):
        logger.info("Initializing MOCK LeafTracker")

    def track_leaves(self, prev_leaves: List[Dict[str, Any]], current_frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Track leaves from previous frame to current frame.

        Args:
            prev_leaves: List of leaf detections from previous frame
            current_frame: Current video frame as numpy array (H, W, 3)

        Returns:
            List of tracked leaf detections in current frame.
        """
        logger.debug("Using MOCK LeafTracker")
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