"""Run one budgeted baseline/variant inference in a killable child process."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _worker(args: argparse.Namespace) -> int:
    import numpy as np
    from PIL import Image
    from app.ml.service import PlantAnalysisService
    from app.storage.local import LocalFileObjectStorage

    image_path = Path(args.image).resolve(strict=True)
    digest = hashlib.sha256()
    with image_path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    with Image.open(image_path) as opened:
        image = np.asarray(opened.convert("RGB"), dtype=np.uint8)

    cuda_peak = None
    if args.profile == "cuda":
        import torch
        torch.cuda.reset_peak_memory_stats(0)
    storage_dir = Path(args.output) / "private-mask-storage"
    storage = LocalFileObjectStorage(storage_dir)
    service = PlantAnalysisService(device="cpu" if args.profile == "cpu" else "cuda:0",
                                   storage=storage, variant_preference=args.variant_preference)
    result = service.analyze(image)
    if args.profile == "cuda":
        cuda_peak = round(torch.cuda.max_memory_reserved(0) / (1024 ** 3), 3)

    mask_dir = Path(args.output) / "masks"
    mask_dir.mkdir(exist_ok=True)
    leaves = []
    for leaf in result.leaves:
        masks = {}
        for kind, asset in (("disease", leaf.segmentation.mask_asset if leaf.segmentation else None),
                            ("leaf", leaf.leaf_mask_asset)):
            if asset:
                stored = storage.get(asset.storage_key)
                filename = f"leaf_{leaf.leaf_id}_{kind}.png"
                (mask_dir / filename).write_bytes(stored.content)
                masks[kind] = f"masks/{filename}"
        leaves.append({
            "leaf_id": leaf.leaf_id,
            "bounding_box": leaf.bounding_box,
            "classification": leaf.classification.model_dump(mode="json") if leaf.classification else None,
            "segmentation": leaf.segmentation.model_dump(mode="json", exclude={"mask_asset"}) if leaf.segmentation else None,
            "severity": leaf.severity.model_dump(mode="json") if leaf.severity else None,
            "masks": masks,
        })
    manifest = json.loads((Path(__file__).resolve().parents[2] / "artifacts" / "model_manifest.json").read_text(encoding="utf-8"))
    artifact_hashes = {model_id: model["original_checkpoint"].get("sha256")
                       for model_id, model in manifest["models"].items()}
    report = {
        "schema_version": "1.0.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": result.status,
        "profile": args.profile,
        "variant_preference": args.variant_preference,
        "input_sha256": digest.hexdigest(),
        "source_revision": manifest.get("source_revision"),
        "artifact_sha256": artifact_hashes,
        "model_versions": result.model_versions,
        "stage_timings_ms": result.stage_timings_ms,
        "model_load_timings_ms": result.model_load_timings_ms,
        "processing_time_ms": result.processing_time_ms,
        "peak_vram_reserved_gb": cuda_peak,
        "leaves": leaves,
        "warnings": [warning.code for warning in result.warnings],
        "validation_status": "inference_smoke_only_no_quality_ground_truth",
    }
    (Path(args.output) / "benchmark.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


def _nvidia_memory_gb() -> float:
    output = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        text=True, timeout=2,
    )
    values = [int(line.strip()) for line in output.splitlines() if line.strip()]
    if not values:
        raise RuntimeError("nvidia-smi reported no NVIDIA devices")
    return max(values) / 1024


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="New, clean output directory; existing paths are refused")
    parser.add_argument("--profile", choices=("cpu", "cuda"), required=True)
    parser.add_argument("--variant-preference", choices=("original", "automatic"), default="original")
    parser.add_argument("--max-seconds", type=float, required=True, help="Hard child-process timeout")
    parser.add_argument("--max-ram-gb", type=float, required=True, help="Parent kills the worker above this RSS limit")
    parser.add_argument("--max-vram-gb", type=float, help="Required for CUDA; worker is killed when nvidia-smi exceeds it")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return _worker(args)
    if args.max_seconds <= 0 or args.max_ram_gb <= 0 or (args.profile == "cuda" and (args.max_vram_gb is None or args.max_vram_gb <= 0)):
        parser.error("Positive time and RAM budgets are required; CUDA also requires a positive VRAM budget")
    if args.output.exists():
        parser.error("Output directory already exists; choose a clean new directory")

    from app.ml.runtime import collect_runtime_capabilities
    capabilities = collect_runtime_capabilities(profile=args.profile)
    if capabilities.ram_available_gb is not None and args.max_ram_gb > capabilities.ram_available_gb:
        parser.error("RAM budget exceeds currently available system memory")
    if args.profile == "cuda" and capabilities.cuda["available"] is not True:
        parser.error("BLOCKED: PyTorch does not report a usable NVIDIA CUDA runtime")
    required_models = ("sam2_hiera_base_plus", "dinov2_vits14_leaf_filter", "dinov2_vitb14_classifier", "segformer_b0_plantseg")
    blocked = [name for name in required_models if capabilities.model_compatibility[name][args.profile]["status"] != "prerequisites_present"]
    if blocked:
        parser.error("BLOCKED: model runtime prerequisites unavailable: " + ", ".join(blocked))
    if args.profile == "cuda":
        total_vram = capabilities.cuda.get("total_vram_gb")
        available_vram = capabilities.cuda.get("available_vram_gb")
        if total_vram is not None and args.max_vram_gb > total_vram:
            parser.error("VRAM budget exceeds detected total device VRAM")
        if available_vram is not None and args.max_vram_gb > available_vram:
            parser.error("VRAM budget exceeds currently available VRAM; account for existing use")
        try:
            _nvidia_memory_gb()
        except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as exc:
            parser.error(f"BLOCKED: NVIDIA memory monitor unavailable ({type(exc).__name__})")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    child_args = [sys.executable, str(Path(__file__).resolve()), "--worker", "--image", str(args.image.resolve()),
                  "--output", str(output), "--profile", args.profile,
                  "--variant-preference", args.variant_preference,
                  "--max-seconds", str(args.max_seconds), "--max-ram-gb", str(args.max_ram_gb)]
    if args.max_vram_gb is not None:
        child_args.extend(["--max-vram-gb", str(args.max_vram_gb)])
    env = os.environ.copy()
    env["PLANTGUARD_INFERENCE_PROFILE"] = args.profile
    backend_dir = str(Path(__file__).resolve().parents[1])
    env["PYTHONPATH"] = backend_dir + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    log_path = output / "worker.log"
    with log_path.open("w", encoding="utf-8") as log:
        child = subprocess.Popen(child_args, cwd=backend_dir, env=env, stdout=log, stderr=subprocess.STDOUT)
        started = time.monotonic()
        peak_ram_gb = 0.0
        failure = None
        try:
            import psutil
            process = psutil.Process(child.pid)
        except ImportError:
            child.kill()
            parser.error("BLOCKED: psutil is required to enforce the RAM budget")
        while child.poll() is None:
            if time.monotonic() - started > args.max_seconds:
                failure = "timeout_budget_exceeded"
                child.kill()
                break
            try:
                peak_ram_gb = max(peak_ram_gb, process.memory_info().rss / (1024 ** 3))
                if args.profile == "cuda" and _nvidia_memory_gb() > args.max_vram_gb:
                    failure = "vram_budget_exceeded"
                    child.kill()
                    break
            except (psutil.Error, OSError, subprocess.SubprocessError, ValueError, RuntimeError):
                pass
            if peak_ram_gb > args.max_ram_gb:
                failure = "ram_budget_exceeded"
                child.kill()
                break
            time.sleep(0.25)
        child.wait()

    if failure or child.returncode != 0:
        report = {"status": "blocked_or_failed", "reason": failure or "inference_failed",
                  "profile": args.profile, "peak_ram_gb_observed": round(peak_ram_gb, 3)}
        (output / "benchmark_status.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report))
        return 2
    report_path = output / "benchmark.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["peak_ram_gb_observed"] = round(peak_ram_gb, 3)
    report["budget"] = {"max_seconds": args.max_seconds, "max_ram_gb": args.max_ram_gb,
                        "max_vram_gb": args.max_vram_gb}
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "completed", "report": str(report_path),
                      "processing_time_ms": report["processing_time_ms"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
