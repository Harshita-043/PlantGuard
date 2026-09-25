
# app/segmentation.py

import os
import cv2
import numpy as np
import matplotlib.pyplot as plt


def crop_on_white(
    image,
    mask,
    pad=4
):
    x, y, w, h = [
        int(v)
        for v in mask["bbox"]
    ]

    segmentation = mask["segmentation"]

    output = np.full_like(
        image,
        255
    )

    output[segmentation] = image[segmentation]

    x0 = max(x - pad, 0)
    y0 = max(y - pad, 0)

    x1 = min(
        x + w + pad,
        image.shape[1]
    )

    y1 = min(
        y + h + pad,
        image.shape[0]
    )

    return output[y0:y1, x0:x1]


def label_anchor(segmentation):

    seg = segmentation.astype(
        np.uint8
    )

    distance = cv2.distanceTransform(
        seg,
        cv2.DIST_L2,
        3
    )

    y, x = np.unravel_index(
        distance.argmax(),
        distance.shape
    )

    return x, y


def filter_area(
    masks,
    image,
    min_frac=0.002,
    max_frac=0.25
):

    h, w = image.shape[:2]

    total_area = h * w

    masks = [
        m for m in masks
        if min_frac <=
        m["area"] / total_area
        <= max_frac
    ]

    masks.sort(
        key=lambda m: -m["area"]
    )

    return masks