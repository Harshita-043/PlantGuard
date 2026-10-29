"""
Versioned, typed Pydantic contracts for PlantGuard AI ML inference.

Design principles:
1. Mask binary data (PNG/WebP) are referenced via MaskAsset pointers (storage keys, URLs, dimensions),
   never serializing raw 2D pixel grids directly into JSON.
2. Structured representations for OOD, classification with probabilities, segmentation geometry,
   severity metrics, pipeline warnings, and partial failures.
3. Backward-compatible conversion to legacy PlantAnalysisResponse when requested.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class SeverityLevel(str, Enum):
    HEALTHY = "healthy"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OverallHealthStatus(str, Enum):
    HEALTHY = "healthy"
    MILDLY_DISEASED = "mildly_diseased"
    SEVERELY_DISEASED = "severely_diseased"
    UNKNOWN = "unknown"


class WarningSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class PipelineWarning(BaseModel):
    """Non-fatal notice emitted during the inference lifecycle."""
    model_config = ConfigDict(frozen=True)

    code: str = Field(..., description="Machine-readable error/warning code (e.g. LOW_LEAF_CONFIDENCE)")
    message: str = Field(..., description="Human-readable warning explanation")
    component: str = Field(..., description="Name of the component originating the warning")
    severity: WarningSeverity = Field(default=WarningSeverity.WARNING, description="Notice severity level")


class PartialFailure(BaseModel):
    """Explicit report of a degraded or failed subsystem in the pipeline."""
    model_config = ConfigDict(frozen=True)

    component: str = Field(..., description="Pipeline component that failed (e.g. segmentation, classifier)")
    error_type: str = Field(..., description="Category or class name of the error")
    message: str = Field(..., description="Diagnostic detail for debugging")
    fallback_applied: bool = Field(default=False, description="Whether a graceful fallback or heuristic was applied")


class MaskAsset(BaseModel):
    """Pointer to a mask asset stored in object storage or local disk."""
    model_config = ConfigDict(frozen=True)

    storage_key: str = Field(..., description="Object key or relative storage path for the mask binary")
    content_type: str = Field(default="image/png", description="MIME content type of the mask asset")
    width: int = Field(..., gt=0, description="Pixel width of the mask")
    height: int = Field(..., gt=0, description="Pixel height of the mask")
    byte_size: Optional[int] = Field(None, ge=0, description="Size of the stored mask binary in bytes")
    download_url: Optional[str] = Field(None, description="Pre-signed or public URL to download the mask asset")


class ClassificationResult(BaseModel):
    """Output from the disease classification model (e.g. DINOv2 Base 38-class)."""
    model_config = ConfigDict(frozen=True)

    primary_class: str = Field(..., description="Predicted primary class name (e.g. Tomato___Late_blight)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for the primary class (0-1)")
    is_healthy: bool = Field(..., description="True if the primary class denotes a healthy specimen")
    crop_type: Optional[str] = Field(None, description="Parsed crop name (e.g. Tomato, Apple)")
    disease_name: Optional[str] = Field(None, description="Parsed disease name (e.g. Late_blight, healthy)")
    top_k_probabilities: Dict[str, float] = Field(
        default_factory=dict,
        description="Top-k class names and their respective softmax probabilities"
    )


class OODResult(BaseModel):
    """Out-of-Distribution (OOD) detection result for anomalous or non-plant inputs."""
    model_config = ConfigDict(frozen=True)

    score: float = Field(..., description="Normalized prediction uncertainty score")
    threshold: float = Field(..., description="Provisional configured decision boundary")
    is_ood: bool = Field(..., description="Provisional flag; not a validated OOD decision")
    method: str = Field(default="entropy_threshold", description="Uncertainty summary method")
    status: Literal[
        "ood_detected",
        "ood_not_detected",
        "ood_unavailable",
        "ood_unvalidated",
    ] = "ood_unvalidated"
    classification_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    calibration_status: str = Field(default="incomplete", description="Calibration dataset has not been evaluated")


class PredictionUncertainty(BaseModel):
    """Provisional classification uncertainty, distinct from an OOD decision."""
    model_config = ConfigDict(frozen=True)

    score: float = Field(..., ge=0.0, le=1.0, description="Normalized Shannon entropy")
    threshold: float = Field(..., ge=0.0, le=1.0, description="Configured provisional warning threshold")
    is_high_uncertainty: bool
    classification_confidence: float = Field(..., ge=0.0, le=1.0)
    method: str = "normalized_shannon_entropy"
    calibration_status: str = "incomplete"


class SegmentationResult(BaseModel):
    """Lesion semantic segmentation result (e.g. SegFormer-B0)."""
    model_config = ConfigDict(frozen=True)

    has_lesions: bool = Field(..., description="True if diseased lesions were detected")
    diseased_pixels: int = Field(..., ge=0, description="Number of pixels predicted as diseased")
    total_leaf_pixels: int = Field(..., ge=0, description="Total pixels in the analyzed leaf mask")
    diseased_ratio: float = Field(..., ge=0.0, le=1.0, description="Ratio of diseased pixels to leaf pixels")
    mask_asset: Optional[MaskAsset] = Field(None, description="Stored mask asset reference")
    disease_bounding_box: Optional[List[float]] = Field(
        None,
        min_length=4,
        max_length=4,
        description="Normalized bounding box of diseased lesions [ymin, xmin, ymax, xmax]"
    )


class SeverityResult(BaseModel):
    """Mask-derived quantitative severity estimation."""
    model_config = ConfigDict(frozen=True)

    status: str = Field(default="available", description="available or unavailable")
    method: str = Field(default="leaf_intersection_pixel_ratio")
    score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Affected fraction when available")
    level: Optional[SeverityLevel] = Field(None, description="Provisional threshold category")
    affected_percentage: Optional[float] = Field(None, ge=0.0, le=100.0, description="Percentage of valid leaf pixels affected")
    diseased_leaf_pixels: Optional[int] = Field(None, ge=0)
    valid_leaf_pixels: Optional[int] = Field(None, ge=0)
    thresholds_validated: bool = False
    lesion_count: Optional[int] = Field(None, ge=0, description="Estimated count of distinct disease lesions")
    assessment: str = Field(..., description="Summary statement of severity impact")


class ExplainabilityResult(BaseModel):
    """Attention map or gradient-based explainability visual artifact."""
    model_config = ConfigDict(frozen=True)

    status: str = Field(default="available", description="available or unavailable")
    method: str = Field(..., description="Architecture-compatible visualization method")
    heatmap_asset: Optional[MaskAsset] = Field(None, description="Stored normalized heatmap asset")
    description: Optional[str] = Field(None, description="Interpretation guide for the visual overlay")


class SingleLeafAnalysis(BaseModel):
    """Consolidated assessment for a single leaf instance."""
    leaf_id: int = Field(..., ge=0, description="Instance index of the leaf")
    bounding_box: List[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Normalized bounding box of the leaf [ymin, xmin, ymax, xmax]"
    )
    leaf_mask_asset: Optional[MaskAsset] = Field(None, description="Stored instance mask for this leaf")
    leaf_crop_asset: Optional[MaskAsset] = Field(None, description="Stored crop image for this leaf")
    lesion_overlay_asset: Optional[MaskAsset] = Field(None, description="Stored lesion overlay on leaf crop")
    attention_overlay_asset: Optional[MaskAsset] = Field(None, description="Stored attention overlay on leaf crop")
    is_leaf: bool = Field(default=True, description="Whether candidate passed the leaf filter")
    leaf_filter_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence that candidate is a leaf")
    candidate_score: float = Field(default=0.0, ge=0.0, le=1.0, description="SAM proposal ranking score")
    candidate_source: str = Field(default="sam2.1_automatic_mask_generator")
    classification: Optional[ClassificationResult] = Field(None, description="Disease classification output")
    ood: Optional[OODResult] = Field(None, description="OOD evaluation")
    segmentation: Optional[SegmentationResult] = Field(None, description="Disease lesion segmentation output")
    severity: Optional[SeverityResult] = Field(None, description="Quantitative severity assessment")
    explainability: Optional[ExplainabilityResult] = Field(None, description="Visual explanation")
    prediction_uncertainty: Optional[PredictionUncertainty] = Field(None, description="Uncalibrated entropy/confidence signal")
    warnings: List[PipelineWarning] = Field(default_factory=list, description="Per-leaf warnings")


class PlantHealthSummary(BaseModel):
    """High-level summary aggregated across all leaves in the scan."""
    overall_health_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Descriptive score derived from measured mask severity; null when unavailable")
    health_status: OverallHealthStatus = Field(..., description="Overall health state category")
    total_leaves_detected: int = Field(..., ge=0, description="Count of candidate leaves detected")
    valid_leaves_analyzed: int = Field(..., ge=0, description="Count of leaves passing leaf verification")
    healthy_leaves_count: int = Field(..., ge=0, description="Count of leaves assessed as healthy")
    diseased_leaves_count: int = Field(..., ge=0, description="Count of leaves assessed with disease")
    primary_diagnosis: Optional[str] = Field(None, description="Dominant disease diagnosed across the plant")
    disease_breakdown: Dict[str, int] = Field(default_factory=dict, description="Frequency count of diagnosed diseases")
    average_severity_percentage: Optional[float] = Field(None, ge=0.0, le=100.0, description="Mean measured leaf area affected; null when masks are unavailable")
    recommendations: List[str] = Field(default_factory=list, description="Agronomic care and treatment guidance")


# Backward-compatible alias
AggregatedPlantHealth = PlantHealthSummary


class FullScanResult(BaseModel):
    """Complete, versioned response returned by the PlantGuard AI pipeline."""
    schema_version: str = Field(default="2.0.0", description="Contract schema version")
    analysis_id: str = Field(..., description="Unique UUID for this analysis execution")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of completion"
    )
    status: str = Field(..., description="Execution status: completed, partial, or failed")
    hardware_device: str = Field(..., description="Compute hardware utilized (e.g. cpu, cuda:0, openvino)")
    processing_time_ms: int = Field(..., ge=0, description="Total pipeline execution duration in milliseconds")
    model_versions: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of active model component names to their artifact versions"
    )
    sam_variant: str = Field(default="unknown", description="Leaf proposal model adapter used for this scan")
    sam_fallback_applied: bool = Field(
        default=False,
        description="Whether MobileSAM was used after SAM 2 could not generate candidates",
    )
    stage_timings_ms: Dict[str, int] = Field(default_factory=dict, description="Per-stage elapsed time in milliseconds")
    model_load_timings_ms: Dict[str, int] = Field(default_factory=dict, description="Lazy per-model checkpoint load time in milliseconds")
    leaves: List[SingleLeafAnalysis] = Field(default_factory=list, description="Individual leaf assessments")
    plant_summary: PlantHealthSummary = Field(..., description="Plant-level aggregated health summary")
    warnings: List[PipelineWarning] = Field(default_factory=list, description="Global pipeline warnings")
    partial_failures: List[PartialFailure] = Field(default_factory=list, description="Degraded or failed subsystems")
