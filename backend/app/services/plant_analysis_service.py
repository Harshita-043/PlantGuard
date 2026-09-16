"""
Plant Analysis Service - Main service that orchestrates ML services
"""
import logging
from typing import Optional
from app.services.interfaces.plant_analysis import PlantAnalysisService
from app.services.interfaces.leaf_segmentation import LeafSegmentationService
from app.services.interfaces.disease_classification import DiseaseClassificationService
from app.services.interfaces.disease_segmentation import DiseaseSegmentationService
from app.services.interfaces.severity import SeverityService
from app.services.interfaces.explainability import ExplainabilityService
from app.services.interfaces.video_tracking import VideoTrackingService
from app.services.mock import (
    MockLeafSegmentationService,
    MockDiseaseClassificationService,
    MockDiseaseSegmentationService,
    MockSeverityService,
    MockExplainabilityService,
    MockVideoTrackingService,
    MockPlantAnalysisService
)
from app.core.config import settings

logger = logging.getLogger(__name__)


def create_plant_analysis_service() -> PlantAnalysisService:
    """
    Factory function to create the appropriate plant analysis service
    based on configuration (mock or real models).

    Returns:
        PlantAnalysisService: Configured plant analysis service
    """
    if settings.ML_MODE.lower() == "mock":
        logger.info("Creating MOCK PlantAnalysisService")
        return MockPlantAnalysisService(
            leaf_segmentation_service=MockLeafSegmentationService(),
            disease_classification_service=MockDiseaseClassificationService(),
            disease_segmentation_service=MockDiseaseSegmentationService(),
            severity_service=MockSeverityService(),
            explainability_service=MockExplainabilityService(),
            video_tracking_service=MockVideoTrackingService(),
            plant_aggregator_service=MockPlantAggregatorService()
        )
    else:
        logger.info("Creating REAL PlantAnalysisService - loading actual models")
        # TODO: Implement real service creation when models are available
        # For now, fall back to mock for development
        logger.warning("REAL ML mode not implemented yet, falling back to mock")
        return MockPlantAnalysisService(
            leaf_segmentation_service=MockLeafSegmentationService(),
            disease_classification_service=MockDiseaseClassificationService(),
            disease_segmentation_service=MockDiseaseSegmentationService(),
            severity_service=MockSeverityService(),
            explainability_service=MockExplainabilityService(),
            video_tracking_service=MockVideoTrackingService(),
            plant_aggregator_service=MockPlantAggregatorService()
        )