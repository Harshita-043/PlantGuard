"""
Analysis API endpoints (v1)
"""
import logging
import os
import tempfile
import warnings
from typing import List
from fastapi import APIRouter, File, UploadFile, HTTPException, status
import numpy as np
from PIL import Image, UnidentifiedImageError
import uuid

from app.schemas.plant_analysis import PlantAnalysisResponse
from app.services.plant_analysis_service import create_plant_analysis_service, MLCapabilityUnavailable
from app.services.interfaces.plant_analysis import PlantAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_IMAGE_BYTES = 10 * 1024 * 1024
SUPPORTED_IMAGE_TYPES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


@router.post("/analyze/image", response_model=PlantAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
):
    """Validate an image in temporary storage, then attempt real analysis."""
    if file is None:  # Also gives direct callers the same result as a missing multipart field.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An image file is required",
        )
    expected_format = SUPPORTED_IMAGE_TYPES.get(file.content_type or "")
    if expected_format is None:
        await file.close()
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Supported image types are JPEG, PNG, and WebP",
        )

    try:
        # The client filename is deliberately ignored. Both the directory and object
        # name are generated locally, and the TemporaryDirectory context cleans up
        # on every return and exception path.
        with tempfile.TemporaryDirectory(prefix="plantguard-upload-") as temporary_directory:
            image_path = os.path.join(temporary_directory, f"{uuid.uuid4().hex}.upload")
            size = 0
            with open(image_path, "xb") as temporary_file:
                while True:
                    chunk = await file.read(min(64 * 1024, MAX_IMAGE_BYTES + 1 - size))
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_IMAGE_BYTES:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="File size too large. Maximum 10MB allowed.",
                        )
                    temporary_file.write(chunk)

            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(image_path) as image:
                        actual_format = image.format
                        image.verify()
                if actual_format != expected_format:
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail="Image content does not match its declared image type",
                    )
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(image_path) as image:
                        image_array = np.asarray(image.convert("RGB"))
            except (
                UnidentifiedImageError,
                Image.DecompressionBombError,
                Image.DecompressionBombWarning,
                OSError,
                SyntaxError,
                ValueError,
            ) as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded file is malformed or corrupted",
                ) from exc

            try:
                plant_analysis_service: PlantAnalysisService = create_plant_analysis_service()
            except MLCapabilityUnavailable as exc:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

            analysis_id = str(uuid.uuid4())
            result = plant_analysis_service.analyze_image(image=image_array, analysis_id=analysis_id)
            logger.info("Image analysis completed: %s", analysis_id)
            return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error processing an uploaded image")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Image processing failed",
        ) from exc
    finally:
        await file.close()


@router.post("/analyze/video", response_model=PlantAnalysisResponse)
async def analyze_video(
    file: UploadFile = File(...),
):
    """Video analysis is not integrated in this repository."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Video analysis is not available until verified video inference is integrated",
    )


@router.get("/analysis/{analysis_id}", response_model=PlantAnalysisResponse)
async def get_analysis(
    analysis_id: str,
):
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Analysis retrieval is unavailable because results are not persisted",
    )


@router.get("/analyses", response_model=List[PlantAnalysisResponse])
async def get_analyses(
    skip: int = 0,
    limit: int = 10,
):
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Analysis history is unavailable because results are not persisted",
    )


# Health check endpoint for the analysis service
@router.get("/analyze/health")
async def analysis_health(
):
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Plant analysis is unavailable because no ML implementation is integrated",
    )
