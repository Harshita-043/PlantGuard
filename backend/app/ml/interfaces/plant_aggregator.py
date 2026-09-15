"""
Plant Aggregator Interface
Defines the contract for plant-level result aggregation.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class PlantAggregator(ABC):
    """
    Abstract base class for plant aggregators.
    Responsible for combining leaf-level results into plant-level assessment.
    """

    @abstractmethod
    def aggregate_leaf_results(
        self,
        leaf_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate leaf-level results into plant-level assessment.

        Args:
            leaf_results: List of leaf result dictionaries, each containing:
                - disease_class: String identifier of the disease
                - confidence: Confidence score for the prediction
                - severity_score: Severity score for the leaf (0-1)
                - bounding_box: Leaf bounding box [x_min, y_min, width, height]
                - Other leaf-specific data from previous pipeline stages

        Returns:
            Dictionary with plant-level assessment:
                - overall_health_score: Overall plant health score (0-100)
                - disease_summary: Summary of diseases found
                - recommendations: List of care recommendations
                - risk_assessment: Overall risk level ("low", "medium", "high")
                - Additional plant-level metrics (optional)
        """
        pass