"""Application-level Plant Analysis Service integrating ML inference with FastAPI."""

import io
import importlib.util
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings
from app.ml.errors import (
    InferenceError,
    InferenceErrorCode,
    InvalidImageError,
    ModelCapabilityError,
)
from app.ml.variants import MODEL_IDS
from app.ml.service import PlantAnalysisService as ModelInferenceService
from app.ml.remote import RemoteInferenceClient, probe_remote_health
from app.schemas.inference import (
    FullScanResult,
    SeverityLevel as ModelSeverityLevel,
)
from app.schemas.plant_analysis import (
    HealthStatus,
    LeafResult,
    PlantAnalysisResponse,
    PlantHealthSummary,
    SeverityLevel,
)
from app.services.interfaces.plant_analysis import PlantAnalysisService
from app.storage.interface import ObjectStorage

logger = logging.getLogger(__name__)

MAX_IMAGE_SIDE = 8192
MAX_IMAGE_PIXELS = 32_000_000


class MLCapabilityUnavailable(ModelCapabilityError):
    """Backward-compatible typed capability error for legacy agent routes."""

    def __init__(self, message: str):
        super().__init__(InferenceErrorCode.UNSUPPORTED_RUNTIME, message, stage="agent")


class ApplicationPlantAnalysisService(PlantAnalysisService):
    """
    Application-level Plant Analysis Service.
    Acts as the application-facing interface coordinating the underlying ML inference
    service, validating inputs, handling errors, and returning structured contracts.
    """

    def __init__(
        self,
        inference: ModelInferenceService | RemoteInferenceClient | None = None,
        storage: ObjectStorage | None = None,
    ):
        self.storage = storage
        if inference is not None:
            self.inference = inference
        elif settings.PLANTGUARD_INFERENCE_PROFILE == "remote":
            self.inference = RemoteInferenceClient.from_settings()
        else:
            device = {"cpu": "cpu", "cuda": "cuda:0"}.get(settings.PLANTGUARD_INFERENCE_PROFILE)
            self.inference = ModelInferenceService(device=device, storage=storage)

    def initialize(self) -> None:
        """Initialize the service. Model weights remain loaded on-demand/sequentially."""
        if hasattr(self.inference, "initialize"):
            self.inference.initialize()
        return None

    def is_ready(self) -> bool:
        """Check if required model prerequisites are available."""
        return bool(self.model_readiness().get("model_prerequisites"))

    def model_readiness(self) -> Dict[str, Optional[bool]]:
        """Check required on-demand stages and distinguish SAM2 from its fallback."""
        if isinstance(self.inference, RemoteInferenceClient):
            token = settings.PLANTGUARD_REMOTE_INFERENCE_TOKEN
            available = bool(
                token and probe_remote_health(
                    settings.PLANTGUARD_REMOTE_INFERENCE_URL or "",
                    token.get_secret_value()
                ) == "available"
            )
            return {
                "model_prerequisites": available,
                "sam2_primary": None,
                "mobilesam_fallback": None,
            }

        if not hasattr(self.inference, "sam") or not hasattr(self.inference, "mobile_sam"):
            # If a mocked or customized inference service is injected
            return {
                "model_prerequisites": True,
                "sam2_primary": True,
                "mobilesam_fallback": False,
            }

        model_status = {
            "model_prerequisites": False,
            "sam2_primary": self._variant_is_selectable(self.inference.sam),
            "mobilesam_fallback": self._variant_is_selectable(self.inference.mobile_sam),
        }
        if not all(importlib.util.find_spec(name) is not None for name in ("torch", "transformers")):
            return model_status
        try:
            self.inference.ood_detector.validate_calibration()
        except ModelCapabilityError:
            return model_status
        if getattr(self.inference.segmenter, "_configuration_error", None) is not None:
            return model_status
        class_mapping = self.inference.classifier.get_class_mapping() or {}
        if len(class_mapping) != 38:
            return model_status
        try:
            for adapter in (self.inference.leaf_filter, self.inference.classifier, self.inference.segmenter):
                self.inference._select_variant(adapter, MODEL_IDS[adapter.name])
        except ModelCapabilityError:
            return model_status
        model_status["model_prerequisites"] = (
            model_status["sam2_primary"] is True or model_status["mobilesam_fallback"] is True
        )
        return model_status

    def _variant_is_selectable(self, adapter) -> bool:
        if hasattr(self.inference, "sam") and adapter is self.inference.sam:
            config_rel = Path(adapter.config_name)
            if config_rel.is_absolute() or ".." in config_rel.parts:
                return False
            package_spec = importlib.util.find_spec("sam2")
            if package_spec is None or package_spec.origin is None:
                return False
            package_root = Path(package_spec.origin).resolve().parent
            if not (package_root / config_rel).is_file():
                return False
        try:
            if hasattr(self.inference, "_select_variant"):
                self.inference._select_variant(adapter, MODEL_IDS[adapter.name])
            return True
        except ModelCapabilityError:
            return False

    def get_service_name(self) -> str:
        return "PlantGuardModelInference"

    def analyze_bytes(
        self,
        image_bytes: bytes,
        analysis_id: Optional[str] = None
    ) -> FullScanResult:
        """
        Application-level entry point to analyze raw image bytes.

        Validates payload non-emptiness and delegates execution to the underlying
        inference service. Propagates typed inference errors cleanly to the caller.
        """
        if not isinstance(image_bytes, (bytes, bytearray, memoryview)):
            raise InvalidImageError("Image payload must be bytes-like")
        if len(image_bytes) == 0:
            raise InvalidImageError("Image payload is empty")

        if hasattr(self.inference, "analyze_bytes"):
            return self.inference.analyze_bytes(bytes(image_bytes), analysis_id=analysis_id)

        # Fallback decode if injected inference only implements analyze(np.ndarray)
        try:
            with Image.open(io.BytesIO(image_bytes)) as im:
                if im.width <= 0 or im.height <= 0 or im.width > MAX_IMAGE_SIDE or im.height > MAX_IMAGE_SIDE:
                    raise InvalidImageError("Image dimensions exceed the supported limit")
                if im.width * im.height > MAX_IMAGE_PIXELS:
                    raise InvalidImageError("Image pixel count exceeds the supported limit")
                oriented = ImageOps.exif_transpose(im)
                image_array = np.asarray(oriented.convert("RGB"), dtype=np.uint8)
        except InvalidImageError:
            raise
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            raise InvalidImageError("Image is corrupt or cannot be decoded") from exc

        return self.analyze(image_array, analysis_id=analysis_id)

    def analyze(
        self,
        image: np.ndarray,
        analysis_id: Optional[str] = None
    ) -> FullScanResult:
        """
        Analyze an in-memory RGB numpy image array through the inference pipeline.
        """
        if not isinstance(image, np.ndarray):
            raise InvalidImageError("Image must be a numpy ndarray")
        if image.ndim != 3 or image.shape[2] != 3:
            raise InvalidImageError("Image must be an RGB 3-channel array (H, W, 3)")
        if image.size == 0 or image.shape[0] == 0 or image.shape[1] == 0:
            raise InvalidImageError("Image dimensions must be non-zero")

        return self.inference.analyze(image, analysis_id=analysis_id)

    def analyze_image(
        self,
        image: np.ndarray,
        analysis_id: Optional[str] = None
    ) -> PlantAnalysisResponse:
        """
        Legacy compatibility method mapping FullScanResult to PlantAnalysisResponse.
        Fails closed with typed OUT_OF_DISTRIBUTION error if any leaf is flagged as OOD.
        """
        result = self.analyze(image, analysis_id=analysis_id)
        if any(leaf.ood is not None and leaf.ood.is_ood for leaf in result.leaves):
            raise InferenceError(
                InferenceErrorCode.OUT_OF_DISTRIBUTION,
                "The legacy response contract cannot represent classifier output together with OOD status",
                stage="ood_detection",
            )
        leaf_results = []
        for leaf in result.leaves:
            y0, x0, y1, x1 = leaf.bounding_box
            if leaf.segmentation and leaf.segmentation.disease_bounding_box:
                dy0, dx0, dy1, dx1 = leaf.segmentation.disease_bounding_box
                disease_bbox = [dx0, dy0, dx1 - dx0, dy1 - dy0]
            else:
                disease_bbox = [0.0, 0.0, 0.0, 0.0]
            severity = leaf.severity
            severity_available = bool(
                severity and severity.status == "available" and severity.score is not None
                and severity.affected_percentage is not None and severity.level is not None
            )
            level = None
            if severity_available:
                if severity.level == ModelSeverityLevel.HEALTHY:
                    level = SeverityLevel.HEALTHY
                elif severity.level == ModelSeverityLevel.LOW:
                    level = SeverityLevel.LOW
                elif severity.level == ModelSeverityLevel.MEDIUM:
                    level = SeverityLevel.MEDIUM
                elif severity.level == ModelSeverityLevel.HIGH:
                    level = SeverityLevel.HIGH
            leaf_results.append(LeafResult(
                leaf_index=leaf.leaf_id,
                bounding_box=[x0, y0, x1 - x0, y1 - y0],
                disease_class=leaf.classification.primary_class if leaf.classification else "",
                classification_confidence=leaf.classification.confidence if leaf.classification else 0.0,
                all_probabilities=leaf.classification.top_k_probabilities if leaf.classification else None,
                disease_mask=None,
                diseased_area_ratio=leaf.segmentation.diseased_ratio if leaf.segmentation else 0.0,
                disease_bounding_box=disease_bbox,
                severity_status="available" if severity_available else "unavailable",
                severity_score=severity.score if severity_available else None,
                severity_level=level,
                affected_percentage=severity.affected_percentage if severity_available else None,
                leaf_confidence=leaf.leaf_filter_confidence,
                explainability_heatmap=None,
            ))

        model_summary = result.plant_summary
        if model_summary.health_status.value == "healthy":
            health_status = HealthStatus.GOOD
        elif model_summary.health_status.value == "severely_diseased":
            health_status = HealthStatus.POOR
        elif model_summary.health_status.value == "unknown":
            health_status = HealthStatus.FAIR
        else:
            health_status = HealthStatus.FAIR
        summary = PlantHealthSummary(
            overall_health_score=model_summary.overall_health_score or 0.0,
            health_status=health_status,
            healthy_leaf_count=model_summary.healthy_leaves_count,
            total_leaf_count=model_summary.valid_leaves_analyzed,
            disease_summary=model_summary.disease_breakdown,
            risk_assessment=model_summary.health_status.value,
            recommendations=model_summary.recommendations,
        )
        return PlantAnalysisResponse(
            analysis_id=result.analysis_id,
            timestamp=result.timestamp,
            status=result.status,
            leaf_results=leaf_results,
            plant_health_summary=summary,
            processing_time_ms=result.processing_time_ms,
            ml_mode=f"real_models_{result.hardware_device}",
        )

    def analyze_video_frame(
        self,
        frame: np.ndarray,
        prev_leaf_results: Optional[List[Dict[str, Any]]] = None,
        analysis_id: Optional[str] = None,
    ) -> PlantAnalysisResponse:
        raise InferenceError(
            InferenceErrorCode.UNSUPPORTED_RUNTIME,
            "Video tracking is not implemented",
            stage="video"
        )


def create_plant_analysis_service(
    inference: ModelInferenceService | RemoteInferenceClient | None = None,
    storage: ObjectStorage | None = None,
    **kwargs: Any,
) -> ApplicationPlantAnalysisService:
    """
    Factory for the application-level plant analysis service supporting dependency injection.
    """
    if inference is not None:
        return ApplicationPlantAnalysisService(inference=inference, storage=storage)
    if settings.PLANTGUARD_INFERENCE_PROFILE == "remote":
        if kwargs:
            raise ValueError("Device-specific kwargs cannot be passed to the configured remote inference profile")
        return ApplicationPlantAnalysisService(
            inference=RemoteInferenceClient.from_settings(),
            storage=storage,
        )
    return ApplicationPlantAnalysisService(
        inference=ModelInferenceService(storage=storage, **kwargs),
        storage=storage,
    )
