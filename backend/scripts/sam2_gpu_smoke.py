"""Explicit GPU-only SAM 2.1 Hiera Base Plus smoke check (never run on the Vivobook)."""

import argparse
import logging
import time
from pathlib import Path

import numpy as np
from PIL import Image

from app.ml.adapters.sam_adapter import Sam2LeafSegmentationAdapter
from app.ml.errors import InferenceErrorCode, ModelCapabilityError


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, type=Path, help="Path to a representative RGB test image")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        import torch
    except ImportError as exc:
        raise SystemExit("BLOCKED: PyTorch CUDA runtime is not installed") from exc
    if not torch.cuda.is_available():
        raise SystemExit("BLOCKED: CUDA is not available; this smoke check requires the RTX 5060 host")
    if not args.image.is_file():
        raise SystemExit(f"Image not found: {args.image}")

    with Image.open(args.image) as im:
        image = np.asarray(im.convert("RGB"), dtype=np.uint8)
    adapter = Sam2LeafSegmentationAdapter(execution_strategy="cuda_dense")
    started = time.perf_counter()
    if not adapter.load("cuda:0"):
        raise SystemExit(f"BLOCKED: {adapter.last_error}")
    try:
        candidates = adapter.predict(image)
        torch.cuda.synchronize()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if any(candidate.get("method") != "sam2.1_automatic_mask_generator" for candidate in candidates):
            raise ModelCapabilityError(InferenceErrorCode.MODEL_FAILURE,
                                       "Candidate provenance is not SAM2", stage="sam2")
        print({
            "status": "passed",
            "runtime": torch.cuda.get_device_name(0),
            "model_variant": adapter.artifact_version,
            "candidate_count": len(candidates),
            "duration_ms": elapsed_ms,
            "mask_shapes": [list(candidate["segmentation"].shape) for candidate in candidates],
        })
    finally:
        adapter.unload()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
