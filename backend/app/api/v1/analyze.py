"""
Analysis API endpoints (v1)
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, status
from fastapi.responses import JSONResponse
import numpy as np
from PIL import Image
import io
import uuid
from datetime import datetime

from app.schemas.plant_analysis import (
    PlantAnalysisResponse, PlantAnalysisRequest,
    LeafResult, PlantHealthSummary
)
from app.services.plant_analysis_service import create_plant_analysis_service
from app.services.interfaces.plant_analysis import PlantAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency to get plant analysis service
def get_plant_analysis_service() -> PlantAnalysisService:
    return create_plant_analysis_service()


@router.post("/analyze/image", response_model=PlantAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    plant_analysis_service: PlantAnalysisService = Depends(get_plant_analysis_service)
):
    """
    Analyze a plant image for health assessment
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )

    # Check file size (limit to 10MB)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10 MB
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size too large. Maximum 10MB allowed."
        )

    try:
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(contents))

        # Convert to RGB if necessary (removes alpha channel if present)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Convert to numpy array
        image_array = np.array(image)

        logger.info(f"Processing image upload: {file.filename}, size: {len(contents)} bytes")

        # Perform analysis
        analysis_id = str(uuid.uuid4())
        result = plant_analysis_service.analyze_image(
            image=image_array,
            analysis_id=analysis_id
        )

        logger.info(f"Image analysis completed: {analysis_id}")
        return result

    except Exception as e:
        logger.error(f"Error processing image {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing image: {str(e)}"
        )


@router.post("/analyze/video", response_model=PlantAnalysisResponse)
async def analyze_video(
    file: UploadFile = File(...),
    plant_analysis_service: PlantAnalysisService = Depends(get_plant_analysis_service)
):
    """
    Analyze a plant video frame for health assessment
    (Currently processes first frame only - video tracking to be implemented)
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith('video/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a video"
        )

    # For now, we'll extract the first frame and process it as an image
    # In a full implementation, we would process multiple frames and use tracking
    try:
        # Note: Actual video frame extraction would require additional libraries like opencv-python
        # For this mock implementation, we'll treat it similar to image processing
        # but log that we're using video-specific processing

        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:  # 10 MB
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size too large. Maximum 10MB allowed."
            )

        # For mock purposes, we'll process as image (first frame simulation)
        # In reality, we'd extract a frame from the video
        image = Image.open(io.BytesIO(contents))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image_array = np.array(image)

        logger.info(f"Processing video upload: {file.filename}, size: {len(contents)} bytes (processing first frame)")

        # Perform analysis
        analysis_id = str(uuid.uuid4())
        result = plant_analysis_service.analyze_video_frame(
            frame=image_array,
            analysis_id=analysis_id
        )

        logger.info(f"Video frame analysis completed: {analysis_id}")
        return result

    except Exception as e:
        logger.error(f"Error processing video {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing video: {str(e)}"
        )


@router.get("/analysis/{analysis_id}", response_model=PlantAnalysisResponse)
async def get_analysis(
    analysis_id: str,
    plant_analysis_service: PlantAnalysisService = Depends(get_plant_analysis_service)
):
    """
    Retrieve a previous analysis by ID
    """
    # Check if the service has the method to get analysis by ID (mock service does)
    if hasattr(plant_analysis_service, 'get_analysis_by_id'):
        analysis = plant_analysis_service.get_analysis_by_id(analysis_id)
        if analysis is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        return analysis
    else:
        # Fallback for services that don't implement this method
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Analysis retrieval not yet implemented for this service type."
        )


@router.get("/analyses", response_model=List[PlantAnalysisResponse])
async def get_analyses(
    skip: int = 0,
    limit: int = 10,
    plant_analysis_service: PlantAnalysisService = Depends(get_plant_analysis_service)
):
    """
    Retrieve a list of analyses with pagination
    """
    # Check if the service has the method to get analyses (mock service does)
    if hasattr(plant_analysis_service, 'get_analyses'):
        analyses = plant_analysis_service.get_analyses(skip=skip, limit=limit)
        return analyses
    else:
        # Fallback for services that don't implement this method
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Analyses listing not yet implemented for this service type."
        )


# Health check endpoint for the analysis service
@router.get("/health")
async def analysis_health(
    plant_analysis_service: PlantAnalysisService = Depends(get_plant_analysis_service)
):
    """
    Health check for the analysis service and its ML components
    """
    try:
        is_ready = plant_analysis_service.is_ready()
        service_name = plant_analysis_service.get_service_name()

        return {
            "status": "healthy" if is_ready else "unhealthy",
            "service": service_name,
            "ml_mode": getattr(plant_analysis_service, 'ml_mode', 'unknown'),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )