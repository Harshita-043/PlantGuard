"""Check model runtime prerequisites without loading checkpoints or running inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.ml.runtime import collect_runtime_capabilities
from app.core.config import settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-cuda", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error("Output report already exists; choose a new path")
    profile = "cuda" if args.require_cuda else settings.PLANTGUARD_INFERENCE_PROFILE
    limit = settings.PLANTGUARD_CUDA_MEMORY_LIMIT_GB if profile == "cuda" else settings.PLANTGUARD_CPU_MEMORY_LIMIT_GB
    report = collect_runtime_capabilities(profile=profile, memory_limit_gb=limit,
                                           concurrency=settings.PLANTGUARD_MAX_CONCURRENCY).public_dict()
    checks = {
        "cuda_runtime_usable": report["cuda"]["available"] is True if args.require_cuda else None,
        "supported_python_312": report["supported_python_version"],
        "pytorch_cuda_build_present": bool(report["cuda"]["pytorch_cuda_build"]) if args.require_cuda else None,
        "sam2_requirements_present": report["model_compatibility"]["sam2_hiera_base_plus"]["cuda" if args.require_cuda else "cpu"]["status"] == "prerequisites_present",
        "dinov2_filter_requirements_present": report["model_compatibility"]["dinov2_vits14_leaf_filter"]["cuda" if args.require_cuda else "cpu"]["status"] == "prerequisites_present",
        "dinov2_classifier_requirements_present": report["model_compatibility"]["dinov2_vitb14_classifier"]["cuda" if args.require_cuda else "cpu"]["status"] == "prerequisites_present",
        "segformer_requirements_present": report["model_compatibility"]["segformer_b0_plantseg"]["cuda" if args.require_cuda else "cpu"]["status"] == "prerequisites_present",
    }
    report["checks"] = checks
    report["checkpoints_loaded"] = False
    report["cuda_inference_performed"] = False
    serialized = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    required = [value for value in checks.values() if value is not None]
    return 0 if all(required) else 2


if __name__ == "__main__":
    raise SystemExit(main())
