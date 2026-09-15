"""
Plant Health Pipeline
Orchestrates the multi-stage ML pipeline for plant health analysis.
"""
import logging
import numpy as np
from typing import List, Dict, Any, Optional
import uuid
from PIL import Image

from app.ml.interfaces.leaf_segmentation import LeafSegmentationModel
from app.ml.interfaces.disease_classification import DiseaseClassificationModel
from app.ml.interfaces.disease_segmentation import DiseaseSegmentationModel
from app.ml.interfaces.severity_calculator import SeverityCalculator
from app.ml.interfaces.explainability import ExplainabilityModel
from app.ml.interfaces.leaf_tracker import LeafTracker
from app.ml.interfaces.plant_aggregator import PlantAggregator

logger = logging.getLogger(__name__)


class PlantHealthPipeline:
    """
    Orchestrates the complete plant health analysis pipeline:
    Whole plant image → leaf segmentation → per-leaf classification →
    disease segmentation → severity calculation → explainability →
    (for video) leaf tracking → plant-level aggregation → health report
    """

    def __init__(
        self,
        leaf_segmentation_model: LeafSegmentationModel,
        disease_classification_model: DiseaseClassificationModel,
        disease_segmentation_model: DiseaseSegmentationModel,
        severity_calculator: SeverityCalculator,
        explainability_model: ExplainabilityModel,
        leaf_tracker: Optional[LeafTracker] = None,
        plant_aggregator: PlantAggregator = None
    ):
        """
        Initialize the pipeline with ML models for each stage.

        Args:
            leaf_segmentation_model: Model for segmenting leaves from whole plant image
            disease_classification_model: Model for classifying disease per leaf
            disease_segmentation_model: Model for segmenting diseased regions per leaf
            severity_calculator: Model for calculating disease severity
            explainability_model: Model for generating Grad-CAM visualizations
            leaf_tracker: Optional model for tracking leaves across video frames
            plant_aggregator: Model for aggregating leaf results into plant-level assessment
        """
        self.leaf_segmentation_model = leaf_segmentation_model
        self.disease_classification_model = disease_classification_model
        self.disease_segmentation_model = disease_segmentation_model
        self.severity_calculator = severity_calculator
        self.explainability_model = explainability_model
        self.leaf_tracker = leaf_tracker
        self.plant_aggregator = plant_aggregator or MockPlantAggregator()

        logger.info("PlantHealthPipeline initialized with all ML components")

    def process_image(
        self,
        image_array: np.ndarray,
        scan_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a single plant image through the complete ML pipeline.

        Args:
            image_array: Input RGB image as numpy array (H, W, 3)
            scan_id: Optional identifier for the scan (used for logging/tracking)

        Returns:
            Dictionary containing complete pipeline results:
                - scan_id: Identifier for this scan
                - leaf_count: Number of leaves detected
                - leaf_results: List of results for each leaf
                - health_report: Plant-level aggregation results
                - processing_metadata: Information about processing steps
        """
        if scan_id is None:
            scan_id = str(uuid.uuid4())

        logger.info(f"Processing scan {scan_id} through plant health pipeline")
        logger.debug(f"Input image shape: {image_array.shape}")

        # Stage 1: Leaf Segmentation
        logger.debug("Stage 1: Leaf segmentation")
        leaf_detections = self.leaf_segmentation_model.segment_leaves(image_array)
        logger.info(f"Detected {len(leaf_detections)} leaves")

        # Convert image to PIL for cropping
        if image_array.dtype != np.uint8:
            # Normalize to 0-255 if needed
            image_array = ((image_array - image_array.min()) * (255 / (image_array.max() - image_array.min()))).astype(np.uint8)
        pil_image = Image.fromarray(image_array)

        # Process each leaf through remaining stages
        leaf_results = []
        for i, leaf_detection in enumerate(leaf_detections):
            logger.debug(f"Processing leaf {i+1}/{len(leaf_detections)}")

            # Extract leaf bounding box (normalized coordinates)
            bbox = leaf_detection["bbox"]  # [x_min, y_min, width, height] normalized 0-1
            h, w = image_array.shape[:2]

            # Convert to pixel coordinates
            x_min = int(bbox[0] * w)
            y_min = int(bbox[1] * h)
            width = int(bbox[2] * w)
            height = int(bbox[3] * h)

            # Ensure bounds are within image
            x_min = max(0, min(x_min, w-1))
            y_min = max(0, min(y_min, h-1))
            x_max = min(w, x_min + width)
            y_max = min(h, y_min + height)

            # Crop leaf image
            leaf_image = pil_image.crop((x_min, y_min, x_max, y_max))
            leaf_image_array = np.array(leaf_image)

            # Skip if leaf image is too small
            if leaf_image_array.shape[0] < 10 or leaf_image_array.shape[1] < 10:
                logger.warning(f"Leaf {i} too small after cropping, skipping")
                continue

            # Stage 2: Disease Classification
            logger.debug(f"Stage 2: Disease classification for leaf {i}")
            classification_result = self.disease_classification_model.classify_disease(leaf_image_array)

            # Stage 3: Disease Segmentation
            logger.debug(f"Stage 3: Disease segmentation for leaf {i}")
            segmentation_result = self.disease_segmentation_model.segment_disease(leaf_image_array)

            # Stage 4: Severity Calculation
            logger.debug(f"Stage 4: Severity calculation for leaf {i}")
            severity_result = self.severity_calculator.calculate_severity(
                leaf_image_array,
                segmentation_result.get("mask")
            )

            # Stage 5: Explainability (Grad-CAM)
            logger.debug(f"Stage 5: Explainability for leaf {i}")
            explainability_result = self.explainability_model.generate_explanation(
                leaf_image_array,
                classification_result["disease_class"]
            )

            # Compile leaf result
            leaf_result = {
                "leaf_index": i,
                "bounding_box": bbox,  # Keep normalized coordinates
                "disease_class": classification_result["disease_class"],
                "classification_confidence": classification_result["confidence"],
                "all_probabilities": classification_result.get("all_probabilities", {}),
                "disease_mask": segmentation_result.get("mask"),  # Binary mask
                "diseased_area_ratio": segmentation_result.get("diseased_area_ratio", 0.0),
                "disease_bounding_box": segmentation_result.get("bounding_box", [0, 0, 0, 0]),
                "severity_score": severity_result["severity_score"],
                "severity_level": severity_result["severity_level"],
                "affected_percentage": severity_result["affected_percentage"],
                "severity_metrics": severity_result.get("metrics", {}),
                "explainability_heatmap": explainability_result.get("heatmap"),
                "explainability_overlay": explainability_result.get("overlay"),
                "leaf_confidence": leaf_detection.get("confidence", 1.0)
            }

            leaf_results.append(leaf_result)

        # Stage 6: Plant-Level Aggregation
        logger.debug("Stage 6: Plant-level aggregation")
        health_report = self.plant_aggregator.aggregate_leaf_results(leaf_results)

        # Prepare final result
        result = {
            "scan_id": scan_id,
            "leaf_count": len(leaf_results),
            "leaf_results": leaf_results,
            "health_report": health_report,
            "processing_metadata": {
                "pipeline_version": "0.1.0",
                "models_used": {
                    "leaf_segmentation": self.leaf_segmentation_model.__class__.__name__,
                    "disease_classification": self.disease_classification_model.__class__.__name__,
                    "disease_segmentation": self.disease_segmentation_model.__class__.__name__,
                    "severity_calculator": self.severity_calculator.__class__.__name__,
                    "explainability": self.explainability_model.__class__.__name__,
                    "plant_aggregator": self.plant_aggregator.__class__.__name__
                }
            }
        }

        logger.info(f"Scan {scan_id} processed successfully. Found {len(leaf_results)} leaves.")
        return result

    def process_video_frame(
        self,
        frame_array: np.ndarray,
        prev_leaf_results: Optional[List[Dict[str, Any]]] = None,
        scan_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a single video frame through the pipeline (for leaf tracking).

        Args:
            frame_array: Input RGB frame as numpy array (H, W, 3)
            prev_leaf_results: Leaf results from previous frame (for tracking)
            scan_id: Optional identifier for the scan

        Returns:
            Dictionary containing pipeline results for this frame
        """
        if scan_id is None:
            scan_id = str(uuid.uuid4())

        logger.debug(f"Processing video frame for scan {scan_id}")

        # For now, process as single image (tracking to be enhanced later)
        # In a full implementation, this would use the leaf_tracker for temporal consistency
        result = self.process_image(frame_array, scan_id)

        # TODO: Implement actual leaf tracking when leaf_tracker is provided
        # For now, just return the image processing result

        return result