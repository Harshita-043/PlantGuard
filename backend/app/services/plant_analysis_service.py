"""Adapter from the legacy application service contract to typed model inference."""

from typing import Any, Dict, List, Optional
import importlib.util
from pathlib import Path

import numpy as np

from app.ml.errors import InferenceError, InferenceErrorCode
from app.ml.service import PlantAnalysisService as ModelInferenceService
from app.ml.remote import RemoteInferenceClient, probe_remote_health
from app.core.config import settings
from app.schemas.inference import SeverityLevel as ModelSeverityLevel
from app.schemas.plant_analysis import (
    HealthStatus,
    LeafResult,
    PlantAnalysisResponse,
    PlantHealthSummary,
    SeverityLevel,
)
from app.services.interfaces.plant_analysis import PlantAnalysisService


class ApplicationPlantAnalysisService(PlantAnalysisService):
    """Concrete legacy-contract adapter; model weights remain lazily loaded."""

    def __init__(self, inference: ModelInferenceService | None = None):
        if inference is not None:
            self.inference = inference
        elif settings.PLANTGUARD_INFERENCE_PROFILE == "remote":
            self.inference = RemoteInferenceClient.from_settings()
        else:
            device = {"cpu": "cpu", "cuda": "cuda:0"}.get(settings.PLANTGUARD_INFERENCE_PROFILE)
            self.inference = ModelInferenceService(device=device)

    def initialize(self) -> None:
        # Loading is per-inference and sequential to keep peak memory bounded.
        return None

    def is_ready(self) -> bool:
        # We report prerequisites only; weights still load lazily at call time.
        if isinstance(self.inference, RemoteInferenceClient):
            token = settings.PLANTGUARD_REMOTE_INFERENCE_TOKEN
            return bool(token and probe_remote_health(settings.PLANTGUARD_REMOTE_INFERENCE_URL or "",
                                                      token.get_secret_value()))
        adapters = (
            self.inference.sam, self.inference.leaf_filter, self.inference.classifier, self.inference.segmenter
        )
        if not all(adapter.artifact_path.is_file() for adapter in adapters):
            return False
        if not all(importlib.util.find_spec(name) is not None for name in ("torch", "transformers", "sam2")):
            return False
        package_root = Path(importlib.util.find_spec("sam2").origin).resolve().parent.parent
        if not (package_root / self.inference.sam.config_name).is_file():
            return False
        return self.inference.segmenter._configuration_error is None and len(self.inference.classifier.get_class_mapping() or {}) == 38

    def get_service_name(self) -> str:
        return "PlantGuardModelInference"

    def analyze_image(self, image: np.ndarray, analysis_id: Optional[str] = None) -> PlantAnalysisResponse:
        result = self.inference.analyze(image, analysis_id=analysis_id)
        leaf_results = []
        for leaf in result.leaves:
            y0, x0, y1, x1 = leaf.bounding_box
            if leaf.segmentation and leaf.segmentation.disease_bounding_box:
                dy0, dx0, dy1, dx1 = leaf.segmentation.disease_bounding_box
                disease_bbox = [dx0, dy0, dx1 - dx0, dy1 - dy0]
            else:
                disease_bbox = [0.0, 0.0, 0.0, 0.0]
            severity = leaf.severity
            severity_available = bool(severity and severity.status == "available" and severity.score is not None
                                      and severity.affected_percentage is not None and severity.level is not None)
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
            overall_health_score=model_summary.overall_health_score,
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
        raise InferenceError(InferenceErrorCode.UNSUPPORTED_RUNTIME,
                             "Video tracking is not implemented", stage="video")


def create_plant_analysis_service(**kwargs) -> ApplicationPlantAnalysisService:
    """Create a lazy inference service; required model failures are reported per request."""
    if settings.PLANTGUARD_INFERENCE_PROFILE == "remote":
        if kwargs:
            raise ValueError("Device-specific kwargs cannot be passed to the configured remote inference profile")
        return ApplicationPlantAnalysisService(RemoteInferenceClient.from_settings())
    return ApplicationPlantAnalysisService(ModelInferenceService(**kwargs))
