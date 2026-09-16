"""
Plant Aggregator Service Interface
Defines the contract for plant aggregation services.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ..schemas.plant_analysis import LeafResult, PlantHealthSummary


class PlantAggregatorService(BaseService):
    """
    Interface for plant aggregator services.
    Responsible for aggregating leaf-level results into plant-level assessment.
    """

    @abstractmethod
    def aggregate_leaf_results(
        self,
        leaf_results: List[LeafResult]
    ) -> PlantHealthSummary:
        """
        Aggregate leaf-level results into plant-level assessment.

        Args:
            leaf_results: List of leaf result objects, each containing:
                - disease_class: String identifier of the disease
                - classification_confidence: Confidence score for the prediction
                - severity_score: Severity score for the leaf (0-1)
                - severity_level: Severity level (low, medium, high)
                - affected_percentage: Percentage of leaf affected (0-100)
                - bounding_box: Leaf bounding box [x_min, y_min, width, height] normalized
                - Other leaf-specific data from previous pipeline stages

        Returns:
            PlantHealthSummary: Plant-level assessment with:
                - overall_health_score: Overall plant health score (0-100)
                - health_status: Overall health status (excellent, good, fair, poor, critical)
                - healthy_leaf_count: Number of healthy leaves
                - total_leaf_count: Total number of leaves analyzed
                - disease_summary: Summary of diseases found
                - risk_assessment: Overall risk level (low, medium, high)
                - recommendations: List of care recommendations
        """
        pass