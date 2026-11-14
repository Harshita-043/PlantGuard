"""Plant Management Service Interface.

Defines the contract for managing user plant profiles and associated scan summaries.
"""
from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from app.schemas.analysis_lifecycle import AnalysisLifecycleResponse
from app.schemas.plant import PlantCreate, PlantDetailResponse, PlantResponse, PlantUpdate


class PlantServiceError(Exception):
    """Base exception for plant service operations."""
    pass


class PlantNotFoundError(PlantServiceError):
    """Raised when a plant cannot be found or is not owned by the requesting user."""
    pass


class AnalysisScanNotFoundError(PlantServiceError):
    """Raised when an analysis record cannot be found or is not owned by the requesting user."""
    pass


class ScanNotAssociatedWithPlantError(PlantServiceError):
    """Raised when attempting to disassociate a scan that is not linked to the specified plant."""
    pass


class PlantManagementService(ABC):
    """Application-facing interface for plant profile management."""

    @abstractmethod
    def create_plant(self, user_id: UUID, payload: PlantCreate) -> PlantResponse:
        """Create a new plant profile owned by the specified user."""
        pass

    @abstractmethod
    def get_plant(self, plant_id: UUID, user_id: UUID) -> PlantResponse:
        """Retrieve a plant profile owned by the specified user."""
        pass

    @abstractmethod
    def get_plant_detail(self, plant_id: UUID, user_id: UUID) -> PlantDetailResponse:
        """Retrieve detailed plant profile including scan history and health trend."""
        pass

    @abstractmethod
    def list_user_plants(self, user_id: UUID) -> List[PlantResponse]:
        """List all plant profiles belonging to the specified user, ordered newest first."""
        pass

    @abstractmethod
    def update_plant(self, plant_id: UUID, user_id: UUID, payload: PlantUpdate) -> PlantResponse:
        """Update fields on an owned plant profile."""
        pass

    @abstractmethod
    def delete_plant(self, plant_id: UUID, user_id: UUID) -> None:
        """Delete an owned plant profile, safely preserving analysis records."""
        pass

    @abstractmethod
    def associate_scan(self, plant_id: UUID, analysis_id: UUID, user_id: UUID) -> AnalysisLifecycleResponse:
        """Associate an owned analysis scan with an owned plant profile."""
        pass

    @abstractmethod
    def disassociate_scan(self, plant_id: UUID, analysis_id: UUID, user_id: UUID) -> AnalysisLifecycleResponse:
        """Disassociate an analysis scan from a plant profile."""
        pass
