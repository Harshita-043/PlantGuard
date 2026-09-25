

"""
PlantGuard inference pipeline.

Pipeline
--------
Input image
    ↓
SAM2.1 automatic mask generation
    ↓
Geometric / area filtering
    ↓
CLIP zero-shot leaf filtering
    ↓
Leaf candidate ranking
    ↓
Maximum leaf limit
    ↓
Spatial ordering
    ↓
Export
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import torch

from sam2.build_sam import build_sam2
from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator

from .config import (
    MODEL_PATH,
    MODEL_CONFIG,
    DEVICE,
    MAX_IMAGE_SIDE,
    POINTS_PER_SIDE,
    POINTS_PER_BATCH,
    PRED_IOU_THRESHOLD,
    STABILITY_SCORE_THRESHOLD,
    BOX_NMS_THRESHOLD,
    CROP_N_LAYERS,
    MIN_MASK_REGION_AREA,
    MAX_LEAVES,
    LEAF_THRESHOLD,
    OUTPUT_DIR,
    USE_CLIP,
)

from .preprocessing import load_image
from .segmentation import filter_area
from .leaf_filter import LeafFilter
from .export import (
    save_overlay,
    save_cutout_sheet,
    export_candidates,
)


class PlantGuard:
    """
    Complete PlantGuard inference engine.

    Components
    ----------
    SAM2.1:
        Generates candidate segmentation masks.

    CLIP:
        Filters candidate masks into leaf / non-leaf.

    Export:
        Saves overlay, leaf grid, masks and metadata.
    """

    def __init__(self) -> None:

        self.device = DEVICE

        # --------------------------------------------------
        # Validate model files
        # --------------------------------------------------

        if not Path(MODEL_PATH).exists():
            raise FileNotFoundError(
                f"SAM2 checkpoint not found:\n{MODEL_PATH}"
            )

        if not Path(MODEL_CONFIG).exists():
            raise FileNotFoundError(
                f"SAM2 configuration not found:\n{MODEL_CONFIG}"
            )

        # --------------------------------------------------
        # Load SAM2.1
        # --------------------------------------------------

        print("Loading SAM2 model...")

        self.model = build_sam2(
            str(MODEL_CONFIG),
            str(MODEL_PATH),
            device=self.device,
            apply_postprocessing=False,
        )

        self.model.eval()

        # --------------------------------------------------
        # SAM2 automatic mask generator
        # --------------------------------------------------

        self.generator = SAM2AutomaticMaskGenerator(
            model=self.model,

            points_per_side=POINTS_PER_SIDE,

            points_per_batch=POINTS_PER_BATCH,

            pred_iou_thresh=PRED_IOU_THRESHOLD,

            stability_score_thresh=STABILITY_SCORE_THRESHOLD,

            box_nms_thresh=BOX_NMS_THRESHOLD,

            crop_n_layers=CROP_N_LAYERS,

            min_mask_region_area=MIN_MASK_REGION_AREA,
        )

        # --------------------------------------------------
        # Load CLIP leaf filter
        # --------------------------------------------------

        self.leaf_filter = None

        if USE_CLIP:

            print("Loading CLIP leaf filter...")

            self.leaf_filter = LeafFilter(
                device=self.device,
                threshold=LEAF_THRESHOLD,
            )

        print("PlantGuard model initialized.")

    # ======================================================
    # Prediction
    # ======================================================

    def predict(
        self,
        image_path: str | os.PathLike,
        save_results: bool = True,
    ) -> dict[str, Any]:
        """
        Run PlantGuard inference.

        Parameters
        ----------
        image_path:
            Input plant image.

        save_results:
            Whether to save generated artifacts.

        Returns
        -------
        dict
            {
                "image": RGB numpy array,
                "masks": list of leaf masks,
                "count": number of leaves,
                "metadata": optional exported metadata
            }
        """

        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(
                f"Input image not found:\n{image_path}"
            )

        # --------------------------------------------------
        # Load image
        # --------------------------------------------------

        image = load_image(
            str(image_path),
            MAX_IMAGE_SIDE,
        )

        # --------------------------------------------------
        # Generate SAM2 candidate masks
        # --------------------------------------------------

        with torch.inference_mode():

            masks = self.generator.generate(image)

        candidate_count = len(masks)

        # --------------------------------------------------
        # Geometric / area filtering
        # --------------------------------------------------

        masks = filter_area(
            masks,
            image,
        )

        after_area_filter = len(masks)

        # --------------------------------------------------
        # CLIP leaf filtering
        #
        # IMPORTANT:
        # CLIP runs BEFORE MAX_LEAVES.
        # --------------------------------------------------

        if self.leaf_filter is not None:

            masks = self.leaf_filter.filter(
                image,
                masks,
            )

        after_clip_filter = len(masks)

        # --------------------------------------------------
        # Rank leaf candidates
        #
        # SAM2 mask quality × CLIP leaf score
        # --------------------------------------------------

        def ranking_score(mask: dict) -> float:

            sam_score = float(
                mask.get(
                    "predicted_iou",
                    0.0,
                )
            )

            leaf_score = float(
                mask.get(
                    "leaf_prob",
                    1.0,
                )
            )

            return sam_score * leaf_score

        masks = sorted(
            masks,
            key=ranking_score,
            reverse=True,
        )

        # --------------------------------------------------
        # Maximum number of leaves
        # --------------------------------------------------

        masks = masks[:MAX_LEAVES]

        # --------------------------------------------------
        # Spatial ordering
        #
        # Top-to-bottom, then left-to-right.
        # --------------------------------------------------

        masks = sorted(
            masks,
            key=lambda m: (
                float(m["bbox"][1]),
                float(m["bbox"][0]),
            ),
        )

        # --------------------------------------------------
        # Assign final IDs
        # --------------------------------------------------

        for idx, mask in enumerate(masks, start=1):
            mask["id"] = idx

        # --------------------------------------------------
        # Base result
        # --------------------------------------------------

        result: dict[str, Any] = {
            "image": image,
            "masks": masks,
            "count": len(masks),
            "statistics": {
                "sam_candidates": candidate_count,
                "after_area_filter": after_area_filter,
                "after_clip_filter": after_clip_filter,
                "final_leaf_count": len(masks),
            },
        }

        # --------------------------------------------------
        # Export results
        # --------------------------------------------------

        if save_results:

            stem = image_path.stem

            result_dir = (
                Path(OUTPUT_DIR) / stem
            )

            result_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            # ----------------------------------------------
            # Overlay
            # ----------------------------------------------

            save_overlay(
                image,
                masks,
                str(
                    result_dir /
                    "leaf_masks.png"
                ),
            )

            # ----------------------------------------------
            # Leaf contact sheet
            # ----------------------------------------------

            save_cutout_sheet(
                image,
                masks,
                str(
                    result_dir /
                    "leaf_grid.png"
                ),
            )

            # ----------------------------------------------
            # Individual masks / crops / metadata
            # ----------------------------------------------

            metadata = export_candidates(
                image,
                masks,
                str(
                    result_dir /
                    "leaves"
                ),
                stem,
            )

            result["metadata"] = metadata

        return result
