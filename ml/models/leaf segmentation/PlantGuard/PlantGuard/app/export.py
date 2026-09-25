
# app/export.py

import os
import json
import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

from .segmentation import crop_on_white, label_anchor


def save_overlay(
    image,
    masks,
    path,
    title="PlantGuard — Leaf Candidate Masks"
):

    os.makedirs(
        os.path.dirname(path) or ".",
        exist_ok=True
    )

    rng = np.random.default_rng(3)

    overlay = image.astype(
        np.float32
    ).copy()

    for mask in masks:

        segmentation = (
            mask["segmentation"]
            .astype(bool)
        )

        color = rng.integers(
            40,
            255,
            size=3
        ).astype(np.float32)

        overlay[segmentation] = (
            0.45 * overlay[segmentation]
            + 0.55 * color
        )

    overlay = np.clip(
        overlay,
        0,
        255
    ).astype(np.uint8)

    fig, ax = plt.subplots(
        figsize=(8, 10)
    )

    ax.imshow(overlay)
    ax.axis("off")

    ax.set_title(
        f"{title} ({len(masks)})"
    )

    for i, mask in enumerate(
        masks,
        start=1
    ):

        x, y = label_anchor(
            mask["segmentation"]
        )

        ax.text(
            x,
            y,
            str(i),
            color="white",
            fontsize=9,
            ha="center",
            va="center",
            bbox=dict(
                boxstyle="square,pad=0.25",
                fc="black",
                ec="none",
                alpha=0.85
            )
        )

    plt.tight_layout()

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close(fig)


def save_cutout_sheet(
    image,
    masks,
    path,
    ncols=5
):

    os.makedirs(
        os.path.dirname(path) or ".",
        exist_ok=True
    )

    if not masks:

        fig, ax = plt.subplots(
            figsize=(8, 4)
        )

        ax.text(
            0.5,
            0.5,
            "No leaf candidates detected",
            ha="center",
            va="center"
        )

        ax.axis("off")

        plt.savefig(
            path,
            dpi=200,
            bbox_inches="tight"
        )

        plt.close(fig)

        return

    nrows = int(
        np.ceil(
            len(masks) / ncols
        )
    )

    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(
            3 * ncols,
            3 * nrows
        ),
        squeeze=False
    )

    for ax in axes.ravel():
        ax.axis("off")

    for i, mask in enumerate(masks):

        ax = axes[
            i // ncols,
            i % ncols
        ]

        ax.imshow(
            crop_on_white(
                image,
                mask
            )
        )

        ax.set_title(
            f"Leaf {i + 1}"
        )

        ax.axis("off")

    fig.suptitle(
        f"PlantGuard — Extracted Leaves ({len(masks)})"
    )

    plt.tight_layout()

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
        facecolor="white"
    )

    plt.close(fig)


def export_candidates(
    image,
    masks,
    out_dir,
    stem="plant"
):

    os.makedirs(
        out_dir,
        exist_ok=True
    )

    h, w = image.shape[:2]

    # CVPPP-style indexed label image
    label = np.zeros(
        (h, w),
        dtype=np.uint16
    )

    metadata = []

    for leaf_id, mask in enumerate(
        masks,
        start=1
    ):

        segmentation = (
            mask["segmentation"]
            .astype(bool)
        )

        # ------------------------------------------------
        # Indexed segmentation label
        # ------------------------------------------------

        label[
            segmentation &
            (label == 0)
        ] = leaf_id

        # ------------------------------------------------
        # Bounding box
        # ------------------------------------------------

        x, y, bw, bh = [
            int(v)
            for v in mask["bbox"]
        ]

        x0 = max(x, 0)
        y0 = max(y, 0)

        x1 = min(
            x + bw,
            w
        )

        y1 = min(
            y + bh,
            h
        )

        # ------------------------------------------------
        # Transparent RGBA leaf crop
        # ------------------------------------------------

        alpha = (
            segmentation
            .astype(np.uint8)
            * 255
        )

        rgba = np.dstack(
            [
                image,
                alpha
            ]
        )

        crop = rgba[
            y0:y1,
            x0:x1
        ]

        Image.fromarray(
            crop
        ).save(
            os.path.join(
                out_dir,
                f"{stem}_leaf_{leaf_id:03d}.png"
            )
        )

        # ------------------------------------------------
        # Metadata
        # ------------------------------------------------

        metadata.append(
            {
                "id": leaf_id,
                "bbox_xywh": [
                    x,
                    y,
                    bw,
                    bh
                ],
                "area": int(
                    mask["area"]
                ),
                "predicted_iou": float(
                    mask.get(
                        "predicted_iou",
                        -1
                    )
                ),
                "stability_score": float(
                    mask.get(
                        "stability_score",
                        -1
                    )
                ),
                "leaf_probability": float(
                    mask.get(
                        "leaf_prob",
                        -1
                    )
                )
            }
        )

    # ----------------------------------------------------
    # Save indexed label image
    # ----------------------------------------------------

    Image.fromarray(
        label
    ).save(
        os.path.join(
            out_dir,
            f"{stem}_label.png"
        )
    )

    # ----------------------------------------------------
    # Save JSON metadata
    # ----------------------------------------------------

    with open(
        os.path.join(
            out_dir,
            f"{stem}_candidates.json"
        ),
        "w"
    ) as f:

        json.dump(
            metadata,
            f,
            indent=2
        )

    return metadata