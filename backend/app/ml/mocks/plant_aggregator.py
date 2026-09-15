"""
Mock Plant Aggregator
Returns fixed mock plant-level aggregation for development and testing.
"""
import logging
from typing import List, Dict, Any
from app.ml.interfaces.plant_aggregator import PlantAggregator

logger = logging.getLogger(__name__)


class MockPlantAggregator(PlantAggregator):
    """
    Mock implementation of PlantAggregator.
    Returns fixed plant-level aggregation for testing.
    """

    def __init__(self):
        logger.info("Initializing MOCK PlantAggregator")

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

        Returns:
            Dictionary with plant-level assessment:
                - overall_health_score: Overall plant health score (0-100)
                - disease_summary: Summary of diseases found
                - recommendations: List of care recommendations
                - risk_assessment: Overall risk level
        """
        logger.debug("Using MOCK PlantAggregator")

        if not leaf_results:
            return {
                "overall_health_score": 100.0,
                "disease_summary": {"healthy": 0, "total": 0},
                "recommendations": ["No leaves detected in image"],
                "risk_assessment": "unknown"
            }

        # Count diseases
        disease_counts = {}
        total_severity = 0.0
        healthy_count = 0

        for leaf in leaf_results:
            disease = leaf.get("disease_class", "unknown")
            disease_counts[disease] = disease_counts.get(disease, 0) + 1

            if disease == "healthy":
                healthy_count += 1

            # Accumulate severity
            total_severity += leaf.get("severity_score", 0.0)

        # Calculate overall health score (inverse of average severity)
        avg_severity = total_severity / len(leaf_results) if leaf_results else 0.0
        overall_health_score = max(0.0, min(100.0, 100.0 - (avg_severity * 100.0)))

        # Determine risk assessment
        if overall_health_score >= 80:
            risk_assessment = "low"
        elif overall_health_score >= 60:
            risk_assessment = "medium"
        else:
            risk_assessment = "high"

        # Generate mock recommendations
        recommendations = []
        if healthy_count == len(leaf_results):
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

        return {
            "overall_health_score": float(overall_health_score),
            "disease_summary": {
                "healthy": healthy_count,
                "total_leaves": len(leaf_results),
                "disease_distribution": disease_counts
            },
            "recommendations": recommendations,
            "risk_assessment": risk_assessment
        }