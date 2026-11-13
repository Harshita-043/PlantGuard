"""
Plant Analysis Service Interface.
Defines the application-level contract for orchestrating plant health image analysis.
"""
from abc import abstractmethod
from typing import Any, Dict, List, Optional
import numpy as np

from .base import BaseService
from ...schemas.inference import FullScanResult
from ...schemas.plant_analysis import PlantAnalysisResponse


class PlantAnalysisService(BaseService):
    """
    Interface for the application-level plant analysis service.
    Responsible for orchestrating the ML inference pipeline and returning
    structured analysis contracts to the application layer.
    """

    @abstractmethod
    def analyze_bytes(
        self,
        image_bytes: bytes,
        analysis_id: Optional[str] = None
    ) -> FullScanResult:
        """
        Analyze a raw image payload through the complete ML pipeline.

        Args:
            image_bytes: Raw binary image payload (JPEG, PNG, WebP)
            analysis_id: Optional identifier for tracing this analysis

        Returns:
            FullScanResult: Complete structured analysis output
        """
        pass

    @abstractmethod
    def analyze(
        self,
        image: np.ndarray,
        analysis_id: Optional[str] = None
    ) -> FullScanResult:
        """
        Analyze an in-memory RGB image array through the complete ML pipeline.

        Args:
            image: Input RGB image as numpy array (H, W, 3) with uint8 values
            analysis_id: Optional identifier for tracing this analysis

        Returns:
            FullScanResult: Complete structured analysis output
        """
        pass

    @abstractmethod
    def analyze_image(
        self,
        image: np.ndarray,
        analysis_id: Optional[str] = None
    ) -> PlantAnalysisResponse:
        """
        Legacy compatibility method for analyzing an RGB image array.

        Args:
            image: Input RGB image as numpy array (H, W, 3)
            analysis_id: Optional identifier for the analysis

        Returns:
            PlantAnalysisResponse: Legacy analysis result format
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
