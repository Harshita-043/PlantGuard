"""Authenticated plant management endpoints."""
import logging
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.plant import Plant
from app.models.user import User
from app.schemas.analysis_lifecycle import AnalysisLifecycleResponse
from app.schemas.plant import PlantCreate, PlantDetailResponse, PlantResponse, PlantUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_owned_plant(plant_id: UUID, current_user: User, db: Session) -> Plant:
    plant = db.scalar(
        select(Plant).where(Plant.id == plant_id, Plant.user_id == current_user.id)
    )
    if plant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found",
        )
    return plant


def _to_analysis_response(analysis: Analysis) -> AnalysisLifecycleResponse:
    return AnalysisLifecycleResponse(
        analysis_id=analysis.id,
        plant_id=analysis.plant_id,
        status=analysis.status,
        created_at=analysis.created_at,
        image_content_type=analysis.image_content_type,
        image_size_bytes=analysis.image_size_bytes,
        result_available=analysis.result_data is not None,
        result=analysis.result_data,
        failure=analysis.failure_data,
    )


@router.post("", response_model=PlantResponse, status_code=status.HTTP_201_CREATED)
def create_plant(
    payload: PlantCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PlantResponse:
    """Register a new plant belonging to the authenticated user."""
    plant = Plant(
        user_id=current_user.id,
        name=payload.name,
        species=payload.species,
        location=payload.location,
        notes=payload.notes,
    )
    db.add(plant)
    db.commit()
    db.refresh(plant)
    return PlantResponse(
        id=plant.id,
        user_id=plant.user_id,
        name=plant.name,
        species=plant.species,
        location=plant.location,
        notes=plant.notes,
        created_at=plant.created_at,
        updated_at=plant.updated_at,
        total_scans=0,
        health_status=None,
        latest_analysis=None,
    )


@router.get("", response_model=List[PlantResponse])
def list_plants(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> List[PlantResponse]:
    """List all plants owned by the authenticated user with latest analysis status."""
    plants = db.scalars(
        select(Plant).where(Plant.user_id == current_user.id).order_by(Plant.created_at.desc())
    ).all()

    results: List[PlantResponse] = []
    for p in plants:
        scans = db.scalars(
            select(Analysis)
            .where(Analysis.plant_id == p.id, Analysis.user_id == current_user.id)
            .order_by(Analysis.created_at.desc())
        ).all()
        latest = scans[0] if scans else None
        latest_status = None
        if latest and latest.result_data:
            summary = latest.result_data.get("plant_summary") or {}
            latest_status = summary.get("health_status")

        results.append(PlantResponse(
            id=p.id,
            user_id=p.user_id,
            name=p.name,
            species=p.species,
            location=p.location,
            notes=p.notes,
            created_at=p.created_at,
            updated_at=p.updated_at,
            total_scans=len(scans),
            health_status=latest_status,
            latest_analysis=_to_analysis_response(latest) if latest else None,
        ))
    return results


@router.get("/{plant_id}", response_model=PlantDetailResponse)
def get_plant_detail(
    plant_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PlantDetailResponse:
    """Retrieve details, scan history, and health trend for an owned plant."""
    plant = _get_owned_plant(plant_id, current_user, db)
    scans = db.scalars(
        select(Analysis)
        .where(Analysis.plant_id == plant.id, Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.desc())
    ).all()

    trend = []
    latest_status = None
    if scans:
        for s in reversed(scans):
            if s.status == "completed" and s.result_data:
                summary = s.result_data.get("plant_summary") or {}
                score = summary.get("overall_health_score")
                h_status = summary.get("health_status")
                avg_sev = summary.get("average_severity_percentage")
                if score is not None:
                    trend.append({
                        "analysis_id": str(s.id),
                        "timestamp": s.created_at.isoformat(),
                        "health_score": float(score),
                        "health_status": h_status,
                        "severity_percentage": float(avg_sev) if avg_sev is not None else None,
                    })
        latest = scans[0]
        if latest.result_data:
            summary = latest.result_data.get("plant_summary") or {}
            latest_status = summary.get("health_status")
    else:
        latest = None

    return PlantDetailResponse(
        id=plant.id,
        user_id=plant.user_id,
        name=plant.name,
        species=plant.species,
        location=plant.location,
        notes=plant.notes,
        created_at=plant.created_at,
        updated_at=plant.updated_at,
        total_scans=len(scans),
        health_status=latest_status,
        latest_analysis=_to_analysis_response(latest) if latest else None,
        recent_scans=[_to_analysis_response(s) for s in scans[:10]],
        health_trend=trend,
    )


@router.patch("/{plant_id}", response_model=PlantResponse)
def update_plant(
    plant_id: UUID,
    payload: PlantUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PlantResponse:
    """Update metadata for an owned plant."""
    plant = _get_owned_plant(plant_id, current_user, db)
    for field in payload.model_fields_set:
        setattr(plant, field, getattr(payload, field))
    db.commit()
    db.refresh(plant)

    scans = db.scalars(
        select(Analysis)
        .where(Analysis.plant_id == plant.id, Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.desc())
    ).all()
    latest = scans[0] if scans else None
    latest_status = None
    if latest and latest.result_data:
        summary = latest.result_data.get("plant_summary") or {}
        latest_status = summary.get("health_status")

    return PlantResponse(
        id=plant.id,
        user_id=plant.user_id,
        name=plant.name,
        species=plant.species,
        location=plant.location,
        notes=plant.notes,
        created_at=plant.created_at,
        updated_at=plant.updated_at,
        total_scans=len(scans),
        health_status=latest_status,
        latest_analysis=_to_analysis_response(latest) if latest else None,
    )


@router.delete("/{plant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plant(
    plant_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete an owned plant. Associated scans will remain with plant_id set to null."""
    plant = _get_owned_plant(plant_id, current_user, db)
    db.delete(plant)
    db.commit()


@router.post("/{plant_id}/scans/{analysis_id}", response_model=AnalysisLifecycleResponse)
def associate_scan_with_plant(
    plant_id: UUID,
    analysis_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AnalysisLifecycleResponse:
    """Link an owned analysis scan to an owned plant."""
    plant = _get_owned_plant(plant_id, current_user, db)
    analysis = db.scalar(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == current_user.id)
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    analysis.plant_id = plant.id
    db.commit()
    db.refresh(analysis)
    return _to_analysis_response(analysis)


@router.delete("/{plant_id}/scans/{analysis_id}", response_model=AnalysisLifecycleResponse)
def disassociate_scan_from_plant(
    plant_id: UUID,
    analysis_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AnalysisLifecycleResponse:
    """Unlink an analysis scan from a plant."""
    _get_owned_plant(plant_id, current_user, db)
    analysis = db.scalar(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == current_user.id)
    )
    if analysis is None or analysis.plant_id != plant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found on this plant")
    analysis.plant_id = None
    db.commit()
    db.refresh(analysis)
    return _to_analysis_response(analysis)
