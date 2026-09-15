"""
Mock Disease Classification Model
Returns fixed mock disease classifications for development and testing.
"""
import logging
import numpy as np
from app.ml.interfaces.disease_classification import DiseaseClassificationModel

logger = logging.getLogger(__name__)


class MockDiseaseClassificationModel(DiseaseClassificationModel):
    """
    Mock implementation of DiseaseClassificationModel.
    Returns fixed disease classifications for testing.
    """

    def __init__(self):
        logger.info("Initializing MOCK DiseaseClassificationModel")
        # Define some common plant disease classes
        self.disease_classes = [
            "healthy",
            "leaf_spot",
            "powdery_mildew",
            "rust",
            "blight",
            "yellow_virus"
        ]

    def classify_disease(self, leaf_image: np.ndarray) -> Dict[str, Any]:
        """
        Return mock disease classification.

        Args:
            leaf_image: Cropped RGB image of a leaf as numpy array (H, W, 3)

        Returns:
            Dictionary with mock classification results.
        """
        logger.debug("Using MOCK DiseaseClassificationModel")

        # Return deterministic but varied results based on image properties
        # Use image hash to get consistent results for same image
        img_hash = hash(leaf_image.tobytes()) % len(self.disease_classes)
        disease_class = self.disease_classes[img_hash]

        # Vary confidence slightly
        base_confidence = 0.85
        variation = (hash(leaf_image.tobytes()) % 20) / 100.0  # 0-0.2
        confidence = min(0.95, base_confidence + variation)

        # Generate mock probabilities for all classes
        probabilities = {}
        remaining = 1.0 - confidence
        for i, cls in enumerate(self.disease_classes):
            if cls == disease_class:
                probabilities[cls] = confidence
            else:
                # Distribute remaining probability among other classes
                probabilities[cls] = remaining / (len(self.disease_classes) - 1)

        return {
            "disease_class": disease_class,
            "confidence": float(confidence),
            "all_probabilities": probabilities
        }