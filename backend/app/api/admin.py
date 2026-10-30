"""Protected runtime diagnostics without artifact paths or secret values."""

import hmac
import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from app.core.config import settings
from app.ml.device import device_manager
from app.ml.errors import ModelCapabilityError
from app.ml.remote import probe_remote_health
from app.ml.runtime import collect_runtime_capabilities
from app.ml.service import PlantAnalysisService as ModelInferenceService
from app.ml.variants import MODEL_IDS, ModelVariantRegistry
from app.services.plant_analysis_service import create_plant_analysis_service

router = APIRouter(prefix="/admin", tags=["administration"])


def _authorized(authorization: str | None, expected: str | None) -> bool:
    if not expected or not authorization:
        return False
    scheme, separator, token = authorization.partition(" ")
    return bool(separator and scheme.lower() == "bearer" and hmac.compare_digest(token, expected))


@router.get("/runtime")
def runtime_diagnostics(authorization: Annotated[str | None, Header()] = None):
    diagnostics_token = settings.PLANTGUARD_DIAGNOSTICS_TOKEN
    if diagnostics_token is None:
        raise HTTPException(status_code=404, detail="Not found")
    if not _authorized(authorization, diagnostics_token.get_secret_value()):
        raise HTTPException(status_code=401, detail="Administrative credentials required",
                            headers={"WWW-Authenticate": "Bearer"})

    profile = settings.PLANTGUARD_INFERENCE_PROFILE
    if profile == "auto":
        profile = "cuda" if device_manager.active_device.startswith("cuda") else "cpu"
    memory_limit = (settings.PLANTGUARD_CUDA_MEMORY_LIMIT_GB if profile == "cuda"
                    else settings.PLANTGUARD_CPU_MEMORY_LIMIT_GB)
    remote_credentials_present = bool(settings.PLANTGUARD_REMOTE_INFERENCE_URL and settings.PLANTGUARD_REMOTE_INFERENCE_TOKEN)
    remote_configured = remote_credentials_present and settings.PLANTGUARD_REMOTE_IMAGE_UPLOAD_AUTHORIZED
    remote_status = ("configured_disabled" if remote_configured else
                     "authorization_required" if remote_credentials_present else "not_configured")
    if (profile == "remote" and remote_configured and settings.PLANTGUARD_REMOTE_INFERENCE_URL
            and settings.PLANTGUARD_REMOTE_INFERENCE_TOKEN):
        remote_status = probe_remote_health(
            settings.PLANTGUARD_REMOTE_INFERENCE_URL,
            settings.PLANTGUARD_REMOTE_INFERENCE_TOKEN.get_secret_value(),
        )
    capabilities = collect_runtime_capabilities(
        profile=profile,
        memory_limit_gb=memory_limit,
        concurrency=(settings.PLANTGUARD_REMOTE_MAX_CONCURRENCY if profile == "remote"
                     else settings.PLANTGUARD_MAX_CONCURRENCY),
        remote_configured=remote_configured,
        remote_status=remote_status,
    )
    manifest_path = Path(__file__).resolve().parents[3] / "artifacts" / "model_manifest.json"
    manifest_summary = {}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if profile == "remote":
            manifest_summary["remote_pipeline"] = {
                "artifact_status": "managed_by_remote_service",
                "initialization_status": "remote",
                "supported_operations": ["plant_analysis"],
            }
        else:
            application_service = create_plant_analysis_service()
            inference = application_service.inference
            if not isinstance(inference, ModelInferenceService):
                raise RuntimeError("local inference service is unavailable")
            variant_registry = ModelVariantRegistry(manifest_path.parents[1])
            configured_variants = {
                "dino_leaf_filter": settings.PLANTGUARD_LEAF_FILTER_VERSION,
                "dino_disease_classifier": settings.PLANTGUARD_DISEASE_CLASSIFIER_VARIANT,
                "segformer_disease_segmentation": settings.PLANTGUARD_SEGFORMER_VARIANT,
            }
            model_adapters = {
                "sam2_hiera_base_plus": (inference.sam, "leaf_proposals"),
                "mobile_sam_vit_t": (inference.mobile_sam, "fallback_leaf_proposals"),
                "dinov2_vits14_leaf_filter": (inference.leaf_filter, "leaf_candidate_filtering"),
                "dinov2_vitb14_classifier": (inference.classifier, "disease_classification"),
                "segformer_b0_plantseg": (inference.segmenter, "lesion_segmentation"),
            }
            for model_id, (adapter, operation) in model_adapters.items():
                model = manifest.get("models", {}).get(model_id, {})
                original = next(
                    (item for item in model.get("variants", []) if item.get("kind") == "original"),
                    None,
                )
                compatibility = capabilities.model_compatibility.get(model_id, {}).get(profile, {})
                selection = None
                selection_error = None
                try:
                    selection = variant_registry.select(
                        adapter.name,
                        profile=profile,
                        capabilities=capabilities,
                        memory_limit_gb=memory_limit,
                        concurrency=capabilities.configured_concurrency,
                        requested_variant=configured_variants.get(adapter.name),
                    )
                except ModelCapabilityError as exc:
                    selection_error = exc.code.value

                is_loaded = adapter.is_ready()
                manifest_summary[model_id] = {
                    "configured_candidate": original.get("variant_id") if original else None,
                    "selected_variant": selection["variant_id"] if selection else None,
                    "artifact_status": "verified" if selection else "unavailable",
                    "selection_error_code": selection_error,
                    "runtime_supported": compatibility.get("status") == "prerequisites_present",
                    "initialization_status": adapter.loading_status.value,
                    "loaded_model_identity": (
                        {"model_id": model_id, "variant_id": adapter.artifact_version}
                        if is_loaded else None
                    ),
                    "device": adapter.active_device if is_loaded else None,
                    "load_error_code": (
                        adapter.load_error_code.value
                        if getattr(adapter.load_error_code, "value", None) else None
                    ),
                    "supported_operations": [operation] if selection else [],
                    "optimized_variant_count": sum(
                        1 for item in model.get("variants", []) if item.get("kind") != "original"
                    ),
                }
    except (OSError, ValueError):
        manifest_summary = {"status": "manifest_unavailable"}
    return {"capabilities": capabilities.public_dict(),
            "model_variants": manifest_summary,
            "model_loading_policy": "lazy_sequential",
            "secrets_included": False}
