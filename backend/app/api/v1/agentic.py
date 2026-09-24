"""Agentic API boundary, disabled until real capabilities are integrated."""

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.plant_analysis import PlantAnalysisResponse

router = APIRouter()


@router.post("/analyze/agentic/image", response_model=PlantAnalysisResponse)
async def analyze_image_agentic(file: UploadFile = File(...)):
    """Return an explicit unavailable response instead of fabricated analysis."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Agentic plant analysis is unavailable until real ML capabilities are integrated",
    )
