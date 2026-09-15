"""
Mock Explainability Model
Returns fixed mock explainability visualizations for development and testing.
"""
import logging
import numpy as np
from app.ml.interfaces.explainability import ExplainabilityModel

logger = logging.getLogger(__name__)


class MockExplainabilityModel(ExplainabilityModel):
    """
    Mock implementation of ExplainabilityModel.
    Returns fixed Grad-CAM style visualizations for testing.
    """

    def __init__(self):
        logger.info("Initializing MOCK ExplainabilityModel")

    def generate_explanation(
        self,
        leaf_image: np.ndarray,
        disease_class: str
    ) -> Dict[str, Any]:
        """
        Return mock explainability visualization.

        Args:
            leaf_image: RGB leaf image as numpy array (H, W, 3)
            disease_class: Predicted disease class for the leaf

        Returns:
            Dictionary with mock explanation results.
        """
        logger.debug("Using MOCK ExplainabilityModel")
        h, w = leaf_image.shape[:2]

        # Create a mock heatmap (bright spot in center)
        heatmap = np.zeros((h, w), dtype=np.float32)
        center_y, center_x = h // 2, w // 2
        radius_y, radius_x = h // 3, w // 3

        # Create Gaussian-like heatmap
        for y in range(h):
            for x in range(w):
                # Normalized distance from center
                dx = (x - center_x) / radius_x
                dy = (y - center_y) / radius_y
                distance = dx*dx + dy*dy
                if distance <= 1.0:
                    heatmap[y, x] = 1.0 - distance  # Linear falloff

        # Normalize to 0-1 range
        if np.max(heatmap) > 0:
            heatmap = heatmap / np.max(heatmap)

        # Create overlay (simplified - just return heatmap for now)
        overlay = np.stack([heatmap, heatmap*0.5, heatmap*0.5], axis=-1)  # Reddish overlay

        return {
            "heatmap": heatmap,
            "overlay": overlay,
            "activation_map": heatmap  # In mock, same as heatmap
        }