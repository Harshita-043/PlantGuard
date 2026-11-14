"""Application implementation of PlantManagementService.

Encapsulates all plant profile CRUD, user ownership validation, and scan association persistence.
"""
import logging
from typing import Annotated, Any, Dict, List, Optional
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.plant import Plant
from app.schemas.analysis_lifecycle import AnalysisLifecycleResponse
from app.schemas.inference import FullScanResult
from app.schemas.plant import PlantCreate, PlantDetailResponse, PlantResponse, PlantUpdate
from app.services.interfaces.plant_management import (
    AnalysisScanNotFoundError,
    PlantManagementService,
    PlantNotFoundError,
    ScanNotAssociatedWithPlantError,
)

logger = logging.getLogger(__name__)


def _to_analysis_response(analysis: Analysis) -> AnalysisLifecycleResponse:
    """Map an Analysis ORM model to the AnalysisLifecycleResponse contract."""
    validated_result = None
    if analysis.result_data:
        try:
            validated_result = FullScanResult.model_validate(analysis.result_data)
        except Exception:
            logger.warning(
                "Analysis %s result_data could not be parsed as FullScanResult; leaving as unparsed",
                analysis.id,
            )
            validated_result = None

    return AnalysisLifecycleResponse(
        analysis_id=analysis.id,
        plant_id=analysis.plant_id,
        status=analysis.status,
        created_at=analysis.created_at,
        image_content_type=analysis.image_content_type,
        image_size_bytes=analysis.image_size_bytes,
        result_available=analysis.result_data is not None,
        result=validated_result,
        failure=analysis.failure_data,
    )



class ApplicationPlantManagementService(PlantManagementService):
    """Production implementation of PlantManagementService backed by SQLAlchemy."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _get_owned_plant_entity(self, plant_id: UUID, user_id: UUID) -> Plant:
        """Fetch plant verifying ownership, raising PlantNotFoundError on missing/unauthorized."""
        plant = self.db.scalar(
            select(Plant).where(Plant.id == plant_id, Plant.user_id == user_id)
        )
        if plant is None:
            raise PlantNotFoundError(f"Plant {plant_id} not found or not owned by user {user_id}")
        return plant

    def _get_scans_for_plant(self, plant_id: UUID, user_id: UUID) -> List[Analysis]:
        """Fetch all analyses associated with a plant owned by user, sorted newest first."""
        return list(
            self.db.scalars(
                select(Analysis)
                .where(Analysis.plant_id == plant_id, Analysis.user_id == user_id)
                .order_by(Analysis.created_at.desc())
            ).all()
        )

    def _build_plant_response(self, plant: Plant, scans: Optional[List[Analysis]] = None) -> PlantResponse:
        """Construct PlantResponse schema including scan count and latest health status."""
        if scans is None:
            scans = self._get_scans_for_plant(plant.id, plant.user_id)

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

    def create_plant(self, user_id: UUID, payload: PlantCreate) -> PlantResponse:
        """Register a new plant profile owned by user_id."""
        plant = Plant(
            user_id=user_id,
            name=payload.name,
            species=payload.species,
            location=payload.location,
            notes=payload.notes,
        )
        self.db.add(plant)
        self.db.commit()
        self.db.refresh(plant)
        return self._build_plant_response(plant, scans=[])

    def get_plant(self, plant_id: UUID, user_id: UUID) -> PlantResponse:
        """Retrieve plant profile by ID enforcing user ownership."""
        plant = self._get_owned_plant_entity(plant_id, user_id)
        return self._build_plant_response(plant)

    def get_plant_detail(self, plant_id: UUID, user_id: UUID) -> PlantDetailResponse:
        """Retrieve detailed plant profile with scan history and health trend."""
        plant = self._get_owned_plant_entity(plant_id, user_id)
        scans = self._get_scans_for_plant(plant.id, user_id)

        trend: List[Dict[str, Any]] = []
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

    def list_user_plants(self, user_id: UUID) -> List[PlantResponse]:
        """List all plants owned by user_id, ordered newest first."""
        plants = self.db.scalars(
            select(Plant).where(Plant.user_id == user_id).order_by(Plant.created_at.desc())
        ).all()

        results: List[PlantResponse] = []
        for p in plants:
            results.append(self._build_plant_response(p))
        return results

    def update_plant(self, plant_id: UUID, user_id: UUID, payload: PlantUpdate) -> PlantResponse:
        """Update metadata fields on an owned plant profile."""
        plant = self._get_owned_plant_entity(plant_id, user_id)
        for field in payload.model_fields_set:
            setattr(plant, field, getattr(payload, field))
        self.db.commit()
        self.db.refresh(plant)
        return self._build_plant_response(plant)

    def delete_plant(self, plant_id: UUID, user_id: UUID) -> None:
        """Safely delete plant profile, ensuring analysis scan history is preserved."""
        plant = self._get_owned_plant_entity(plant_id, user_id)

        # Explicitly detach analyses to guarantee preservation across all database dialects
        analyses = self.db.scalars(
            select(Analysis).where(Analysis.plant_id == plant.id)
        ).all()
        for analysis in analyses:
            analysis.plant_id = None

        self.db.delete(plant)
        self.db.commit()

    def associate_scan(self, plant_id: UUID, analysis_id: UUID, user_id: UUID) -> AnalysisLifecycleResponse:
        """Link an owned analysis scan to an owned plant profile."""
        plant = self._get_owned_plant_entity(plant_id, user_id)
        analysis = self.db.scalar(
            select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user_id)
        )
        if analysis is None:
            raise AnalysisScanNotFoundError(
                f"Analysis {analysis_id} not found or not owned by user {user_id}"
            )
        analysis.plant_id = plant.id
        self.db.commit()
        self.db.refresh(analysis)
        return _to_analysis_response(analysis)

    def disassociate_scan(self, plant_id: UUID, analysis_id: UUID, user_id: UUID) -> AnalysisLifecycleResponse:
        """Unlink an owned analysis scan from a plant profile."""
        self._get_owned_plant_entity(plant_id, user_id)
        analysis = self.db.scalar(
            select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user_id)
        )
        if analysis is None or analysis.plant_id != plant_id:
            raise ScanNotAssociatedWithPlantError(
                f"Analysis {analysis_id} is not associated with plant {plant_id}"
            )
        analysis.plant_id = None
        self.db.commit()
        self.db.refresh(analysis)
        return _to_analysis_response(analysis)


def get_plant_management_service(
    db: Annotated[Session, Depends(get_db)]
) -> PlantManagementService:
    """FastAPI dependency for injecting the PlantManagementService."""
    return ApplicationPlantManagementService(db=db)
