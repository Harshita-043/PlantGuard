"""Compare baseline and candidate outputs on the identical input image."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image


def _mask(report_path: Path, relative_path: str) -> np.ndarray:
    path = report_path.parent / relative_path
    with Image.open(path) as image:
        return np.asarray(image.convert("L")) > 0


def compare(baseline_path: Path, candidate_path: Path) -> dict:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if baseline.get("input_sha256") != candidate.get("input_sha256"):
        raise ValueError("Baseline and candidate must use the same input image checksum")
    left, right = baseline.get("leaves", []), candidate.get("leaves", [])
    labels_agree = len(left) == len(right) and all(
        a.get("classification", {}).get("primary_class") == b.get("classification", {}).get("primary_class")
        for a, b in zip(left, right)
    )
    confidence_deltas = [abs(a["classification"]["confidence"] - b["classification"]["confidence"])
                         for a, b in zip(left, right) if a.get("classification") and b.get("classification")]
    severity_deltas = [abs(a["severity"]["affected_percentage"] - b["severity"]["affected_percentage"])
                       for a, b in zip(left, right) if a.get("severity", {}).get("affected_percentage") is not None
                       and b.get("severity", {}).get("affected_percentage") is not None]
    mask_ious = []
    for a, b in zip(left, right):
        am, bm = a.get("masks", {}).get("disease"), b.get("masks", {}).get("disease")
        if am and bm:
            x, y = _mask(baseline_path, am), _mask(candidate_path, bm)
            if x.shape != y.shape:
                mask_ious.append(0.0)
            else:
                union = np.count_nonzero(x | y)
                mask_ious.append(1.0 if union == 0 else np.count_nonzero(x & y) / union)
    return {
        "schema_version": "1.0.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "same_input": True,
        "baseline_model_versions": baseline.get("model_versions"),
        "candidate_model_versions": candidate.get("model_versions"),
        "leaf_count_agreement": len(left) == len(right),
        "classification_label_agreement": labels_agree,
        "max_confidence_absolute_difference": max(confidence_deltas, default=None),
        "mean_disease_mask_iou": float(np.mean(mask_ious)) if mask_ious else None,
        "min_disease_mask_iou": min(mask_ious) if mask_ious else None,
        "max_severity_percentage_point_difference": max(severity_deltas, default=None),
        "note": "Single-input output agreement is a smoke comparison, not a quality or accuracy evaluation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--min-mask-iou", type=float, default=0.99)
    parser.add_argument("--max-severity-delta-pct", type=float, default=1.0)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output report already exists; choose a new file")
    result = compare(args.baseline.resolve(), args.candidate.resolve())
    result["gates"] = {
        "min_mask_iou": args.min_mask_iou,
        "max_severity_delta_pct": args.max_severity_delta_pct,
        "passed": bool(result["leaf_count_agreement"] and result["classification_label_agreement"]
                        and result["min_disease_mask_iou"] is not None
                        and result["min_disease_mask_iou"] >= args.min_mask_iou
                        and result["max_severity_percentage_point_difference"] is not None
                        and result["max_severity_percentage_point_difference"] <= args.max_severity_delta_pct),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.output), "gates_passed": result["gates"]["passed"]}, indent=2))
    return 0 if result["gates"]["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
