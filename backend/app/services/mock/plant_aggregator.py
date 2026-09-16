"""
Mock Plant Aggregator Service
"""
import logging
from typing import List
from app.services.interfaces.plant_aggregator import PlantAggregatorService
from app.schemas.plant_analysis import LeafResult, PlantHealthSummary, SeverityLevel, HealthStatus

logger = logging.getLogger(__name__)


class MockPlantAggregatorService(PlantAggregatorService):
    """
    Mock implementation of PlantAggregatorService.
    Returns fixed plant-level aggregation for testing.
    """

    def __init__(self):
        logger.info("Initializing MOCK PlantAggregatorService")
        self._ready = True

    def initialize(self) -> None:
        """Initialize the mock service."""
        logger.info("MockPlantAggregatorService initialized")
        self._ready = True

    def is_ready(self) -> bool:
        """Check if the service is ready."""
        return self._ready

    def get_service_name(self) -> str:
        """Get the service name."""
        return "MockPlantAggregatorService"

    def aggregate_leaf_results(
        self,
        leaf_results: List[LeafResult]
    ) -> PlantHealthSummary:
        """
        Aggregate leaf-level results into plant-level assessment.

        Args:
            leaf_results: List of leaf result objects

        Returns:
            PlantHealthSummary: Plant-level assessment
        """
        logger.debug("Using MOCK PlantAggregatorService")

        if not leaf_results:
            return PlantHealthSummary(
                overall_health_score=100.0,
                health_status=HealthStatus.EXCELLENT,
                healthy_leaf_count=0,
                total_leaf_count=0,
                disease_summary={},
                risk_assessment="low",
                recommendations=["No leaves detected in image"]
            )

        # Count diseases and calculate average severity
        disease_counts = {}
        total_severity = 0.0
        healthy_count = 0

        for leaf in leaf_results:
            disease = leaf.disease_class
            disease_counts[disease] = disease_counts.get(disease, 0) + 1

            if disease == "healthy":
                healthy_count += 1

            # Accumulate severity
            total_severity += leaf.severity_score

        # Calculate overall health score (inverse of average severity)
        total_leaves = len(leaf_results)
        avg_severity = total_severity / total_leaves if total_leaves > 0 else 0.0
        overall_health_score = max(0.0, min(100.0, 100.0 - (avg_severity * 100.0)))

        # Determine health status
        if overall_health_score >= 90:
            health_status = HealthStatus.EXCELLENT
        elif overall_health_score >= 75:
            health_status = HealthStatus.GOOD
        elif overall_health_score >= 60:
            health_status = HealthStatus.FAIR
        elif overall_health_score >= 40:
            health_status = HealthStatus.POOR
        else:
            health_status = HealthStatus.CRITICAL

        # Determine risk assessment
        if overall_health_score >= 80:
            risk_assessment = "low"
        elif overall_health_score >= 60:
            risk_assessment = "medium"
        else:
            risk_assessment = "high"

        # Generate mock recommendations
        recommendations = []
        if healthy_count == total_leaves:
            recommendations = [
                "Plant appears healthy! Continue regular care.",
                "Monitor for any changes in leaf appearance.",
                "Maintain current watering and lighting schedule."
            ]
        else:
            recommendations = [
                "Some leaves show signs of stress or disease.",
                "Consider isolating affected plants if possible.",
                "Review watering habits - over/under watering can cause issues.",
                "Check for pests on undersides of leaves.",
                "Ensure adequate air circulation around plants."
            ]

        # Add specific recommendations based on detected diseases
        if "leaf_spot" in disease_counts:
            recommendations.append("Leaf spot detected: Remove affected leaves and avoid wetting foliage.")
        if "powdery_mildew" in disease_counts:
            recommendations.append("Powdery mildew detected: Increase air circulation and consider fungicidal treatment.")
        if "rust" in disease_counts:
            recommendations.append("Rust detected: Remove infected leaves and apply appropriate treatment.")

        return PlantHealthSummary(
            overall_health_score=overall_health_score,
            health_status=health_status,
            healthy_leaf_count=healthy_count,
            total_leaf_count=total_leaves,
            disease_summary=disease_counts,
            risk_assessment=risk_assessment,
            recommendations=recommendations
        )