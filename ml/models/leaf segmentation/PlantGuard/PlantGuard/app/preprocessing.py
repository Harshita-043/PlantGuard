
# app/preprocessing.py

import cv2
import numpy as np
from PIL import Image


def load_image(
    path: str,
    max_side: int = 1280
):
    """
    Load image as RGB numpy array.
    """

    image = np.array(
        Image.open(path).convert("RGB")
    )

    h, w = image.shape[:2]

    scale = max_side / max(h, w)

    if scale < 1:

        image = cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_AREA
        )

    return image