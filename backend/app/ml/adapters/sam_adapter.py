"""
SAM 2.1 Hiera Base+ Instance Segmentation Adapter.

Implements Segment Anything 2.1 with robust leaf candidate selection:
- Does NOT assume the largest mask is always the correct leaf.
- Filters candidates using geometric leaf priors (area ratios, aspect ratios, margin offsets).
- Configurable CPU/GPU execution strategy for ASUS Vivobook responsiveness.
Artifact: `artifacts/sam2/sam2.1_hiera_base_plus.pt`.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.ml.interfaces.adapter import (
    BaseModelAdapter,
    ContractSpec,
    EvaluationStatus,
    FailureBehavior,
    ModelLoadingStatus,
    PreprocessingSpec,
)
from app.ml.errors import InferenceErrorCode, ModelCapabilityError

logger = logging.getLogger(__name__)


class Sam2LeafSegmentationAdapter(BaseModelAdapter):
    """
    Adapter for SAM 2.1 Hiera Base+ leaf segmentation.
    Configurable execution strategies:
      - 'auto': use bounded CPU settings unless a CUDA device is selected.
      - 'cpu_bounded': actual SAM2 inference with an 8x8 point grid.
      - 'cuda_dense': actual SAM2 inference with a 32x32 point grid.
    """

    def __init__(
        self,
        artifact_path: Optional[Path] = None,
        artifact_version: str = "sam2.1-hiera-base-plus",
        execution_strategy: Optional[str] = None,
        failure_behavior: FailureBehavior = FailureBehavior.FAIL_FAST,
    ):
        path = artifact_path or self._resolve_default_path()
        super().__init__(
            name="sam2_instance_segmentation",
            artifact_path=path,
            artifact_version=artifact_version,
            device_requirements="cuda_recommended",
            failure_behavior=failure_behavior,
            evaluation_status=EvaluationStatus.EXPERIMENTAL,
        )
        self.execution_strategy = execution_strategy or os.getenv("PLANTGUARD_SAM_STRATEGY", "auto")
        self.config_name = os.getenv("PLANTGUARD_SAM_CONFIG", "configs/sam2.1/sam2.1_hiera_b+.yaml")
        self._model = None
        self._generator = None

    def _resolve_default_path(self) -> Path:
        candidates = [
            Path("artifacts/sam2/sam2.1_hiera_base_plus.pt"),
            Path("../artifacts/sam2/sam2.1_hiera_base_plus.pt"),
        ]
        for c in candidates:
            if c.exists():
                return c.resolve()
        return Path("artifacts/sam2/sam2.1_hiera_base_plus.pt")

    def get_input_contract(self) -> ContractSpec:
        return ContractSpec(
            data_type="np.ndarray[uint8]",
            shape=("H", "W", 3),
            description="Raw RGB uint8 image array",
        )

    def get_preprocessing_spec(self) -> PreprocessingSpec:
        return PreprocessingSpec(
            target_size=(1024, 1024),
            mean=(0.485, 0.456, 0.406),
            std=(0.229, 0.224, 0.225),
            color_mode="RGB",
            normalization_range=(0.0, 1.0),
        )

    def get_output_contract(self) -> ContractSpec:
        return ContractSpec(
            data_type="List[Dict[str, Any]]",
            shape=("N",),
            description="Filtered candidate leaf masks with normalized bounding boxes and quality metrics",
        )

    def get_class_mapping(self) -> Optional[Dict[int, str]]:
        return None

    def load(self, target_device: str = "cpu") -> bool:
        """Load SAM 2.1 model if sam2 package is available."""
        self.loading_status = ModelLoadingStatus.LOADING
        self.active_device = target_device
        self.last_error = None
        self.load_error_code = None

        if not self.artifact_path.is_file():
            self.last_error = f"SAM2 checkpoint is missing: {self.artifact_path}"
            self.load_error_code = InferenceErrorCode.MISSING_ARTIFACT
            self.loading_status = ModelLoadingStatus.FAILED
            logger.warning(self.last_error)
            return False

        if self.execution_strategy not in {"auto", "cpu_bounded", "cuda_dense"}:
            self.last_error = f"Unsupported SAM2 strategy: {self.execution_strategy}"
            self.load_error_code = InferenceErrorCode.UNSUPPORTED_RUNTIME
            self.loading_status = ModelLoadingStatus.FAILED
            return False

        try:
            import sam2
            from sam2.build_sam import build_sam2
            from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator

            config_rel = Path(self.config_name)
            if config_rel.is_absolute() or ".." in config_rel.parts:
                self.last_error = "SAM2 config must be a package-relative config name"
                self.load_error_code = InferenceErrorCode.INVALID_CONFIGURATION
                self.loading_status = ModelLoadingStatus.FAILED
                return False
            sam2_package_root = Path(sam2.__file__).resolve().parent
            config_path = sam2_package_root / config_rel
            if not config_path.is_file():
                self.last_error = f"SAM2 package config is missing: {self.config_name}"
                self.load_error_code = InferenceErrorCode.INVALID_CONFIGURATION
                self.loading_status = ModelLoadingStatus.FAILED
                return False

            logger.info("Loading SAM 2.1 Hiera Base+ on %s (strategy: %s)...", target_device, self.execution_strategy)
            if target_device.startswith("cuda"):
                import torch
                if not torch.cuda.is_available():
                    raise RuntimeError("CUDA was requested but is unavailable")
            elif target_device != "cpu":
                raise RuntimeError(f"Unsupported SAM2 device: {target_device}")

            if self.execution_strategy == "cuda_dense" and not target_device.startswith("cuda"):
                raise RuntimeError("cuda_dense SAM2 strategy requires a CUDA device")
            if self.execution_strategy == "cpu_bounded" and target_device.startswith("cuda"):
                points_per_side = 8
            else:
                points_per_side = 8 if target_device == "cpu" else 32
            self._model = build_sam2(self.config_name, str(self.artifact_path), device=target_device)
            self._generator = SAM2AutomaticMaskGenerator(
                model=self._model,
                points_per_side=points_per_side,
                pred_iou_thresh=0.80,
                stability_score_thresh=0.85,
                crop_n_layers=0 if target_device == "cpu" else 1,
            )
            self.loading_status = ModelLoadingStatus.READY
            logger.info("SAM 2.1 loaded successfully (points_per_side=%d)", points_per_side)
            return True
        except ImportError as e:
            self.last_error = f"SAM 2.1 package not installed in environment: {e}"
            self.load_error_code = InferenceErrorCode.UNSUPPORTED_RUNTIME
            self.loading_status = ModelLoadingStatus.FAILED
            logger.warning(self.last_error)
            return False
        except Exception as exc:
            self.last_error = f"Failed to load SAM 2.1: {exc}"
            self.load_error_code = InferenceErrorCode.MODEL_FAILURE
            self.loading_status = ModelLoadingStatus.FAILED
            logger.error(self.last_error)
            return False

    def unload(self) -> None:
        """Evict SAM2 weights from memory."""
        self._model = None
        self._generator = None
        self.loading_status = ModelLoadingStatus.UNLOADED
        self.active_device = None

    def predict(self, raw_rgb_image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Segment and filter leaf candidates.
        Applies geometric pruning so the largest mask (often the background or table) is not chosen blindly.
        """
        if raw_rgb_image.ndim != 3 or raw_rgb_image.shape[2] != 3 or raw_rgb_image.dtype != np.uint8:
            raise ValueError("SAM2 expects an RGB uint8 image with shape (H, W, 3)")
        if not self.is_ready() or self._generator is None:
            raise ModelCapabilityError(InferenceErrorCode.UNSUPPORTED_RUNTIME,
                                       "SAM2 is not loaded; heuristic proposals are disabled", stage="sam2")
        raw_masks = self._generator.generate(raw_rgb_image)
        candidates = self._filter_and_rank_leaf_candidates(raw_masks, raw_rgb_image.shape[:2])
        for candidate in candidates:
            candidate["method"] = "sam2.1_automatic_mask_generator"
        return candidates

    @staticmethod
    def _filter_and_rank_leaf_candidates(
        raw_masks: List[Dict[str, Any]],
        image_shape: Tuple[int, int],
    ) -> List[Dict[str, Any]]:
        """
        Intelligently filter candidate masks:
        - Rejects background canvas (area > 90% of entire image).
        - Rejects tiny noise fragments (area < 0.5% of entire image).
        - Rejects extreme needle-thin edge artifacts (aspect ratio < 0.15 or > 6.5).
        - Ranks by combination of predicted IOU, stability, and centrality.
        """
        h, w = image_shape
        total_pixels = h * w
        valid_candidates = []

        for m in raw_masks:
            seg = m.get("segmentation")
            if seg is None:
                continue

            area = int(m.get("area", np.count_nonzero(seg)))
            area_ratio = area / float(total_pixels)

            # Rule 1: Exclude image background / whole-frame masks
            if area_ratio > 0.90 or area_ratio < 0.005:
                continue

            # Compute bounding box
            if "bbox" in m and len(m["bbox"]) == 4:
                # SAM bbox format is [x, y, width, height]
                bx, by, bw, bh = m["bbox"]
                ymin = float(by) / h
                xmin = float(bx) / w
                ymax = float(by + bh) / h
                xmax = float(bx + bw) / w
                aspect_ratio = float(bw) / max(1.0, float(bh))
            else:
                rows = np.any(seg, axis=1)
                cols = np.any(seg, axis=0)
                if not np.any(rows) or not np.any(cols):
                    continue
                r_min, r_max = np.where(rows)[0][[0, -1]]
                c_min, c_max = np.where(cols)[0][[0, -1]]
                ymin = float(r_min) / h
                xmin = float(c_min) / w
                ymax = float(r_max + 1) / h
                xmax = float(c_max + 1) / w
                aspect_ratio = float(c_max - c_min + 1) / max(1.0, float(r_max - r_min + 1))

            # Rule 2: Exclude extreme needle-like slivers
            if aspect_ratio < 0.15 or aspect_ratio > 6.5:
                continue

            # Centrality score: leaves closer to the center of the viewfinder get priority
            center_y = (ymin + ymax) / 2.0
            center_x = (xmin + xmax) / 2.0
            dist_from_center = np.sqrt((center_y - 0.5) ** 2 + (center_x - 0.5) ** 2)
            centrality = max(0.0, 1.0 - dist_from_center * 1.4)

            quality_score = float(m.get("predicted_iou", 0.8)) * 0.6 + centrality * 0.4

            valid_candidates.append({
                "segmentation": seg,
                "bbox": [round(ymin, 4), round(xmin, 4), round(ymax, 4), round(xmax, 4)],
                "area": area,
                "score": round(quality_score, 4),
            })

        # Rank candidates by quality score descending
        valid_candidates.sort(key=lambda x: x["score"], reverse=True)

        return valid_candidates
