"""Authenticated image storage and analysis lifecycle endpoints."""

import logging
import os
import tempfile
import warnings
from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, Response, status
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.api.v1.ownership import get_owned_analysis
from app.core.database import get_db
from app.core.config import settings
from app.models.analysis import Analysis
from app.models.user import User
from app.schemas.analysis_lifecycle import AnalysisAssetLink, AnalysisAssetsResponse, AnalysisLifecycleResponse
from app.ml.errors import InferenceError
from app.schemas.plant_analysis import PlantAnalysisResponse
from app.services.plant_analysis_service import create_plant_analysis_service
from app.storage import ObjectNotFound, ObjectStorage, StorageConfigurationError, StorageError, create_object_storage


logger = logging.getLogger(__name__)
router = APIRouter()

MAX_IMAGE_BYTES = 10 * 1024 * 1024
SUPPORTED_IMAGE_TYPES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


@router.post(
    "/analyze/image",
    response_model=AnalysisLifecycleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def analyze_image(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AnalysisLifecycleResponse:
    """Validate, privately store, run the configured real pipeline, and persist its result."""
    try:
        image_content, content_type = await _read_validated_image(file)
    finally:
        await file.close()

    analysis_id = uuid4()
    object_key = f"users/{current_user.id}/analyses/{analysis_id}/image"
    try:
        storage: ObjectStorage = create_object_storage()
    except StorageConfigurationError as exc:
        logger.error("Image storage configuration is unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image storage is unavailable",
        ) from exc

    try:
        storage.put(
            image_content,
            object_key=object_key,
            content_type=content_type,
        )
    except StorageError as exc:
        logger.error("Image storage write failed for analysis %s", analysis_id)
        _cleanup_after_failed_write(storage, object_key, analysis_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image storage is unavailable",
        ) from exc

    analysis = Analysis(
        id=analysis_id,
        user_id=current_user.id,
        image_object_key=object_key,
        image_content_type=content_type,
        image_size_bytes=len(image_content),
        status="pending",
    )
    db.add(analysis)
    try:
        db.flush()
        db.commit()
    except Exception as exc:
        db.rollback()
        try:
            storage.delete(object_key)
        except StorageError:
            logger.error(
                "Analysis persistence failed and image cleanup could not be confirmed (analysis %s)",
                analysis_id,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Analysis persistence failed and image cleanup could not be confirmed",
            ) from None
        logger.error("Analysis persistence failed; stored image was removed (analysis %s)", analysis_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not persist the uploaded analysis",
        ) from exc

    try:
        # Inference is synchronous but runs off the ASGI event loop. The model
        # service loads one stage at a time and enforces its process-wide slot.
        application_service = (
            create_plant_analysis_service()
            if settings.PLANTGUARD_INFERENCE_PROFILE == "remote"
            else create_plant_analysis_service(storage=storage)
        )
        result = await run_in_threadpool(
            application_service.inference.analyze_bytes,
            image_content,
            analysis_id=str(analysis_id),
        )
        analysis.status = "completed"
        analysis.result_data = result.model_dump(mode="json")
        analysis.failure_data = None
        analysis.processing_time_ms = result.processing_time_ms
        analysis.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(analysis)
    except InferenceError as exc:
        db.rollback()
        public_message = (
            "The configured model or runtime is unavailable"
            if exc.code in {
                "missing_artifact", "unsupported_runtime", "artifact_integrity", "resource_limit"
            }
            else "Plant analysis could not be completed"
        )
        failed = db.get(Analysis, analysis_id)
        if failed is not None:
            failed.status = "failed"
            failed.failure_data = {
                "code": str(exc.code),
                "stage": exc.stage,
                "message": public_message,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }
            failed.completed_at = datetime.now(timezone.utc)
            db.commit()
        logger.warning(
            "Plant inference failed analysis_id=%s stage=%s error_code=%s",
            analysis_id, exc.stage, exc.code,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"analysis_id": str(analysis_id), "code": str(exc.code),
                    "stage": exc.stage, "message": public_message},
        ) from exc
    except Exception as exc:
        db.rollback()
        failed = db.get(Analysis, analysis_id)
        if failed is not None:
            failed.status = "failed"
            failed.failure_data = {
                "code": "inference_internal_error",
                "stage": "pipeline",
                "message": "Plant analysis failed",
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }
            failed.completed_at = datetime.now(timezone.utc)
            db.commit()
        logger.exception("Unexpected plant inference failure analysis_id=%s", analysis_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"analysis_id": str(analysis_id), "code": "inference_internal_error",
                    "message": "Plant analysis failed"},
        ) from exc
    return _lifecycle_response(analysis)


@router.get("/analysis/{analysis_id}", response_model=AnalysisLifecycleResponse)
def get_analysis(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
) -> AnalysisLifecycleResponse:
    """Return lifecycle metadata only for the authenticated owner."""
    return _lifecycle_response(analysis)


@router.get("/analysis/{analysis_id}/assets", response_model=AnalysisAssetsResponse)
def get_analysis_asset_urls(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
) -> AnalysisAssetsResponse:
    """Return short-lived provider URLs or authenticated local-proxy URLs for owned assets."""
    try:
        storage: ObjectStorage = create_object_storage()
    except StorageConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Image storage is unavailable") from exc

    assets = []
    for object_key in _analysis_object_keys(analysis):
        try:
            download_url = storage.create_download_url(object_key, expires_in=300)
        except (StorageError, ValueError) as exc:
            logger.error("Analysis asset link creation failed analysis_id=%s", analysis.id)
            raise HTTPException(status_code=503, detail="Analysis assets are unavailable") from exc
        expires_in = 300 if download_url is not None else None
        if download_url is None:
            download_url = (
                f"/api/v1/analysis/{analysis.id}/asset?key={quote(object_key, safe='')}"
            )
        assets.append(AnalysisAssetLink(
            storage_key=object_key,
            kind="original" if object_key == analysis.image_object_key else "artifact",
            download_url=download_url,
            expires_in_seconds=expires_in,
        ))
    return AnalysisAssetsResponse(analysis_id=analysis.id, assets=assets)


@router.get("/analysis/{analysis_id}/asset")
def get_analysis_asset(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    key: Annotated[str, Query(min_length=1, max_length=512)],
) -> Response:
    """Stream a referenced private asset through an authenticated owner check."""
    if key not in _analysis_object_keys(analysis):
        raise HTTPException(status_code=404, detail="Asset not found")
    try:
        stored = create_object_storage().get(key)
    except ObjectNotFound:
        raise HTTPException(status_code=404, detail="Asset not found") from None
    except (StorageConfigurationError, StorageError) as exc:
        logger.error("Analysis asset read failed analysis_id=%s", analysis.id)
        raise HTTPException(status_code=503, detail="Analysis assets are unavailable") from exc
    if stored.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Stored asset type is not supported")
    return Response(
        content=stored.content,
        media_type=stored.content_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )

@router.delete("/analysis/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete an owner's analysis and all validated objects referenced by it."""
    try:
        storage: ObjectStorage = create_object_storage()
    except StorageConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Image storage is unavailable") from exc

    for object_key in _analysis_object_keys(analysis):
        try:
            storage.delete(object_key)
        except StorageError as exc:
            logger.error("Analysis cleanup failed analysis_id=%s", analysis.id)
            raise HTTPException(
                status_code=503,
                detail="Analysis assets could not be deleted; retry the request",
            ) from exc

    try:
        db.delete(analysis)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Analysis deletion persistence failed analysis_id=%s", analysis.id)
        raise HTTPException(status_code=500, detail="Could not delete the analysis record") from exc

@router.get("/analyses", response_model=list[AnalysisLifecycleResponse])
def get_analyses(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> list[AnalysisLifecycleResponse]:
    """List the authenticated user's analyses in deterministic newest-first order."""
    analyses = db.scalars(
        select(Analysis)
        .where(Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return [_lifecycle_response(analysis) for analysis in analyses]


@router.post("/analyze/video", response_model=PlantAnalysisResponse)
async def analyze_video(
    file: UploadFile = File(...),
):
    """Video inference is not yet supported by the model pipeline."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Video analysis is not available until verified video inference is integrated",
    )


@router.get("/analyze/health")
async def analysis_health():
    """Report prerequisites without calling an unverified model pipeline ready."""
    service = create_plant_analysis_service()
    if not service.is_ready():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail={
                                "status": "unavailable",
                                "inference_available": False,
                                "code": "model_prerequisites_unavailable",
                                "message": "Configured model artifacts or runtime are unavailable",
                            })
    # This process constructs the adapters lazily. A prerequisite probe does not
    # verify checkpoint hashes, load weights, or prove real inference succeeds.
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail={
                            "status": "unverified",
                            "inference_available": False,
                            "code": "model_validation_required",
                            "message": "Model prerequisites are present, but checkpoint integrity and real inference have not been verified",
                        })


async def _read_validated_image(file: UploadFile) -> tuple[bytes, str]:
    expected_format = SUPPORTED_IMAGE_TYPES.get(file.content_type or "")
    if expected_format is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Supported image types are JPEG, PNG, and WebP",
        )

    with tempfile.TemporaryDirectory(prefix="plantguard-upload-") as temporary_directory:
        # Ignore the client filename; all temporary paths are generated locally.
        image_path = os.path.join(temporary_directory, f"{uuid4().hex}.upload")
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
                    image.load()
            with open(image_path, "rb") as validated_file:
                return validated_file.read(), file.content_type or ""
        except HTTPException:
            raise
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


def _analysis_object_keys(analysis: Analysis) -> list[str]:
    """Collect only object keys within this analysis' original and artifact namespaces."""
    analysis_id = str(analysis.id)
    user_id = str(analysis.user_id)
    allowed_prefixes = (
        f"users/{user_id}/analyses/{analysis_id}/",
        f"analyses/{analysis_id}/",
    )
    keys: set[str] = set()
    original_key = analysis.image_object_key
    if isinstance(original_key, str) and original_key.startswith(allowed_prefixes[0]):
        keys.add(original_key)

    def visit(value: object) -> None:
        if isinstance(value, dict):
            asset_key = value.get("storage_key")
            if isinstance(asset_key, str) and asset_key.startswith(allowed_prefixes):
                try:
                    from app.storage.keys import validate_object_key
                    keys.add(validate_object_key(asset_key))
                except StorageError:
                    logger.warning("Ignoring invalid stored asset key analysis_id=%s", analysis.id)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(analysis.result_data)
    return sorted(keys)

def _lifecycle_response(analysis: Analysis) -> AnalysisLifecycleResponse:
    return AnalysisLifecycleResponse(
        analysis_id=analysis.id,
        status=analysis.status,
        created_at=analysis.created_at,
        image_content_type=analysis.image_content_type,
        image_size_bytes=analysis.image_size_bytes,
        result_available=analysis.result_data is not None,
        result=analysis.result_data,
        failure=analysis.failure_data,
    )


def _cleanup_after_failed_write(storage: ObjectStorage, object_key: str, analysis_id: UUID) -> None:
    try:
        storage.delete(object_key)
    except StorageError:
        logger.error(
            "Image write failed and object cleanup could not be confirmed (analysis %s)",
            analysis_id,
        )
