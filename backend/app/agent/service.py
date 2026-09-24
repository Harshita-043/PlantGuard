"""
Agent Service
Main service that exposes the agentic orchestrator to the backend API.
"""
import logging
from typing import Optional
import numpy as np
from datetime import datetime
from typing import Dict, Any

from ..schemas.plant_analysis import PlantAnalysisResponse
from app.services.plant_analysis_service import MLCapabilityUnavailable
from ..services.interfaces.plant_analysis import PlantAnalysisService
from .core.orchestrator import OrchestratorComponent
from .contracts.user_request import UserRequest
from .contracts.request_context import RequestContext

logger = logging.getLogger(__name__)


class AgentService:
    """
    Main agent service that exposes the agentic orchestrator to the backend API.

    This service integrates the agentic orchestrator with the existing PlantGuard AI
    backend architecture, allowing API routes to leverage the agentic capabilities
    while maintaining compatibility with existing interfaces.
    """

    def __init__(self):
        logger.info("Initializing AgentService")
        self.orchestrator = OrchestratorComponent()
        self._ready = False

    def initialize(self) -> None:
        """Initialize the agent service and its sub-components."""
        logger.info("AgentService initializing sub-components")

        self.orchestrator.initialize()
        logger.info("AgentService initialized")
        self._ready = True

    def is_ready(self) -> bool:
        """Check if the agent service is ready.

        Returns:
            bool: True if service is ready, False otherwise
        """
        return (
            self._ready and 
            self.orchestrator.is_ready()
        )

    def get_service_name(self) -> str:
        """Get the service name.

        Returns:
            str: Service name
        """
        return "AgentService"

    async def analyze_image_agentic(
        self,
        image: np.ndarray,
        user_id: str = "anonymous",
        request_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PlantAnalysisResponse:
        """
        Analyze a plant image using the agentic orchestrator with LLM-enhanced planning.

        Args:
            image: Input RGB image as numpy array (H, W, 3)
            user_id: Identifier for the user making the request
            request_id: Optional identifier for the analysis
            context: Optional contextual information

        Returns:
            PlantAnalysisResponse: Complete analysis results
        """
        raise MLCapabilityUnavailable("Plant analysis is unavailable: no ML implementation is integrated")

    # Legacy compatibility methods
    async def analyze_image(
        self,
        image: np.ndarray,
        analysis_id: Optional[str] = None
    ) -> PlantAnalysisResponse:
        """
        Legacy method for analyzing a plant image.
        Maintains backward compatibility with existing API routes.
        """
        return await self.analyze_image_agentic(
            image=image,
            request_id=analysis_id or f"legacy_{int(datetime.utcnow().timestamp())}"
        )
