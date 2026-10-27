# CPU model smoke tests

**Environment update on 2026-10-27:** `C:\PlantGuardEnvs\plantguard-vision-cpu` is verified with Python 3.12.2, Torch 2.6.0+cpu, torchvision 0.21.0+cpu, Transformers 4.57.6, safetensors 0.8.0, NumPy 2.3.4, Pillow 12.3.0, and backend requirements. `pip check` and DINO/SegFormer import checks passed. **No real model stage was run.** Checkpoint files remain reparse points with unverified hashes; no checkpoint was opened, hashed, copied, or deserialized. This is an environment pass only, not a model pass.

## Current per-stage result

| Stage | Artifact/integrity | Load | Real inference | Contract facts checked | Status |
|---|---|---|---|---|---|
| SAM 2.1 Hiera Base Plus | Expected file path/length metadata exists; reparse point; SHA missing. SAM package absent. | Not attempted. | Not attempted. | Source code uses real SAM2 automatic mask generation; no heuristic. Config is package-supplied. | **BLOCKED**. On Windows, SAM2 officially recommends WSL. Do not run CPU SAM before checking RAM and applying a time/RSS budget. |
| DINOv2 ViT-S/14 leaf filter | Expected file path/length metadata exists; reparse point; SHA missing. | Not attempted. | Not attempted. | Code contract is 224x224 RGB/ImageNet normalization and `[negative, positive]`; positive threshold 0.5. Historical evaluation report refers to a different v1 file. | **BLOCKED**. No v2 quality claim. |
| DINOv2 ViT-B/14 classifier | Expected file path/length metadata exists; reparse point; SHA missing. `classes.json` readable, 38 unique classes, SHA matches manifest. | Not attempted. | Not attempted. | Code expects 224x224 RGB/ImageNet normalization and 38 probabilities; class index/name association comes from checked `classes.json`. | **BLOCKED**. Checkpoint-to-mapping provenance and inference remain unverified. |
| SegFormer-B0 PlantSeg | Expected file path/length metadata exists; reparse point; SHA missing. Config/preprocessing files readable and hashes match manifest. | Not attempted. | Not attempted. | Mapping cross-checks as 0=`background`, 1=`diseased_region`; output aligned to original image. Preprocessing size 512 conflicts with config `image_size` 224. Training summary records an 18-epoch run and Dice 0.787 but checkpoint identity is not proven. | **BLOCKED**. Do not calculate real severity until trained checkpoint and mapping lineage are confirmed. |

No latency, process memory, or prediction score was measured. SAM2, hydra-core, iopath, and OpenCV remain absent from the CPU environment. Python 3.14 is the separate application environment; it is not the supported model runtime.

## What is tested locally

The isolated model runner `backend/scripts/cpu_model_stage_smoke.py` executes exactly one real adapter at a time, compares the checkpoint and any referenced label/preprocessing metadata hashes to the manifest before model imports, refuses Windows reparse-point checkpoints, and requires caller-supplied wall-time and process-RSS caps. It never injects fake adapters. It reports only a smoke result (load/inference, shapes, mapping, scores/counts); that does not measure quality.

CPU-safe automated tests run from `backend/`:

```powershell
$env:PYTHONPATH = "."
python -m pytest -q app/tests/test_inference_service.py app/tests/test_device_variants.py app/tests/test_ml_foundations.py app/tests/test_reliability_severity_explainability.py
```

Observed during this phase: `71 passed`. These are contract tests with explicitly injected unit-test adapters; they do not load the checkpoint files and are not real model smoke tests. `python -m py_compile scripts/cpu_model_stage_smoke.py` checks the new runner without importing any model package.

## Manual CPU run after artifacts and environment are ready

Use one small, approved test image (maximum 1024 pixels per side and 1 megapixel). Run from the local, non-OneDrive workspace root. First verify all checkpoint copies have real bytes and are not reparse points, then compute manifest hashes (about 774 MB total checkpoint bytes will be read):

```powershell
python backend/scripts/hash_model_manifest.py --root . --max-total-bytes 1000000000
```

Expected output: `status` is `checksums_recorded`, four or more registered artifact entries, and `bytes_hashed` below 1,000,000,000. If any path is missing, is still a reparse point, or exceeds this byte limit, stop and resolve staging; do not add `--allow-reparse-points` for placeholders. Inspect the resulting manifest and retain a backup before any further updates.

Activate/install the CPU environment as described in [LOCAL_ML_ENVIRONMENT.md](LOCAL_ML_ENVIRONMENT.md). Then run **one command at a time** from repository root, changing the image path to the approved local fixture:

```powershell
backend\.venv-ml-cpu\Scripts\python.exe backend\scripts\cpu_model_stage_smoke.py --stage leaf-filter --image C:\PlantGuardData\approved-leaf.jpg --max-seconds 120 --max-ram-gb 4
backend\.venv-ml-cpu\Scripts\python.exe backend\scripts\cpu_model_stage_smoke.py --stage classifier --image C:\PlantGuardData\approved-leaf.jpg --max-seconds 180 --max-ram-gb 7
backend\.venv-ml-cpu\Scripts\python.exe backend\scripts\cpu_model_stage_smoke.py --stage segmenter --image C:\PlantGuardData\approved-leaf.jpg --max-seconds 180 --max-ram-gb 5
```

These are initial per-process ceilings, not measured requirements. Before each command, ensure Windows has at least 4 GB available beyond the selected process cap; otherwise lower the cap or stop. A successful result prints `status: smoke_passed`, a matching checkpoint hash, CPU runtime, load/inference milliseconds, shape and class/pixel checks, plus peak RSS. It does not mean accuracy is validated. Exit 3 means the supervisor killed that one process after its time or memory cap; record it as BLOCKED/RESOURCE-LIMIT and do not immediately rerun with larger limits.

SAM CPU is deliberately not in the recommended run list. First use the RTX 5060 smoke command in `docs/DEVICE_AND_OPTIMIZATION_GUIDE.md`. Attempt CPU SAM only after measuring actual available memory and setting a written time/RSS budget, using the runner's `--stage sam` limits. The runner terminates the worker on budget overrun, but SAM CPU practicality remains unproven.

## Result recording

After each actual run, record the output JSON, package freeze, checkpoint SHA-256, image provenance (without publishing the image), host, wall time and peak RSS in the table above or an attached private report. A successful load without inference is not a pass; smoke inference is not an accuracy result. Do not mark an optimized variant validated from these commands.
