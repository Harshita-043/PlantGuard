"""Protected runtime diagnostics without artifact paths or secret values."""

import hmac
import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from app.core.config import settings
from app.ml.device import device_manager
from app.ml.remote import probe_remote_health
from app.ml.runtime import collect_runtime_capabilities
from app.ml.registry import model_registry

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
        adapter_keys = {
            "sam2_hiera_base_plus": "leaf_instance_segmentation",
            "dinov2_vits14_leaf_filter": "leaf_filter",
            "dinov2_vitb14_classifier": "disease_classifier",
            "segformer_b0_plantseg": "disease_segmentation",
        }
        for model_id, model in manifest.get("models", {}).items():
            variant = next((v for v in model.get("variants", []) if v.get("kind") == "original"), None)
            adapter = model_registry.get_adapter(adapter_keys.get(model_id, ""))
            selected = getattr(adapter, "artifact_version", None) if adapter else None
            if selected and selected not in {"v1", "v2", "plantseg-b0-v1", "sam2.1-hiera-base-plus"}:
                selected_variant = selected
            else:
                selected_variant = None
            manifest_summary[model_id] = {
                "configured_candidate": variant.get("variant_id") if variant else None,
                "last_selected_variant": selected_variant,
                "selection_status": "pending_runtime_and_checksum_verification" if variant and not variant.get("sha256") else "integrity_check_required_at_load",
                "optimized_variant_count": sum(1 for v in model.get("variants", []) if v.get("kind") != "original"),
            }
    except (OSError, ValueError):
        manifest_summary = {"status": "manifest_unavailable"}
    return {"capabilities": capabilities.public_dict(),
            "model_variants": manifest_summary,
            "model_loading_policy": "lazy_sequential",
            "secrets_included": False}
