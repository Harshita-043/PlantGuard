"""Classify optimization candidates without converting or loading any model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.ml.runtime import collect_runtime_capabilities


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error("Output report already exists; choose a new path")
    runtime = collect_runtime_capabilities(profile="cuda")
    report = {
        "schema_version": "1.0.0",
        "checkpoint_loading_performed": False,
        "conversion_performed": False,
        "variants_created": [],
        "verified_variants": [],
        "not_beneficial_variants": [],
        "candidates": [
            {"model": "SAM 2.1 Hiera Base Plus", "variant": "dynamic_int8", "status": "UNSUPPORTED",
             "reason": "Current adapter has no quantized SAM path; custom operators and mask agreement are unverified."},
            {"model": "SAM 2.1 Hiera Base Plus", "variant": "onnx_or_openvino", "status": "UNSUPPORTED",
             "reason": "Current adapter only loads official PyTorch SAM2; no export/decoder compatibility is verified."},
            {"model": "DINOv2 ViT-S/14 leaf filter", "variant": "CPU_dynamic_int8", "status": "BLOCKED" if not runtime.inference_backends["torch"] else "NOT_EVALUATED",
             "reason": "No calibrated representative dataset, operator-level conversion test, or quality comparison has been approved."},
            {"model": "DINOv2 ViT-B/14 classifier", "variant": "CPU_dynamic_int8", "status": "BLOCKED" if not runtime.inference_backends["torch"] else "NOT_EVALUATED",
             "reason": "No calibrated representative dataset, operator-level conversion test, or class-agreement benchmark has been approved."},
            {"model": "DINOv2 ViT-B/14 classifier", "variant": "CUDA_FP16", "status": "BLOCKED" if runtime.cuda["available"] is not True else "NOT_EVALUATED",
             "reason": "FP16 output agreement, confidence drift, reliability impacts, and latency/VRAM have not been measured."},
            {"model": "SegFormer-B0 PlantSeg", "variant": "CPU_dynamic_int8", "status": "BLOCKED" if not runtime.inference_backends["torch"] else "NOT_EVALUATED",
             "reason": "No operator support check, PlantSeg validation set, mask IoU comparison, or severity-drift evaluation has been run."},
            {"model": "SegFormer-B0 PlantSeg", "variant": "CUDA_FP16", "status": "BLOCKED" if runtime.cuda["available"] is not True else "NOT_EVALUATED",
             "reason": "FP16 logits, mask agreement, mask IoU, severity differences, and VRAM are unmeasured."},
            {"model": "All", "variant": "ONNX_Runtime_or_OpenVINO", "status": "BLOCKED" if not (runtime.inference_backends["onnxruntime"] or runtime.inference_backends["openvino"]) else "NOT_EVALUATED",
             "reason": "Backend installation alone does not establish graph export or operator support for this architecture."},
        ],
        "NOT_BENEFICIAL": "No candidate has measurements supporting this conclusion.",
        "runtime": runtime.public_dict(),
    }
    output = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
