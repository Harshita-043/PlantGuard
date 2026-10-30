"""Lazy, sequential PlantGuard inference orchestration."""

from __future__ import annotations

import io
import logging
import math
import os
import threading
import time
from pathlib import Path
from typing import Callable, Iterable
from uuid import uuid4

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.ml.adapters.disease_classifier import DinoDiseaseClassifierAdapter
from app.ml.adapters.disease_segmentation import SegFormerDiseaseSegmentationAdapter
from app.ml.adapters.leaf_filter import DinoLeafFilterAdapter
from app.ml.adapters.mobile_sam_adapter import MobileSamLeafSegmentationAdapter
from app.ml.adapters.sam_adapter import Sam2LeafSegmentationAdapter
from app.ml.contracts import (
    DiseasePrediction,
    LeafCandidate,
    LeafFilterScore,
    SegmentationPrediction,
    StageMetadata,
    StageOutput,
)
from app.ml.device import device_manager
from app.ml.errors import (
    InferenceError,
    InferenceErrorCode,
    InferenceTimeoutError,
    InvalidImageError,
    ModelCapabilityError,
    NoDiseaseMaskError,
    NoLeafFoundError,
)
from app.ml.registry import model_registry
from app.ml.ood import OODDetector
from app.ml.runtime import RuntimeCapabilities, collect_runtime_capabilities
from app.ml.variants import MODEL_IDS, ModelVariantRegistry
from app.ml.severity import SeverityEstimator
from app.core.config import settings
from app.schemas.inference import (
    CandidateStageCounts,
    ClassificationResult,
    ExplainabilityResult,
    FullScanResult,
    MaskAsset,
    OverallHealthStatus,
    PartialFailure,
    PipelineWarning,
    PlantHealthSummary,
    PredictionUncertainty,
    SegmentationResult,
    SeverityResult,
    SeverityLevel,
    SingleLeafAnalysis,
    WarningSeverity,
)
from app.storage.errors import StorageError
from app.storage.interface import ObjectStorage

logger = logging.getLogger(__name__)
_GLOBAL_INFERENCE_SLOT = threading.BoundedSemaphore(settings.PLANTGUARD_MAX_CONCURRENCY)

MAX_IMAGE_SIDE = 8192
MAX_IMAGE_PIXELS = 32_000_000
MAX_CANDIDATES = 8


class PlantAnalysisService:
    """Model-agnostic application boundary backed by sequential model adapters.

    The default model set is created lazily, and only one model is resident at a
    time. A single bounded slot protects the host from overlapping large loads.
    Tests and alternate runtimes can inject adapter implementations.
    """

    def __init__(
        self,
        *,
        sam=None,
        mobile_sam=None,
        leaf_filter=None,
        classifier=None,
        segmenter=None,
        storage: ObjectStorage | None = None,
        ood_detector: OODDetector | None = None,
        device: str | None = None,
        timeout_seconds: float | None = None,
        candidate_limit: int | None = None,
        variant_preference: str = "automatic",
    ):
        self.sam = sam if sam is not None else Sam2LeafSegmentationAdapter()
        self.mobile_sam = mobile_sam if mobile_sam is not None else MobileSamLeafSegmentationAdapter()
        self.leaf_filter = leaf_filter if leaf_filter is not None else DinoLeafFilterAdapter()
        self.classifier = classifier if classifier is not None else DinoDiseaseClassifierAdapter()
        self.segmenter = segmenter if segmenter is not None else SegFormerDiseaseSegmentationAdapter()
        model_registry.register_adapter("leaf_filter", self.leaf_filter)
        model_registry.register_adapter("disease_classifier", self.classifier)
        model_registry.register_adapter("disease_segmentation", self.segmenter)
        model_registry.register_adapter("leaf_instance_segmentation", self.sam)
        model_registry.register_adapter("mobile_sam_instance_segmentation", self.mobile_sam)
        self.storage = storage
        self.ood_detector = ood_detector or OODDetector()
        self.device = device or device_manager.active_device
        configured_profile = settings.PLANTGUARD_INFERENCE_PROFILE
        if configured_profile == "cpu":
            self.device = "cpu"
        elif configured_profile == "cuda":
            self.device = "cuda:0"
        self.profile = ("cuda" if self.device.startswith("cuda") else "cpu") if configured_profile == "auto" else configured_profile
        if self.profile == "remote":
            raise ModelCapabilityError(InferenceErrorCode.UNSUPPORTED_RUNTIME,
                                       "Remote profile must use the configured RemoteInferenceClient", stage="runtime")
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else float(
            os.getenv("PLANTGUARD_INFERENCE_TIMEOUT_SECONDS", "120")
        )
        self.candidate_limit = candidate_limit if candidate_limit is not None else int(
            os.getenv("PLANTGUARD_MAX_CANDIDATES", str(MAX_CANDIDATES))
        )
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("Inference timeout must be a positive finite number")
        if self.candidate_limit < 1 or self.candidate_limit > 32:
            raise ValueError("Maximum leaf candidates must be between 1 and 32")
        if variant_preference not in {"automatic", "original"}:
            raise ValueError("Variant preference must be automatic or original")
        self.variant_preference = variant_preference
        self._inference_slot = _GLOBAL_INFERENCE_SLOT
        self._variant_registry: ModelVariantRegistry | None = None
        self._runtime_capabilities: RuntimeCapabilities | None = None
        if not (self.device in {"cpu", "mps"} or self.device.startswith("cuda")):
            raise ModelCapabilityError(InferenceErrorCode.UNSUPPORTED_RUNTIME,
                                       f"Model adapters do not support runtime '{self.device}'", stage="runtime")

    def analyze_bytes(self, image_bytes: bytes, *, analysis_id: str | None = None) -> FullScanResult:
        try:
            with Image.open(io.BytesIO(image_bytes)) as im:
                if im.width <= 0 or im.height <= 0 or im.width > MAX_IMAGE_SIDE or im.height > MAX_IMAGE_SIDE:
                    raise InvalidImageError("Image dimensions exceed the supported limit")
                if im.width * im.height > MAX_IMAGE_PIXELS:
                    raise InvalidImageError("Image pixel count exceeds the supported limit")
                oriented = ImageOps.exif_transpose(im)
                image = np.asarray(oriented.convert("RGB"), dtype=np.uint8)
        except InvalidImageError:
            raise
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            raise InvalidImageError("Image is corrupt or cannot be decoded") from exc
        return self.analyze(image, analysis_id=analysis_id)

    def analyze(self, image: np.ndarray, *, analysis_id: str | None = None) -> FullScanResult:
        self._validate_image(image)
        image = np.array(image, dtype=np.uint8, order="C", copy=True)
        if not self._inference_slot.acquire(timeout=self.timeout_seconds):
            raise InferenceTimeoutError()

        scan_id = analysis_id or str(uuid4())
        started = time.perf_counter()
        timings: dict[str, int] = {}
        self.model_load_timings_ms: dict[str, int] = {}
        warnings: list[PipelineWarning] = []
        leaves: list[SingleLeafAnalysis] = []
        try:
            candidate_output = self._sam_candidates(image, timings)
            candidates = candidate_output.value
            if not candidates:
                raise NoLeafFoundError()
            sam_fallback_applied = self._selected_sam_adapter is self.mobile_sam
            if sam_fallback_applied:
                warnings.append(PipelineWarning(
                    code="MODEL_FALLBACK_APPLIED",
                    message="SAM 2 was unavailable; MobileSAM generated the leaf candidates.",
                    component="leaf_proposal",
                    severity=WarningSeverity.WARNING,
                ))

            # Candidate filtering. A candidate's segmentation is always the SAM mask.
            accepted: list[tuple[LeafCandidate, np.ndarray, LeafFilterScore]] = []
            t0 = time.perf_counter()
            def filter_candidates(adapter):
                for candidate in candidates:
                    crop, leaf_mask, bbox = self._crop_candidate(image, candidate)
                    model_input = self._validated_input(adapter.preprocess(crop), (1, 3, 224, 224), "leaf_filter")
                    probs = self._probabilities(adapter.predict(model_input), 2, "leaf_filter")
                    confidence = float(probs[0, 1])
                    score = LeafFilterScore(confidence=confidence, accepted=confidence >= 0.5,
                                             model_version=adapter.artifact_version)
                    if score.accepted:
                        accepted.append((candidate, crop, score))
            self._with_model(self.leaf_filter, "leaf_filter", filter_candidates)
            self._candidate_counts["leaf_filter_accepted"] = len(accepted)
            timings["leaf_filter"] = self._elapsed(t0)
            logger.info("inference_stage_complete stage=leaf_filter candidates=%d accepted=%d runtime=%s model=%s duration_ms=%d",
                        len(candidates), len(accepted), self.device, self.leaf_filter.artifact_version, timings["leaf_filter"])
            if not accepted:
                raise NoLeafFoundError("SAM2 candidates did not pass the DINOv2 ViT-S/14 leaf filter")

            # DINOv2 ViT-B/14 classifies only accepted leaf crops.
            predictions: list[tuple[tuple[LeafCandidate, np.ndarray, LeafFilterScore], DiseasePrediction, np.ndarray | None, np.ndarray | None]] = []
            t0 = time.perf_counter()
            def classify(adapter):
                class_map = adapter.get_class_mapping() or {}
                if len(class_map) != 38 or set(class_map) != set(range(38)) or len(set(class_map.values())) != 38:
                    raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                         "Disease classifier must expose the ordered 38-class mapping", stage="classifier")
                for accepted_item in accepted:
                    crop = accepted_item[1]
                    model_input = self._validated_input(adapter.preprocess(crop), (1, 3, 224, 224), "classifier")
                    attention = None
                    features = None
                    if hasattr(adapter, "predict_with_attention"):
                        try:
                            res = adapter.predict_with_attention(model_input, return_features=True)
                            if isinstance(res, tuple) and len(res) == 3:
                                probs, attention, features = res
                            else:
                                probs, attention = res
                        except (RuntimeError, TypeError, ValueError) as exc:
                            if hasattr(adapter, "predict_with_features"):
                                probs, features = adapter.predict_with_features(model_input)
                            else:
                                probs = adapter.predict(model_input)
                            logger.warning("inference_stage_unavailable stage=explainability runtime=%s model=%s error_code=explanation_unavailable error_type=%s",
                                           self.device, adapter.artifact_version, type(exc).__name__)
                    else:
                        probs = adapter.predict(model_input)
                    distribution = self._probabilities(probs, 38, "classifier")
                    class_index = int(np.argmax(distribution[0]))
                    class_name = class_map[class_index]
                    prediction = DiseasePrediction(
                        class_index=class_index,
                        class_name=class_name,
                        confidence=float(distribution[0, class_index]),
                        probabilities=tuple(float(p) for p in distribution[0]),
                        model_version=adapter.artifact_version,
                    )
                    predictions.append((accepted_item, prediction, attention, features))
            self._with_model(self.classifier, "classifier", classify)
            self._candidate_counts["disease_analysis_eligible"] = len(predictions)
            timings["classifier"] = self._elapsed(t0)
            logger.info("inference_stage_complete stage=classifier leaves=%d runtime=%s model=%s duration_ms=%d",
                        len(predictions), self.device, self.classifier.artifact_version, timings["classifier"])

            # SegFormer-B0 PlantSeg masks are decoded at each crop's original dimensions.
            segmented: list[SingleLeafAnalysis] = []
            t0 = time.perf_counter()
            def segment(adapter):
                mapping = adapter.get_class_mapping() or {}
                if mapping != {0: "background", 1: "diseased_region"}:
                    raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                         "SegFormer label mapping does not match the PlantSeg checkpoint", stage="segmentation")
                for idx, (accepted_item, prediction, attention, features) in enumerate(predictions):
                    candidate, crop, filter_score = accepted_item
                    leaf_confidence = filter_score.confidence
                    model_input = self._validated_input(adapter.preprocess(crop), (1, 3, 512, 512), "segmentation")
                    raw_mask = adapter.predict(model_input, original_shape=crop.shape[:2])
                    if raw_mask is None:
                        raise NoDiseaseMaskError("SegFormer returned no mask")
                    disease_mask = np.asarray(raw_mask)
                    if disease_mask.shape != crop.shape[:2] or disease_mask.ndim != 2:
                        raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                             "SegFormer mask dimensions do not match the leaf crop", stage="segmentation")
                    if not np.issubdtype(disease_mask.dtype, np.integer) and disease_mask.dtype != np.bool_:
                        raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                             "SegFormer mask must contain integer class IDs", stage="segmentation")
                    if not np.isin(disease_mask, [0, 1]).all():
                        raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                             "SegFormer emitted a class ID outside the configured PlantSeg mapping", stage="segmentation")
                    _, leaf_mask, bbox = self._crop_candidate(image, candidate)
                    if leaf_mask.shape != disease_mask.shape:
                        from PIL import Image as PILImage
                        leaf_mask = np.asarray(PILImage.fromarray(leaf_mask.astype(np.uint8) * 255).resize(
                            (disease_mask.shape[1], disease_mask.shape[0]), PILImage.Resampling.NEAREST
                        )) > 0
                    segmentation_prediction = SegmentationPrediction(
                        class_mask=disease_mask,
                        label_mapping=dict(mapping),
                        model_version=adapter.artifact_version,
                    )
                    disease_mask = ((segmentation_prediction.class_mask == 1) & leaf_mask).astype(np.uint8)
                    if not np.any(leaf_mask):
                        raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                             "SAM2 leaf mask became empty after crop alignment", stage="segmentation")

                    class_map = self.classifier.get_class_mapping()
                    probs = np.asarray([prediction.probabilities], dtype=np.float32)
                    primary = prediction.class_name
                    top_ids = np.argsort(probs[0])[::-1][:5]
                    top_k = {class_map[int(i)]: round(float(probs[0, i]), 4) for i in top_ids}
                    crop_name, _, disease_name = primary.partition("___")
                    classification = ClassificationResult(
                        primary_class=primary,
                        confidence=prediction.confidence,
                        is_healthy="healthy" in primary.lower(),
                        crop_type=crop_name,
                        disease_name=disease_name.replace("_", " "),
                        top_k_probabilities=top_k,
                    )
                    entropy_signal = self.ood_detector.evaluate_probabilities(probs[0])
                    uncertainty = PredictionUncertainty(
                        score=entropy_signal.score,
                        threshold=entropy_signal.threshold,
                        is_high_uncertainty=entropy_signal.score > entropy_signal.threshold,
                        classification_confidence=classification.confidence,
                        method="normalized_shannon_entropy",
                        calibration_status="incomplete",
                    )

                    crop_asset = self._persist_rgb_image(crop, scan_id, f"leaf_{idx}_crop.png")
                    mask_asset = self._persist_mask(disease_mask, scan_id, f"leaf_{idx}_disease_mask.png")
                    leaf_asset = self._persist_mask(leaf_mask.astype(np.uint8), scan_id, f"leaf_{idx}_leaf_mask.png")

                    # Generate lesion overlay onto crop
                    lesion_overlay = crop.copy()
                    if np.any(disease_mask):
                        lesion_overlay[disease_mask == 1] = (
                            0.45 * lesion_overlay[disease_mask == 1] + 0.55 * np.array([230, 50, 50], dtype=np.uint8)
                        ).astype(np.uint8)
                    lesion_overlay_asset = self._persist_rgb_image(lesion_overlay, scan_id, f"leaf_{idx}_lesion_overlay.png")

                    diseased_pixels = int(np.count_nonzero(disease_mask))
                    total_leaf_pixels = int(np.count_nonzero(leaf_mask))
                    seg_result = SegmentationResult(
                        has_lesions=diseased_pixels > 0,
                        diseased_pixels=diseased_pixels,
                        total_leaf_pixels=total_leaf_pixels,
                        diseased_ratio=diseased_pixels / total_leaf_pixels,
                        mask_asset=mask_asset,
                        disease_bounding_box=SeverityEstimator.compute_disease_bounding_box(disease_mask),
                    )
                    severity = SeverityEstimator.estimate_severity(disease_mask, leaf_mask)
                    attn_overlay_asset = None
                    artifact_warnings: list[PipelineWarning] = []
                    if attention is not None:
                        try:
                            explanation = self._persist_attention(attention, crop.shape[:2], scan_id, idx)
                        except InferenceError as exc:
                            logger.warning(
                                "inference_stage_unavailable stage=explainability error_code=%s",
                                exc.code.value,
                            )
                            explanation = ExplainabilityResult(
                                status="unavailable",
                                method="dinov2_attention_rollout",
                                description="Attribution could not be generated or saved.",
                            )
                            if exc.code == InferenceErrorCode.ARTIFACT_STORAGE_FAILURE:
                                artifact_warnings.append(PipelineWarning(
                                    code="OPTIONAL_ARTIFACT_STORAGE_FAILURE",
                                    message="The attention visualization could not be saved.",
                                    component="artifact_storage",
                                    severity=WarningSeverity.WARNING,
                                ))
                        except (ValueError, TypeError, OSError) as exc:
                            logger.warning(
                                "inference_stage_unavailable stage=explainability error_type=%s",
                                type(exc).__name__,
                            )
                            explanation = ExplainabilityResult(
                                status="unavailable",
                                method="dinov2_attention_rollout",
                                description="Attribution could not be generated or saved.",
                            )
                        if explanation.status == "available":
                            norm_attn = np.clip(attention, 0.0, 1.0)
                            resized_attn = np.asarray(Image.fromarray((norm_attn * 255).astype(np.uint8)).resize(
                                (crop.shape[1], crop.shape[0]), Image.Resampling.BILINEAR
                            ))
                            colored_attn = self._apply_colormap(resized_attn)
                            attn_overlay = (0.5 * crop + 0.5 * colored_attn).astype(np.uint8)
                            try:
                                attn_overlay_asset = self._persist_rgb_image(
                                    attn_overlay,
                                    scan_id,
                                    f"leaf_{idx}_attention_overlay.png",
                                )
                            except InferenceError as exc:
                                if exc.code != InferenceErrorCode.ARTIFACT_STORAGE_FAILURE:
                                    raise
                                logger.warning(
                                    "inference_stage_unavailable stage=attention_overlay error_code=%s",
                                    exc.code.value,
                                )
                                artifact_warnings.append(PipelineWarning(
                                    code="OPTIONAL_ARTIFACT_STORAGE_FAILURE",
                                    message="The attention overlay could not be saved.",
                                    component="artifact_storage",
                                    severity=WarningSeverity.WARNING,
                                ))
                    else:
                        explanation = ExplainabilityResult(status="unavailable", method="dinov2_attention_rollout",
                                                           description="Classifier adapter did not provide an attribution map.")

                    # Evaluate class-conditional Mahalanobis OOD
                    ood_started = time.perf_counter()
                    ood_result = self.ood_detector.evaluate_features(
                        features,
                        prediction.class_index,
                        confidence=prediction.confidence,
                    )
                    timings["ood_detection"] = timings.get("ood_detection", 0) + self._elapsed(ood_started)

                    leaf_warnings: list[PipelineWarning] = [PipelineWarning(
                        code="RELIABILITY_UNCALIBRATED",
                        message=f"Classification confidence is {classification.confidence:.3f}; provisional normalized entropy is {uncertainty.score:.3f} (threshold {uncertainty.threshold:.3f}).",
                        component="reliability",
                        severity=WarningSeverity.WARNING,
                    ), PipelineWarning(
                        code="SEVERITY_THRESHOLDS_UNVALIDATED",
                        message="Severity percentages use provisional thresholds and require agronomic validation.",
                        component="severity",
                        severity=WarningSeverity.WARNING,
                    )]
                    leaf_warnings.extend(artifact_warnings)
                    if classification.confidence < OODDetector.DEFAULT_MIN_CONFIDENCE:
                        leaf_warnings.append(PipelineWarning(
                            code="LOW_CLASSIFICATION_CONFIDENCE",
                            message="Predicted class confidence is below the configured provisional threshold.",
                            component="reliability", severity=WarningSeverity.WARNING,
                        ))
                    if uncertainty.is_high_uncertainty:
                        leaf_warnings.append(PipelineWarning(
                            code="HIGH_PREDICTION_UNCERTAINTY",
                            message="The classifier output is diffuse across classes. Prediction may be ambiguous.",
                            component="reliability", severity=WarningSeverity.WARNING,
                        ))
                    if ood_result.status == "ood_unvalidated" and ood_result.is_ood:
                        leaf_warnings.append(PipelineWarning(
                            code="OOD_FLAGGED_UNVALIDATED",
                            message=f"The unvalidated Mahalanobis threshold was exceeded (distance {ood_result.score:.1f} > threshold {ood_result.threshold:.1f}); the classifier prediction is retained as an unverified candidate and flagged for review.",
                            component="reliability", severity=WarningSeverity.WARNING,
                        ))
                    segmented.append(SingleLeafAnalysis(
                        leaf_id=idx,
                        bounding_box=list(bbox),
                        leaf_mask_asset=leaf_asset,
                        leaf_crop_asset=crop_asset,
                        lesion_overlay_asset=lesion_overlay_asset,
                        attention_overlay_asset=attn_overlay_asset,
                        is_leaf=True,
                        leaf_filter_confidence=leaf_confidence,
                        candidate_score=candidate.sam_score,
                        candidate_source=candidate.model_variant,
                        classification=classification,
                        ood=ood_result,
                        segmentation=seg_result,
                        severity=severity,
                        explainability=explanation,
                        prediction_uncertainty=uncertainty,
                        warnings=leaf_warnings,
                    ))
            partial_failures: list[PartialFailure] = []
            try:
                self._with_model(self.segmenter, "segmentation", segment)
            except InferenceError as exc:
                if exc.code == InferenceErrorCode.ARTIFACT_STORAGE_FAILURE:
                    raise
                timings["segmentation_and_severity"] = self._elapsed(t0)
                leaves = segmented + self._classification_only_results(
                    predictions[len(segmented):],
                    timings,
                    start_index=len(segmented),
                )
                partial_failures.append(PartialFailure(
                    component="disease_segmentation",
                    error_type=exc.code.value,
                    message="Disease segmentation was unavailable for one or more leaves; available classifications are preserved.",
                    fallback_applied=True,
                ))
                warnings.append(PipelineWarning(
                    code="DISEASE_SEGMENTATION_UNAVAILABLE",
                    message="Disease segmentation or mask-derived severity is unavailable for one or more leaves.",
                    component="disease_segmentation",
                    severity=WarningSeverity.WARNING,
                ))
                logger.warning(
                    "inference_stage_unavailable stage=segmentation error_code=%s runtime=%s",
                    exc.code.value, self.device,
                )
            else:
                timings["segmentation_and_severity"] = self._elapsed(t0)
                logger.info("inference_stage_complete stage=segmentation_and_severity leaves=%d runtime=%s model=%s duration_ms=%d",
                            len(segmented), self.device, self.segmenter.artifact_version,
                            timings["segmentation_and_severity"])
                leaves = segmented
            warnings.extend(w for leaf in leaves for w in leaf.warnings)
            summary = self._summary(leaves)
            status = "partial" if partial_failures else "completed"
            model_versions = {
                "leaf_proposals": candidate_output.metadata.model_version,
                "dinov2_vits14": self.leaf_filter.artifact_version,
                "dinov2_vitb14": self.classifier.artifact_version,
            }
            if not partial_failures:
                model_versions["segformer_b0_plantseg"] = self.segmenter.artifact_version
            return FullScanResult(
                analysis_id=scan_id,
                status=status,
                hardware_device=self.device,
                processing_time_ms=self._elapsed(started),
                model_versions=model_versions,
                sam_variant=self._selected_sam_adapter.artifact_version,
                sam_fallback_applied=sam_fallback_applied,
                stage_timings_ms=timings,
                model_load_timings_ms=dict(self.model_load_timings_ms),
                candidate_counts=CandidateStageCounts(**self._candidate_counts),
                leaves=leaves,
                plant_summary=summary,
                warnings=warnings,
                partial_failures=partial_failures,
            )
        except InferenceError as exc:
            logger.error("inference_failed stage=%s error_code=%s runtime=%s duration_ms=%d",
                         exc.stage, exc.code.value, self.device, self._elapsed(started))
            raise
        except Exception as exc:
            logger.exception("inference_failed stage=pipeline error_code=%s runtime=%s duration_ms=%d",
                             InferenceErrorCode.MODEL_FAILURE.value, self.device, self._elapsed(started))
            raise InferenceError(InferenceErrorCode.MODEL_FAILURE,
                                 "Model inference failed; no prediction was generated", stage="pipeline") from exc
        finally:
            self._inference_slot.release()

    def _sam_candidates(self, image: np.ndarray, timings: dict[str, int]) -> StageOutput[tuple[LeafCandidate, ...]]:
        t0 = time.perf_counter()
        self._selected_sam_adapter = None
        self._candidate_counts = {
            "generated": 0,
            "valid": 0,
            "deduplicated": 0,
            "leaf_filter_accepted": 0,
            "disease_analysis_eligible": 0,
        }
        failures: list[str] = []
        for adapter, stage in ((self.sam, "sam2"), (self.mobile_sam, "mobilesam")):
            raw_candidates: list[LeafCandidate] = []
            generated_count = 0
            expected_method = (
                "mobilesam.point_grid_predictor"
                if adapter is self.mobile_sam
                else "sam2.1_automatic_mask_generator"
            )

            def generate(model_adapter):
                nonlocal generated_count
                model_candidates = model_adapter.predict(image)
                generated_count = getattr(
                    model_adapter,
                    "last_generated_candidate_count",
                    len(model_candidates),
                )
                for item in model_candidates[:self.candidate_limit]:
                    mask = np.asarray(item.get("segmentation"))
                    if mask.shape != image.shape[:2] or mask.ndim != 2 or not np.isin(mask, [0, 1, False, True]).all():
                        raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                             f"{stage} returned a mask with invalid dimensions or values", stage=stage)
                    bbox_values = item.get("bbox")
                    if not isinstance(bbox_values, (list, tuple)) or len(bbox_values) != 4:
                        raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                             f"{stage} candidate is missing a normalized bounding box", stage=stage)
                    bbox = tuple(float(v) for v in bbox_values)
                    if not np.isfinite(bbox).all() or not (
                        0 <= bbox[0] < bbox[2] <= 1 and 0 <= bbox[1] < bbox[3] <= 1
                    ):
                        raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                             f"{stage} candidate bounding box is invalid", stage=stage)
                    score = float(item.get("score", 0.0))
                    if not math.isfinite(score) or score < 0 or score > 1:
                        raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                             f"{stage} candidate score is invalid", stage=stage)
                    if not np.any(mask):
                        continue
                    if item.get("method") != expected_method:
                        raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                             f"Candidate was not produced by the configured {stage} model",
                                             stage=stage)
                    raw_candidates.append(LeafCandidate(
                        mask=mask.astype(bool),
                        bbox=bbox,
                        sam_score=score,
                        area_pixels=int(np.count_nonzero(mask)),
                        model_variant=model_adapter.artifact_version,
                    ))

            try:
                self._with_model(adapter, stage, generate)
            except ModelCapabilityError as exc:
                detail = str(exc).replace(str(adapter.artifact_path), "checkpoint")
                failures.append(f"{stage}: {detail}")
                continue
            if not raw_candidates:
                failures.append(f"{stage}: model returned no usable candidates")
                continue

            deduplicated = self._deduplicate_candidates(raw_candidates)
            if not deduplicated:
                failures.append(f"{stage}: no unique usable candidates remained")
                continue
            self._candidate_counts.update({
                "generated": int(generated_count),
                "valid": len(raw_candidates),
                "deduplicated": len(deduplicated),
            })
            self._selected_sam_adapter = adapter
            elapsed = self._elapsed(t0)
            timings["leaf_candidate_generation"] = elapsed
            if adapter is self.mobile_sam:
                logger.warning("model_fallback_applied primary=sam2 selected=mobilesam reason=%s",
                               failures[0] if failures else "SAM 2 unavailable")
            logger.info("inference_stage_complete stage=leaf_candidate_generation generated=%d valid=%d deduplicated=%d runtime=%s model=%s duration_ms=%d",
                        generated_count, len(raw_candidates), len(deduplicated), self.device,
                        adapter.artifact_version, elapsed)
            return StageOutput(
                value=tuple(deduplicated),
                metadata=StageMetadata(
                    stage="leaf_candidate_generation",
                    model_version=adapter.artifact_version,
                    runtime=self.device,
                    duration_ms=elapsed,
                ),
            )

        if all("model returned no usable candidates" in failure for failure in failures):
            raise NoLeafFoundError(f"No leaf candidates were produced; variants tried: {'; '.join(failures)}")
        raise ModelCapabilityError(
            InferenceErrorCode.UNSUPPORTED_RUNTIME,
            f"No leaf-proposal variant could run for requested runtime '{self.profile}' "
            f"(device '{self.device}'); variants tried: {'; '.join(failures)}",
            stage="variant_selection",
        )

    def _with_model(self, adapter, stage: str, operation: Callable) -> None:
        loaded_here = not adapter.is_ready()
        if loaded_here:
            model_id = MODEL_IDS.get(getattr(adapter, "name", ""))
            if model_id:
                self._select_variant(adapter, model_id)
            if not adapter.artifact_path.is_file():
                raise ModelCapabilityError(InferenceErrorCode.MISSING_ARTIFACT,
                                           f"Required {stage} model artifact is missing", stage=stage)
            try:
                load_started = time.perf_counter()
                loaded = adapter.load(self.device)
                self.model_load_timings_ms[stage] = self._elapsed(load_started)
            except Exception as exc:
                self.model_load_timings_ms[stage] = self._elapsed(load_started)
                error = self._loading_error(adapter, stage, exc)
                adapter.unload()
                raise error from exc
            if not loaded:
                error = self._loading_error(adapter, stage)
                adapter.unload()
                raise error
        try:
            operation(adapter)
        except InferenceError:
            raise
        except Exception as exc:
            raise InferenceError(InferenceErrorCode.MODEL_FAILURE,
                                 f"{stage} model execution failed", stage=stage) from exc
        finally:
            if loaded_here:
                adapter.unload()

    def _select_variant(self, adapter, model_id: str) -> None:
        if self._variant_registry is None:
            root = model_registry.workspace_root
            self._variant_registry = ModelVariantRegistry(root)
        if self._runtime_capabilities is None:
            limit = (settings.PLANTGUARD_CUDA_MEMORY_LIMIT_GB if self.profile == "cuda"
                     else settings.PLANTGUARD_CPU_MEMORY_LIMIT_GB)
            self._runtime_capabilities = collect_runtime_capabilities(
                profile=self.profile,
                memory_limit_gb=limit,
                concurrency=settings.PLANTGUARD_MAX_CONCURRENCY,
            )
        configured_variant = None
        if adapter.name == "dino_leaf_filter":
            configured_variant = settings.PLANTGUARD_LEAF_FILTER_VERSION
        elif adapter.name == "dino_disease_classifier":
            configured_variant = settings.PLANTGUARD_DISEASE_CLASSIFIER_VARIANT
        elif adapter.name == "segformer_disease_segmentation":
            configured_variant = settings.PLANTGUARD_SEGFORMER_VARIANT
        selection = self._variant_registry.select(
            adapter.name, profile=self.profile, capabilities=self._runtime_capabilities,
            memory_limit_gb=(settings.PLANTGUARD_CUDA_MEMORY_LIMIT_GB if self.profile == "cuda"
                             else settings.PLANTGUARD_CPU_MEMORY_LIMIT_GB),
            preference=self.variant_preference,
            concurrency=settings.PLANTGUARD_MAX_CONCURRENCY,
            requested_variant=configured_variant,
        )
        if adapter.name == "segformer_disease_segmentation":
            preprocessing = selection.get("preprocessing_identity") or {}
            config_relative = preprocessing.get("config_path")
            preprocessing_relative = preprocessing.get("path")
            if config_relative and preprocessing_relative:
                adapter.config_path = self._variant_registry.root / config_relative
                adapter.preprocessing_path = self._variant_registry.root / preprocessing_relative
                adapter._configuration_error = None
                adapter._load_config_and_preprocessing()
        elif adapter.name == "dino_disease_classifier":
            mapping = selection.get("label_mapping_identity") or {}
            if mapping.get("path"):
                adapter.classes_path = self._variant_registry.root / mapping["path"]
                adapter._class_names = adapter._load_classes()
        adapter.artifact_path = selection["path"]
        adapter.artifact_version = selection["variant_id"]
        if adapter.name in {
            "dino_leaf_filter",
            "dino_disease_classifier",
            "segformer_disease_segmentation",
        }:
            adapter.execution_backend = selection["backend"]
        logger.info("model_variant_selected model=%s variant=%s profile=%s backend=%s precision=%s",
                    model_id, selection["variant_id"], self.profile,
                    selection["backend"], selection["precision"])

    @staticmethod
    def _loading_error(adapter, stage: str, cause: Exception | None = None) -> ModelCapabilityError:
        detail = str(cause or adapter.last_error or "model failed to load")
        code = getattr(adapter, "load_error_code", None)
        if not isinstance(code, InferenceErrorCode):
            if isinstance(cause, ImportError):
                code = InferenceErrorCode.UNSUPPORTED_RUNTIME
            elif getattr(adapter, "_configuration_error", None):
                code = InferenceErrorCode.INVALID_CONFIGURATION
            else:
                code = InferenceErrorCode.MODEL_FAILURE
        return ModelCapabilityError(code, f"{stage} model is unavailable: {detail}", stage=stage)

    @staticmethod
    def _validate_image(image: np.ndarray) -> None:
        if not isinstance(image, np.ndarray) or image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
            raise InvalidImageError("Expected an RGB uint8 image with shape (height, width, 3)")
        height, width = image.shape[:2]
        if height == 0 or width == 0 or height > MAX_IMAGE_SIDE or width > MAX_IMAGE_SIDE or height * width > MAX_IMAGE_PIXELS:
            raise InvalidImageError("Image dimensions exceed the supported limit")

    @staticmethod
    def _probabilities(values, count: int, stage: str) -> np.ndarray:
        probs = np.asarray(values)
        if probs.shape != (1, count) or not np.isfinite(probs).all():
            raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                 f"{stage} probabilities must have shape (1, {count}) and finite values", stage=stage)
        if np.any(probs < 0) or np.any(probs > 1) or not np.isclose(float(probs.sum()), 1.0, atol=1e-3):
            raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                 f"{stage} output is not a valid probability distribution", stage=stage)
        return probs.astype(np.float32, copy=False)

    @staticmethod
    def _validated_input(values, expected_shape: tuple[int, ...], stage: str) -> np.ndarray:
        tensor = np.asarray(values)
        if tensor.shape != expected_shape or not np.issubdtype(tensor.dtype, np.floating) or not np.isfinite(tensor).all():
            raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                 f"{stage} preprocessing must produce finite float input with shape {expected_shape}",
                                 stage=stage)
        return tensor.astype(np.float32, copy=False)

    @staticmethod
    def _crop_candidate(image: np.ndarray, candidate: LeafCandidate):
        h, w = image.shape[:2]
        y0, x0, y1, x1 = candidate.bbox
        iy0, ix0 = max(0, int(y0 * h)), max(0, int(x0 * w))
        iy1, ix1 = min(h, int(math.ceil(y1 * h))), min(w, int(math.ceil(x1 * w)))
        if iy1 <= iy0 or ix1 <= ix0:
            raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT, "SAM2 candidate crop is empty", stage="sam2")
        crop = image[iy0:iy1, ix0:ix1]
        leaf_mask = candidate.mask[iy0:iy1, ix0:ix1]
        if not np.any(leaf_mask):
            raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT, "SAM2 candidate mask is empty in its crop", stage="sam2")
        return crop, leaf_mask, (y0, x0, y1, x1)

    @staticmethod
    def _deduplicate_candidates(
        candidates: list[LeafCandidate],
        *,
        overlap_threshold: float = 0.95,
    ) -> list[LeafCandidate]:
        ranked = sorted(candidates, key=lambda candidate: candidate.sam_score, reverse=True)
        unique: list[LeafCandidate] = []
        for candidate in ranked:
            mask = candidate.mask.astype(bool, copy=False)
            area = int(np.count_nonzero(mask))
            if area == 0:
                continue
            duplicate = False
            for existing in unique:
                existing_mask = existing.mask.astype(bool, copy=False)
                smaller_area = min(area, int(np.count_nonzero(existing_mask)))
                overlap = int(np.count_nonzero(mask & existing_mask))
                if smaller_area and overlap / smaller_area >= overlap_threshold:
                    duplicate = True
                    break
            if not duplicate:
                unique.append(candidate)
        return unique

    def _persist_rgb_image(self, image: np.ndarray, scan_id: str, name: str) -> MaskAsset | None:
        if self.storage is None:
            return None
        arr = np.asarray(image, dtype=np.uint8)
        buffer = io.BytesIO()
        Image.fromarray(arr, mode="RGB").save(buffer, format="PNG", optimize=True)
        payload = buffer.getvalue()
        key = f"analyses/{scan_id}/masks/{name}"
        self._put_artifact(
            payload,
            key,
            metadata={"width": str(arr.shape[1]), "height": str(arr.shape[0])},
        )
        return MaskAsset(storage_key=key, content_type="image/png", width=arr.shape[1],
                         height=arr.shape[0], byte_size=len(payload))

    @staticmethod
    def _apply_colormap(gray: np.ndarray) -> np.ndarray:
        """Apply a JET-like colormap to a 2D uint8 array without OpenCV dependency."""
        norm = gray.astype(np.float32) / 255.0
        r = np.clip(1.5 - np.abs(4.0 * norm - 3.0), 0.0, 1.0)
        g = np.clip(1.5 - np.abs(4.0 * norm - 2.0), 0.0, 1.0)
        b = np.clip(1.5 - np.abs(4.0 * norm - 1.0), 0.0, 1.0)
        rgb = np.stack([r, g, b], axis=-1)
        return (rgb * 255).astype(np.uint8)

    def _persist_mask(self, mask: np.ndarray, scan_id: str, name: str) -> MaskAsset | None:
        if self.storage is None:
            return None
        out = (mask > 0).astype(np.uint8) * 255
        buffer = io.BytesIO()
        Image.fromarray(out, mode="L").save(buffer, format="PNG", optimize=True)
        payload = buffer.getvalue()
        key = f"analyses/{scan_id}/masks/{name}"
        self._put_artifact(
            payload,
            key,
            metadata={"width": str(out.shape[1]), "height": str(out.shape[0])},
        )
        return MaskAsset(storage_key=key, content_type="image/png", width=out.shape[1],
                         height=out.shape[0], byte_size=len(payload))

    def _persist_grayscale(self, image: np.ndarray, scan_id: str, name: str) -> MaskAsset | None:
        if self.storage is None:
            return None
        gray = np.asarray(image)
        if gray.ndim != 2 or gray.dtype != np.uint8:
            raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                 "Explainability image must be a 2D uint8 array", stage="explainability")
        buffer = io.BytesIO()
        Image.fromarray(gray, mode="L").save(buffer, format="PNG", optimize=True)
        payload = buffer.getvalue()
        key = f"analyses/{scan_id}/masks/{name}"
        self._put_artifact(
            payload,
            key,
            metadata={"width": str(gray.shape[1]), "height": str(gray.shape[0])},
        )
        return MaskAsset(storage_key=key, content_type="image/png", width=gray.shape[1],
                         height=gray.shape[0], byte_size=len(payload))

    def _put_artifact(self, payload: bytes, key: str, *, metadata: dict[str, str]) -> None:
        if self.storage is None:
            raise InferenceError(
                InferenceErrorCode.ARTIFACT_STORAGE_FAILURE,
                "Analysis artifacts could not be saved",
                stage="artifact_storage",
            )
        try:
            stored_key = self.storage.put(
                payload,
                object_key=key,
                content_type="image/png",
                metadata=metadata,
            )
        except StorageError as exc:
            raise InferenceError(
                InferenceErrorCode.ARTIFACT_STORAGE_FAILURE,
                "Analysis artifacts could not be saved",
                stage="artifact_storage",
            ) from exc
        if stored_key != key:
            raise InferenceError(
                InferenceErrorCode.ARTIFACT_STORAGE_FAILURE,
                "Storage returned an unexpected analysis artifact reference",
                stage="artifact_storage",
            )

    def _persist_attention(self, attention, shape: tuple[int, int], scan_id: str, index: int) -> ExplainabilityResult | None:
        values = np.asarray(attention, dtype=np.float32)
        if values.shape != (224, 224) or not np.isfinite(values).all() or np.any(values < 0):
            raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                 "DINOv2 attribution must be a finite, non-negative 224x224 map", stage="explainability")
        values = values - values.min()
        maximum = float(values.max())
        if maximum > 0:
            values /= maximum
        gray = np.asarray(Image.fromarray((values * 255).astype(np.uint8)).resize(
            (shape[1], shape[0]), Image.Resampling.BILINEAR
        ))
        if gray.shape != shape:
            raise InferenceError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                 "DINOv2 attribution did not align to the selected leaf crop", stage="explainability")
        asset = self._persist_grayscale(gray, scan_id, f"leaf_{index}_attribution.png")
        return ExplainabilityResult(
            status="available" if asset is not None else "unavailable",
            method="dinov2_attention_rollout",
            heatmap_asset=asset,
            description=("DINOv2 Attention Rollout across all 12 transformer encoder blocks resized to the leaf crop."
                         if asset is not None else "Attribution was computed but no storage backend is configured, so no heatmap is available to the caller."),
        )

    def _classification_only_results(
        self,
        predictions,
        timings: dict[str, int],
        *,
        start_index: int = 0,
    ) -> list[SingleLeafAnalysis]:
        class_map = self.classifier.get_class_mapping() or {}
        results: list[SingleLeafAnalysis] = []
        for idx, (accepted_item, prediction, _attention, features) in enumerate(
            predictions, start=start_index
        ):
            candidate, _crop, filter_score = accepted_item
            probabilities = np.asarray(prediction.probabilities, dtype=np.float32)
            top_ids = np.argsort(probabilities)[::-1][:5]
            top_k = {class_map[int(i)]: round(float(probabilities[i]), 4) for i in top_ids}
            crop_name, _, disease_name = prediction.class_name.partition("___")
            classification = ClassificationResult(
                primary_class=prediction.class_name,
                confidence=prediction.confidence,
                is_healthy="healthy" in prediction.class_name.lower(),
                crop_type=crop_name,
                disease_name=disease_name.replace("_", " "),
                top_k_probabilities=top_k,
            )
            entropy_signal = self.ood_detector.evaluate_probabilities(probabilities)
            uncertainty = PredictionUncertainty(
                score=entropy_signal.score,
                threshold=entropy_signal.threshold,
                is_high_uncertainty=entropy_signal.score > entropy_signal.threshold,
                classification_confidence=classification.confidence,
                method="normalized_shannon_entropy",
                calibration_status="incomplete",
            )
            ood_started = time.perf_counter()
            ood_result = self.ood_detector.evaluate_features(
                features,
                prediction.class_index,
                confidence=prediction.confidence,
            )
            timings["ood_detection"] = timings.get("ood_detection", 0) + self._elapsed(ood_started)
            leaf_warnings = [PipelineWarning(
                code="DISEASE_SEGMENTATION_UNAVAILABLE",
                message="Disease segmentation and mask-derived severity are unavailable for this leaf.",
                component="disease_segmentation",
                severity=WarningSeverity.WARNING,
            )]
            if ood_result.is_ood:
                leaf_warnings.append(PipelineWarning(
                    code="OOD_FLAGGED_UNVALIDATED",
                    message="The provisional OOD threshold was exceeded; the classifier prediction is retained as an unverified candidate and flagged for review.",
                    component="reliability",
                    severity=WarningSeverity.WARNING,
                ))
            results.append(SingleLeafAnalysis(
                leaf_id=idx,
                bounding_box=list(candidate.bbox),
                is_leaf=True,
                leaf_filter_confidence=filter_score.confidence,
                candidate_score=candidate.sam_score,
                candidate_source=candidate.model_variant,
                classification=classification,
                ood=ood_result,
                severity=SeverityResult(
                    status="unavailable",
                    method="unavailable",
                    assessment="Disease segmentation did not complete; affected area and severity are unavailable.",
                ),
                explainability=ExplainabilityResult(
                    status="unavailable",
                    method="dinov2_attention_rollout",
                    description="No explainability artifact is available for this partial result.",
                ),
                prediction_uncertainty=uncertainty,
                warnings=leaf_warnings,
            ))
        return results

    @staticmethod
    def _summary(leaves: list[SingleLeafAnalysis]) -> PlantHealthSummary:
        classified_leaves = [
            leaf for leaf in leaves
            if leaf.classification is not None and not (leaf.ood and leaf.ood.is_ood)
        ]
        healthy = sum(1 for leaf in classified_leaves if leaf.classification and leaf.classification.is_healthy)
        breakdown: dict[str, int] = {}
        for leaf in classified_leaves:
            if leaf.classification and not leaf.classification.is_healthy:
                label = leaf.classification.disease_name or leaf.classification.primary_class
                breakdown[label] = breakdown.get(label, 0) + 1
        measured = [
            l.severity.affected_percentage for l in classified_leaves
            if l.severity and l.severity.status == "available" and l.severity.affected_percentage is not None
        ]
        avg_severity = (
            float(np.mean(measured))
            if measured and len(measured) == len(classified_leaves)
            else None
        )
        # Descriptive only: 100 minus mean measured severity, not a validated health metric.
        score = (
            round(max(0.0, min(100.0, 100.0 - avg_severity)), 1)
            if avg_severity is not None
            else None
        )
        status = OverallHealthStatus.UNKNOWN
        if classified_leaves and avg_severity is not None:
            status = (
                OverallHealthStatus.HEALTHY
                if healthy == len(leaves)
                else OverallHealthStatus.MILDLY_DISEASED
            )
        return PlantHealthSummary(
            overall_health_score=score,
            health_status=status,
            total_leaves_detected=len(leaves),
            valid_leaves_analyzed=len(classified_leaves),
            healthy_leaves_count=healthy,
            diseased_leaves_count=len(classified_leaves) - healthy,
            primary_diagnosis=max(breakdown, key=breakdown.get) if breakdown else ("healthy" if classified_leaves else None),
            disease_breakdown=breakdown,
            average_severity_percentage=avg_severity,
            recommendations=[],
        )

    @staticmethod
    def _elapsed(start: float) -> int:
        return max(0, int((time.perf_counter() - start) * 1000))
