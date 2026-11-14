"""Authenticated plant management endpoints."""
import logging
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.auth import get_current_user
from app.models.user import User
from app.schemas.analysis_lifecycle import AnalysisLifecycleResponse
from app.schemas.plant import PlantCreate, PlantDetailResponse, PlantResponse, PlantUpdate
from app.services.interfaces.plant_management import (
    AnalysisScanNotFoundError,
    PlantManagementService,
    PlantNotFoundError,
    ScanNotAssociatedWithPlantError,
)
from app.services.plant_management_service import get_plant_management_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=PlantResponse, status_code=status.HTTP_201_CREATED)
def create_plant(
    payload: PlantCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlantManagementService, Depends(get_plant_management_service)],
) -> PlantResponse:
    """Register a new plant belonging to the authenticated user."""
    return service.create_plant(user_id=current_user.id, payload=payload)


@router.get("", response_model=List[PlantResponse])
def list_plants(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlantManagementService, Depends(get_plant_management_service)],
) -> List[PlantResponse]:
    """List all plants owned by the authenticated user with latest analysis status."""
    return service.list_user_plants(user_id=current_user.id)


@router.get("/{plant_id}", response_model=PlantDetailResponse)
def get_plant_detail(
    plant_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlantManagementService, Depends(get_plant_management_service)],
) -> PlantDetailResponse:
    """Retrieve details, scan history, and health trend for an owned plant."""
    try:
        return service.get_plant_detail(plant_id=plant_id, user_id=current_user.id)
    except PlantNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found",
        )


@router.patch("/{plant_id}", response_model=PlantResponse)
def update_plant(
    plant_id: UUID,
    payload: PlantUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlantManagementService, Depends(get_plant_management_service)],
) -> PlantResponse:
    """Update metadata for an owned plant."""
    try:
        return service.update_plant(plant_id=plant_id, user_id=current_user.id, payload=payload)
    except PlantNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found",
        )


@router.delete("/{plant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plant(
    plant_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlantManagementService, Depends(get_plant_management_service)],
) -> None:
    """Delete an owned plant. Associated scans will remain with plant_id set to null."""
    try:
        service.delete_plant(plant_id=plant_id, user_id=current_user.id)
    except PlantNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found",
        )


@router.post("/{plant_id}/scans/{analysis_id}", response_model=AnalysisLifecycleResponse)
def associate_scan_with_plant(
    plant_id: UUID,
    analysis_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlantManagementService, Depends(get_plant_management_service)],
) -> AnalysisLifecycleResponse:
    """Link an owned analysis scan to an owned plant."""
    try:
        return service.associate_scan(
            plant_id=plant_id, analysis_id=analysis_id, user_id=current_user.id
        )
    except PlantNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plant not found")
    except AnalysisScanNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")


@router.delete("/{plant_id}/scans/{analysis_id}", response_model=AnalysisLifecycleResponse)
def disassociate_scan_from_plant(
    plant_id: UUID,
    analysis_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlantManagementService, Depends(get_plant_management_service)],
) -> AnalysisLifecycleResponse:
    """Unlink an analysis scan from a plant."""
    try:
        return service.disassociate_scan(
            plant_id=plant_id, analysis_id=analysis_id, user_id=current_user.id
        )
    except PlantNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plant not found")
    except (AnalysisScanNotFoundError, ScanNotAssociatedWithPlantError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found on this plant",
        )
