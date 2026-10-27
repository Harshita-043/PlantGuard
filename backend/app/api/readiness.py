"""Liveness, dependency readiness, and safe model-profile diagnostics."""

import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal
from app.ml.device import device_manager
from app.ml.service import PlantAnalysisService
from app.services.plant_analysis_service import create_plant_analysis_service
from app.storage import StorageConfigurationError, StorageError, create_object_storage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Process liveness only; does not contact external dependencies or load models."""
    return {"status": "ok"}


@router.get("/ready")
def readiness() -> dict[str, object]:
    """Return 503 until DB, storage, configured model runtime and loaded models are ready."""
    checks: dict[str, object] = {
        "database": False,
        "storage": False,
        "model_prerequisites": False,
        "models_loaded": False,
    }
    try:
        if SessionLocal is None:
            raise RuntimeError("database_not_configured")
        with SessionLocal() as db:
            db.execute(text("SELECT 1")).scalar_one()
        checks["database"] = True
    except Exception as exc:
        logger.warning("readiness_dependency_failed dependency=database error_type=%s", type(exc).__name__)

    try:
        checks["storage"] = bool(create_object_storage().check_ready())
    except (StorageConfigurationError, StorageError) as exc:
        logger.warning("readiness_dependency_failed dependency=storage error_type=%s", type(exc).__name__)

    try:
        application_service = create_plant_analysis_service()
        inference = getattr(application_service, "inference", None)
        if isinstance(inference, PlantAnalysisService):
            checks["model_prerequisites"] = bool(application_service.is_ready())
            adapters = (inference.sam, inference.leaf_filter, inference.classifier, inference.segmenter)
            checks["models_loaded"] = all(adapter.is_ready() for adapter in adapters)
        elif inference is not None and settings.PLANTGUARD_INFERENCE_PROFILE == "remote":
            # The remote client performs its own authenticated bounded readiness probe.
            checks["model_prerequisites"] = bool(application_service.is_ready())
            checks["models_loaded"] = checks["model_prerequisites"]
    except Exception as exc:
        logger.warning("readiness_dependency_failed dependency=models error_type=%s", type(exc).__name__)

    ready = all(checks.values())
    payload: dict[str, object] = {"status": "ready" if ready else "not_ready", "checks": checks}
    if not ready:
        raise HTTPException(status_code=503, detail=payload)
    return payload


@router.get("/models")
def models() -> dict[str, object]:
    """Expose model versions and runtime profile without filesystem paths or secrets."""
    profile = settings.PLANTGUARD_INFERENCE_PROFILE
    model_data: dict[str, object] = {}
    if profile == "remote":
        model_data["remote_pipeline"] = {
            "configured_variant": "remote_managed",
            "manifest_checksum": "not_applicable",
            "checkpoint_status": "managed_by_remote_service",
            "runtime_validation": "reported_per_prediction",
        }
    else:
        manifest_path = Path(__file__).resolve().parents[3] / "artifacts" / "model_manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for model_id, entry in manifest.get("models", {}).items():
                variants = entry.get("variants", [])
                original = next((item for item in variants if item.get("kind") == "original"), None)
                model_data[model_id] = {
                    "configured_variant": original.get("variant_id") if original else None,
                    "precision": original.get("precision") if original else None,
                    "manifest_checksum": (
                        "recorded" if entry.get("original_checkpoint", {}).get("sha256") else "missing"
                    ),
                    "checkpoint_status": "not_verified_at_startup",
                    "runtime_validation": "not_smoke_tested",
                }
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("model_manifest_unavailable error_type=%s", type(exc).__name__)
            model_data = {}

    if profile == "cpu":
        device = "cpu"
    elif profile == "cuda":
        device = "cuda:0"
    elif profile == "remote":
        device = "remote"
    else:
        device = device_manager.active_device
    return {
        "profile": profile,
        "device": device,
        "precision": "profile_managed" if profile == "remote" else "fp32",
        "models": model_data,
        "model_load_policy": "lazy_sequential",
    }