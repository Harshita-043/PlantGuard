"""
Plant Analysis Service Interface
Defines the contract for the plant analysis service that orchestrates the pipeline.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from .base import BaseService
import numpy as np
from ...schemas.plant_analysis import PlantAnalysisResponse


class PlantAnalysisService(BaseService):
    """
    Interface for the plant analysis service.
    Responsible for orchestrating the entire ML pipeline for plant health analysis.
    """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass
