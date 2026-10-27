"""Run exactly one real model stage under mandatory time and RSS budgets.

This script never substitutes test adapters. It refuses missing manifest hashes
and Windows reparse-point checkpoints before importing a model implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

STAGES = ("sam", "leaf-filter", "classifier", "segmenter")
ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
MANIFEST = ROOT / "artifacts" / "model_manifest.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _artifact(stage: str) -> tuple[Path, str, dict]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ids = {
        "sam": "sam2_hiera_base_plus",
        "leaf-filter": "dinov2_vits14_leaf_filter",
        "classifier": "dinov2_vitb14_classifier",
        "segmenter": "segformer_b0_plantseg",
    }
    model = manifest["models"][ids[stage]]
    checkpoint = model["original_checkpoint"]
    expected = checkpoint.get("sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise RuntimeError("manifest checkpoint SHA-256 is missing; refusing model load")
    path = (ROOT / checkpoint["path"]).resolve(strict=True)
    if not path.is_relative_to(ROOT):
        raise RuntimeError("checkpoint path escapes the repository root")
    try:
        import stat
        if path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise RuntimeError("checkpoint is a Windows reparse point; stage a verified local copy first")
    except AttributeError:
        pass
    actual = _sha256(path)
    if actual.lower() != expected.lower():
        raise RuntimeError("checkpoint SHA-256 does not match the manifest")
    for identity_key in ("preprocessing_identity", "label_mapping_identity"):
        identity = model.get(identity_key, {})
        if isinstance(identity, dict):
            for path_key, hash_key in (("path", "sha256"), ("config_path", "config_sha256")):
                relative = identity.get(path_key)
                if relative:
                    metadata_path = (ROOT / relative).resolve(strict=True)
                    if not metadata_path.is_relative_to(ROOT) or _sha256(metadata_path).lower() != str(identity.get(hash_key, "")).lower():
                        raise RuntimeError(f"manifest {identity_key} file checksum mismatch")
    return path, model["variants"][0]["variant_id"], model


def _worker(stage: str, image_path: Path) -> int:
    sys.path.insert(0, str(BACKEND))
    artifact_path, variant_id, model_meta = _artifact(stage)
    import numpy as np
    import torch
    from PIL import Image

    torch.set_num_threads(min(torch.get_num_threads(), 2))
    with Image.open(image_path) as image_file:
        if image_file.width > 1024 or image_file.height > 1024 or image_file.width * image_file.height > 1_000_000:
            raise RuntimeError("smoke image exceeds 1024px per side or 1 megapixel")
        image = np.asarray(image_file.convert("RGB"), dtype=np.uint8)
    if not image.size:
        raise RuntimeError("smoke image is empty")

    if stage == "sam":
        from app.ml.adapters.sam_adapter import Sam2LeafSegmentationAdapter
        adapter = Sam2LeafSegmentationAdapter(artifact_path=artifact_path, execution_strategy="cpu_bounded")
    elif stage == "leaf-filter":
        from app.ml.adapters.leaf_filter import DinoLeafFilterAdapter
        adapter = DinoLeafFilterAdapter(artifact_path=artifact_path)
    elif stage == "classifier":
        from app.ml.adapters.disease_classifier import DinoDiseaseClassifierAdapter
        adapter = DinoDiseaseClassifierAdapter(artifact_path=artifact_path)
    else:
        from app.ml.adapters.disease_segmentation import SegFormerDiseaseSegmentationAdapter
        adapter = SegFormerDiseaseSegmentationAdapter(artifact_path=artifact_path)
    adapter.artifact_version = variant_id
    if stage == "classifier":
        identity = model_meta["label_mapping_identity"]
        adapter.classes_path = ROOT / identity["path"]
        adapter._class_names = adapter._load_classes()
    started = time.perf_counter()
    try:
        if not adapter.load("cpu"):
            raise RuntimeError(f"load failed ({getattr(adapter, 'load_error_code', None)}): {adapter.last_error}")
        load_ms = round((time.perf_counter() - started) * 1000)
        inference_started = time.perf_counter()
        detail: dict[str, object]
        if stage == "sam":
            proposals = adapter.predict(image)
            if any(np.asarray(p.get("segmentation")).shape != image.shape[:2] for p in proposals):
                raise RuntimeError("SAM output mask dimensions do not match the input image")
            detail = {"candidate_count": len(proposals), "mask_shapes_valid": True}
        elif stage == "leaf-filter":
            output = np.asarray(adapter.predict(adapter.preprocess(image)))
            if output.shape != (1, 2) or not np.isfinite(output).all() or np.any(output < 0) or np.any(output > 1):
                raise RuntimeError("leaf-filter output failed shape/finite/range validation")
            detail = {"input_shape": [1, 3, 224, 224], "output_shape": list(output.shape),
                      "negative_score": float(output[0, 0]), "positive_score": float(output[0, 1]),
                      "threshold": 0.5, "passed_filter": bool(output[0, 1] >= 0.5)}
        elif stage == "classifier":
            labels = adapter.get_class_mapping() or {}
            output = np.asarray(adapter.predict(adapter.preprocess(image)))
            if len(labels) != 38 or set(labels) != set(range(38)) or output.shape != (1, 38):
                raise RuntimeError("classifier mapping/output shape is not the ordered 38-class contract")
            if not np.isfinite(output).all() or np.any(output < 0) or np.any(output > 1) or not np.isclose(output.sum(), 1, atol=1e-3):
                raise RuntimeError("classifier probabilities are not finite normalized values")
            index = int(output[0].argmax())
            detail = {"input_shape": [1, 3, 224, 224], "output_shape": list(output.shape),
                      "class_index": index, "class_name": labels[index], "confidence": float(output[0, index]),
                      "class_mapping_count": len(labels)}
        else:
            labels = adapter.get_class_mapping() or {}
            if labels != {0: "background", 1: "diseased_region"}:
                raise RuntimeError("SegFormer label mapping differs from the expected PlantSeg metadata")
            output = np.asarray(adapter.predict(adapter.preprocess(image), original_shape=image.shape[:2]))
            if output.shape != image.shape[:2] or not np.issubdtype(output.dtype, np.integer) or not np.isin(output, list(labels)).all():
                raise RuntimeError("SegFormer mask dimensions or class IDs are invalid")
            detail = {"input_shape": [1, 3, *adapter.get_preprocessing_spec().target_size],
                      "mask_shape": list(output.shape), "label_mapping": labels,
                      "disease_pixel_count": int(np.count_nonzero(output == 1))}
        inference_ms = round((time.perf_counter() - inference_started) * 1000)
        print(json.dumps({"status": "smoke_passed", "stage": stage, "variant": variant_id,
                          "checkpoint_sha256": model_meta["original_checkpoint"]["sha256"],
                          "runtime": "cpu", "load_ms": load_ms, "inference_ms": inference_ms,
                          "image_dimensions": [int(image.shape[1]), int(image.shape[0])], **detail}, indent=2))
        return 0
    finally:
        adapter.unload()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, required=True,
                        help="Hard wall-clock stop for the isolated stage process")
    parser.add_argument("--max-ram-gb", type=float, required=True,
                        help="Hard per-process RSS stop; reserve memory for Windows")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.max_seconds <= 0 or args.max_ram_gb <= 0:
        parser.error("resource limits must be positive")
    if not args.image.is_file():
        parser.error("--image must be an existing approved local image")
    if args.worker:
        return _worker(args.stage, args.image.resolve())

    try:
        import psutil
    except ImportError:
        parser.error("psutil is required for resource-bounded execution")
    command = [sys.executable, str(Path(__file__).resolve()), "--stage", args.stage,
               "--image", str(args.image.resolve()), "--max-seconds", str(args.max_seconds),
               "--max-ram-gb", str(args.max_ram_gb), "--worker"]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(BACKEND) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, env=env, cwd=ROOT)
    child = psutil.Process(proc.pid)
    deadline = time.monotonic() + args.max_seconds
    max_rss = args.max_ram_gb * (1024 ** 3)
    peak_rss = 0
    reason = None
    while proc.poll() is None:
        try:
            rss = child.memory_info().rss
            peak_rss = max(peak_rss, rss)
        except psutil.Error:
            rss = peak_rss
        if rss > max_rss:
            reason = "process RSS budget exceeded"
            proc.kill()
            break
        if time.monotonic() >= deadline:
            reason = "wall-clock budget exceeded"
            proc.kill()
            break
        time.sleep(0.25)
    output, _ = proc.communicate()
    if reason:
        print(json.dumps({"status": "stopped", "stage": args.stage, "reason": reason,
                          "peak_rss_gb": round(peak_rss / (1024 ** 3), 3)}, indent=2))
        return 3
    if output:
        print(output.rstrip())
    if proc.returncode == 0:
        print(json.dumps({"resource_observation": {"peak_process_rss_gb": round(peak_rss / (1024 ** 3), 3),
                                                   "budget_gb": args.max_ram_gb,
                                                   "time_budget_seconds": args.max_seconds}}))
    return proc.returncode or 0


if __name__ == "__main__":
    raise SystemExit(main())
