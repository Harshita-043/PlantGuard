"""
Leaf Tracker Interface
Defines the contract for leaf tracking models (for video analysis).
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import numpy as np


class LeafTracker(ABC):
    """
    Abstract base class for leaf trackers.
    Responsible for tracking leaves across video frames.
    """

    @abstractmethod
    def track_leaves(
        self,
        prev_leaves: List[Dict[str, Any]],
        current_frame: np.ndarray
    ) -> List[Dict[str, Any]]:
        """
        Track leaves from previous frame to current frame.

        Args:
            prev_leaves: List of leaf detections from previous frame. Each detection is a dict with:
                - bbox: Bounding box [x_min, y_min, width, height] (normalized 0-1)
                - mask: Optional segmentation mask
                - confidence: Detection confidence
                - leaf_id: Unique identifier for the leaf (if available)
            current_frame: Current video frame as numpy array (H, W, 3)

        Returns:
            List of tracked leaf detections in current frame, each with:
                - bbox: Updated bounding box
                - mask: Updated or same mask
                - confidence: Tracking confidence
                - leaf_id: Identifier matching the leaf from previous frame
        """
        pass