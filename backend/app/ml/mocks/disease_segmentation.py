"""
Mock Disease Segmentation Model
Returns fixed mock disease segmentation for development and testing.
"""
import logging
import numpy as np
from app.ml.interfaces.disease_segmentation import DiseaseSegmentationModel

logger = logging.getLogger(__name__)


class MockDiseaseSegmentationModel(DiseaseSegmentationModel):
    """
    Mock implementation of DiseaseSegmentationModel.
    Returns fixed disease segmentation masks for testing.
    """

    def __init__(self):
        logger.info("Initializing MOCK DiseaseSegmentationModel")

    def segment_disease(self, leaf_image: np.ndarray) -> Dict[str, Any]:
        """
        Return mock disease segmentation.

        Args:
            leaf_image: Cropped RGB image of a leaf as numpy array (H, W, 3)

        Returns:
            Dictionary with mock segmentation results.
        """
        logger.debug("Using MOCK DiseaseSegmentationModel")
        h, w = leaf_image.shape[:2]

        # Create a simple geometric mock mask (ellipse in center)
        mask = np.zeros((h, w), dtype=bool)
        center_y, center_x = h // 2, w // 2
        radius_y, radius_x = h // 3, w // 3

        # Create elliptical mask
        for y in range(h):
            for x in range(w):
                if ((x - center_x) / radius_x) ** 2 + ((y - center_y) / radius_y) ** 2 <= 1:
                    mask[y, x] = True

        # Calculate diseased area ratio
        diseased_area_ratio = np.sum(mask) / (h * w)

        # Bounding box of the diseased region (normalized)
        if np.any(mask):
            rows = np.any(mask, axis=1)
            cols = np.any(mask, axis=0)
            y_min, y_max = np.where(rows)[0][[0, -1]]
            x_min, x_max = np.where(cols)[0][[0, -1]]
            bbox = [
                x_min / w,
                y_min / h,
                (x_max - x_min) / w,
                (y_max - y_min) / h
            ]
        else:
            bbox = [0.0, 0.0, 0.0, 0.0]

        return {
            "mask": mask,
            "diseased_area_ratio": float(diseased_area_ratio),
            "bounding_box": bbox
        }