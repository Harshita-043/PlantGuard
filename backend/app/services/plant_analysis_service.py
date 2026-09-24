"""
Plant Analysis Service - Main service that orchestrates ML services
"""
from app.services.interfaces.plant_analysis import PlantAnalysisService


class MLCapabilityUnavailable(RuntimeError):
    """Raised when no verified ML implementation is configured."""


def create_plant_analysis_service() -> PlantAnalysisService:
    """Return a real analysis service when one is integrated.

    The repository currently has no verified ML inference implementation. Never
    substitute generated demo predictions for results from a real model.
    """
    raise MLCapabilityUnavailable("Plant analysis is unavailable: no ML implementation is integrated")
