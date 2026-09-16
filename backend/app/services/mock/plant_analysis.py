"""
Mock Plant Analysis Service
"""
import logging
import numpy as np
import uuid
from datetime import datetime
from typing import List, Optional
from app.services.interfaces.plant_analysis import PlantAnalysisService
from app.services.interfaces.leaf_segmentation import LeafSegmentationService
from app.services.interfaces.disease_classification import DiseaseClassificationService
from app.services.interfaces.disease_segmentation import DiseaseSegmentationService
from app.services.interfaces.severity import SeverityService
from app.services.interfaces.explainability import ExplainabilityService
from app.services.interfaces.video_tracking import VideoTrackingService
from app.schemas.plant_analysis import (
    PlantAnalysisRequest, PlantAnalysisResponse, LeafResult,
    PlantHealthSummary, SeverityLevel, HealthStatus
)

logger = logging.getLogger(__name__)


class MockPlantAnalysisService(PlantAnalysisService):
    """
    Mock implementation of PlantAnalysisService.
    Orchestrates mock ML services for testing.
    """

    # In-memory storage for analyses (in a real app, this would be a database)
    _analyses: List[PlantAnalysisResponse] = []
    _max_analyses = 100  # Keep only the last 100 analyses

    def __init__(
        self,
        leaf_segmentation_service: LeafSegmentationService,
        disease_classification_service: DiseaseClassificationService,
        disease_segmentation_service: DiseaseSegmentationService,
        severity_service: SeverityService,
        explainability_service: ExplainabilityService,
        video_tracking_service: Optional[VideoTrackingService] = None,
        plant_aggregator_service: Optional[PlantAggregatorService] = None
    ):
        logger.info("Initializing MOCK PlantAnalysisService")
        self.leaf_segmentation_service = leaf_segmentation_service
        self.disease_classification_service = disease_classification_service
        self.disease_segmentation_service = disease_segmentation_service
        self.severity_service = severity_service
        self.explainability_service = explainability_service
        self.video_tracking_service = video_tracking_service
        self.plant_aggregator_service = plant_aggregator_service or MockPlantAggregatorService()
        self._ready = True

    def initialize(self) -> None:
        """Initialize the mock service and all dependent services."""
        logger.info("Initializing MOCK PlantAnalysisService and dependencies")
        self.leaf_segmentation_service.initialize()
        self.disease_classification_service.initialize()
        self.disease_segmentation_service.initialize()
        self.severity_service.initialize()
        self.explainability_service.initialize()
        if self.video_tracking_service:
            self.video_tracking_service.initialize()
        self._ready = True

    def is_ready(self) -> bool:
        """Check if the service and all dependencies are ready."""
        return (
            self._ready and
            self.leaf_segmentation_service.is_ready() and
            self.disease_classification_service.is_ready() and
            self.disease_segmentation_service.is_ready() and
            self.severity_service.is_ready() and
            self.explainability_service.is_ready() and
            (not self.video_tracking_service or self.video_tracking_service.is_ready())
        )

    def get_service_name(self) -> str:
        """Get the service name."""
        return "MockPlantAnalysisService"

    def _store_analysis(self, analysis: PlantAnalysisResponse) -> None:
        """Store an analysis in memory (for mock history)."""
        self._analyses.append(analysis)
        # Keep only the last _max_analyses analyses
        if len(self._analyses) > self._max_analyses:
            self._analyses = self._analyses[-self._max_analyses:]

    def get_analyses(self, skip: int = 0, limit: int = 10) -> List[PlantAnalysisResponse]:
        """Get a list of analyses (most recent first)."""
        # Return a copy of the list in reverse order (most recent first) with pagination
        sorted_analyses = list(reversed(self._analyses))
        return sorted_analyses[skip:skip+limit]

    def get_analysis_by_id(self, analysis_id: str) -> Optional[PlantAnalysisResponse]:
        """Get an analysis by its ID."""
        for analysis in self._analyses:
            if analysis.analysis_id == analysis_id:
                return analysis
        return None

    def analyze_image(
        self,
        image: np.ndarray,
        analysis_id: Optional[str] = None
    ) -> PlantAnalysisResponse:
        """
        Analyze a single plant image through the complete ML pipeline.

        Args:
            image: Input RGB image as numpy array (H, W, 3)
            analysis_id: Optional identifier for the analysis

        Returns:
            PlantAnalysisResponse: Complete analysis results
        """
        if analysis_id is None:
            analysis_id = str(uuid.uuid4())

        start_time = datetime.now()
        logger.info(f"Starting mock plant analysis for {analysis_id}")

        # Ensure all services are ready
        if not self.is_ready():
            raise RuntimeError("One or more services are not ready")

        try:
            # Stage 1: Leaf Segmentation
            logger.debug("Stage 1: Leaf segmentation")
            leaf_detections = self.leaf_segmentation_service.segment_leaves(image)
            logger.info(f"Detected {len(leaf_detections)} leaves")

            # Convert image to proper format for cropping
            if image.dtype != np.uint8:
                # Normalize to 0-255 if needed
                image_uint8 = ((image - image.min()) * (255 / (image.max() - image.min()))).astype(np.uint8)
            else:
                image_uint8 = image.copy()

            # Process each leaf through remaining stages
            leaf_results = []
            for i, leaf_detection in enumerate(leaf_detections):
                logger.debug(f"Processing leaf {i+1}/{len(leaf_detections)}")

                # Extract leaf bounding box (normalized coordinates)
                bbox = leaf_detection["bbox"]  # [x_min, y_min, width, height] normalized 0-1
                h, w = image_uint8.shape[:2]

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

                # Skip if leaf image is too small
                if x_max <= x_min or y_max <= y_min or (x_max - x_min) < 10 or (y_max - y_min) < 10:
                    logger.warning(f"Leaf {i} too small after cropping, skipping")
                    continue

                # Crop leaf image
                leaf_image_crop = image_uint8[y_min:y_max, x_min:x_max]

                # Stage 2: Disease Classification
                logger.debug(f"Stage 2: Disease classification for leaf {i}")
                classification_result = self.disease_classification_service.classify_disease(leaf_image_crop)

                # Stage 3: Disease Segmentation
                logger.debug(f"Stage 3: Disease segmentation for leaf {i}")
                segmentation_result = self.disease_segmentation_service.segment_disease(leaf_image_crop)

                # Stage 4: Severity Calculation
                logger.debug(f"Stage 4: Severity calculation for leaf {i}")
                severity_result = self.severity_service.calculate_severity(
                    leaf_image_crop,
                    segmentation_result.get("mask")
                )

                # Stage 5: Explainability (Grad-CAM)
                logger.debug(f"Stage 5: Explainability for leaf {i}")
                explainability_result = self.explainability_service.generate_explanation(
                    leaf_image_crop,
                    classification_result["disease_class"]
                )

                # Compile leaf result
                leaf_result = LeafResult(
                    leaf_index=i,
                    bounding_box=bbox,  # Keep normalized coordinates
                    disease_class=classification_result["disease_class"],
                    classification_confidence=classification_result["confidence"],
                    all_probabilities=classification_result.get("all_probabilities"),
                    disease_mask=segmentation_result.get("mask").tolist() if segmentation_result.get("mask") is not None else None,
                    diseased_area_ratio=segmentation_result.get("diseased_area_ratio", 0.0),
                    disease_bounding_box=segmentation_result.get("bounding_box", [0.0, 0.0, 0.0, 0.0]),
                    severity_score=severity_result["severity_score"],
                    severity_level=SeverityLevel(severity_result["severity_level"]),
                    affected_percentage=severity_result["affected_percentage"],
                    leaf_confidence=leaf_detection.get("confidence"),
                    explainability_heatmap=explainability_result.get("heatmap").tolist() if explainability_result.get("heatmap") is not None else None
                )

                leaf_results.append(leaf_result)

            # Create plant health summary using the aggregator service
            plant_health_summary = self.plant_aggregator_service.aggregate_leaf_results(leaf_results)

            # Calculate processing time
            end_time = datetime.now()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.info(f"Mock plant analysis {analysis_id} completed in {processing_time_ms}ms")

            # Store the analysis for history
            analysis_to_store = PlantAnalysisResponse(
                analysis_id=analysis_id,
                timestamp=start_time,
                status="completed",
                leaf_results=leaf_results,
                plant_health_summary=plant_health_summary,
                processing_time_ms=processing_time_ms,
                ml_mode="mock"
            )
            self._store_analysis(analysis_to_store)

            return analysis_to_store

        except Exception as e:
            logger.error(f"Error in mock plant analysis {analysis_id}: {str(e)}")
            end_time = datetime.now()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

            failed_analysis = PlantAnalysisResponse(
                analysis_id=analysis_id,
                timestamp=start_time,
                status="failed",
                leaf_results=[],
                plant_health_summary=PlantHealthSummary(
                    overall_health_score=0.0,
                    health_status=HealthStatus.CRITICAL,
                    healthy_leaf_count=0,
                    total_leaf_count=0,
                    disease_summary={"error": 1},
                    risk_assessment="high",
                    recommendations=[f"Analysis failed: {str(e)}"]
                ),
                processing_time_ms=processing_time_ms,
                ml_mode="mock"
            )
            # Store the failed analysis as well? We can choose to store only successful ones.
            # For now, let's not store failed analyses to keep the history clean.
            return failed_analysis

    def analyze_video_frame(
        self,
        frame: np.ndarray,
        prev_leaf_results: Optional[List[Dict[str, Any]]] = None,
        analysis_id: Optional[str] = None
    ) -> PlantAnalysisResponse:
        """
        Analyze a single video frame through the pipeline (for leaf tracking).

        Args:
            frame: Input RGB frame as numpy array (H, W, 3)
            prev_leaf_results: Leaf results from previous frame (for tracking)
            analysis_id: Optional identifier for the analysis

        Returns:
            PlantAnalysisResponse: Analysis results for this frame
        """
        # For now, process as single image (tracking to be enhanced later)
        # In a full implementation, this would use the video_tracking_service for temporal consistency
        logger.debug("Processing video frame as single image (mock)")
        return self.analyze_image(frame, analysis_id)