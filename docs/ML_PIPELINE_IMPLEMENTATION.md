# PlantGuard AI model pipeline implementation

**Implementation status:** service and CPU-safe contract path implemented. Real artifact inference is **BLOCKED on this Vivobook** by the missing PyTorch/Transformers/SAM2 runtime, incompatible active Python 3.14 ML setup, and CUDA-only smoke requirement for the requested SAM 2.1 Base Plus GPU validation. This document distinguishes code behavior from completed model verification.

## Current service behavior

`backend/app/ml/service.py` is the device-neutral application boundary. It validates an RGB `uint8` image, admits one inference at a time process-wide, loads each adapter only when its stage starts, and unloads it before the next model stage. Its order is fixed:

1. `Sam2LeafSegmentationAdapter` runs the official SAM2 automatic mask generator with the Hiera Base Plus checkpoint/config. It filters invalid size/aspect-ratio proposals and ranks the remaining masks. It never creates a color heuristic or central crop. No proposals yields `NO_LEAF_FOUND`.
2. `DinoLeafFilterAdapter` scores each candidate crop using the ViT-S/14 checkpoint. A candidate passes at positive probability `>= 0.5`; this is the existing adapter threshold. Non-finite, wrong-shape, or non-normalized outputs fail.
3. `DinoDiseaseClassifierAdapter` classifies accepted crops with ViT-B/14. The ordered 38 labels from `artifacts/dino_disease/classes.json` are the source of truth. Checkpoint metadata, if present, must agree. Invalid class maps fail closed.
4. `SegFormerDiseaseSegmentationAdapter` loads the local safetensors directory and predicts PlantSeg IDs `0=background`, `1=diseased_region`. The adapter requires both config and preprocessing JSON and checks `id2label`, `label2id`, and preprocessing mappings agree. It preprocesses at 512×512 using its metadata and upsamples logits to the crop dimensions before argmax. The pipeline masks disease pixels outside the SAM leaf mask.
5. The service assembles typed leaf/classification/segmentation/severity/attention outputs, stage durations, model versions, warnings, and mask asset pointers when storage is injected.

The SAM adapter expects the official package config name `configs/sam2.1/sam2.1_hiera_b+.yaml`. The pinned SAM2 source distribution carries this config; the adapter verifies it exists under the installed package before model construction. SAM2's builder accepts the config name through Hydra and loads the supplied checkpoint [official builder](https://github.com/facebookresearch/sam2/blob/main/sam2/build_sam.py). Its installation instructions require installing the SAM2 source package and building its extension as appropriate for the host [official installation guide](https://github.com/facebookresearch/sam2/blob/main/INSTALL.md). An optional authenticated remote client exists in `backend/app/ml/remote.py`; it sends no images unless the remote profile, HTTPS endpoint, token and explicit deployment authorization are configured. Unavailable local inference otherwise returns a typed error.

`backend/app/ml/smoke_check.py` now prints artifact/runtime readiness metadata only. It deliberately does not load checkpoints. The GPU script below is the real SAM inference smoke check.

## Contracts and errors

Public typed output structures are in `backend/app/schemas/inference.py`; candidate masks use the framework-neutral `LeafCandidate` dataclass in `backend/app/ml/contracts.py`. Model-facing inputs are checked for exact shapes and finite floats: DINO inputs `(1,3,224,224)`, SegFormer `(1,3,512,512)`, SAM RGB `uint8` `(H,W,3)`. Output validation checks probability sums/ranges, candidate mask/bbox/score, class mappings and IDs, and segmenter mask dimensions. Encoded and array images are limited to 8192 pixels per side and 32 million pixels.

Typed error codes in `backend/app/ml/errors.py` include `missing_artifact`, `unsupported_runtime`, `invalid_image`, `invalid_model_output`, `no_leaf_found`, `no_disease_mask`, `timeout`, and `model_failure`. The configured timeout bounds waiting for inference capacity; it cannot interrupt a model call already running. A zero-valued SegFormer mask is accepted as a possible healthy/no-lesion result; a missing mask output is an error.

Each model is held only during its own stage. A process-wide bounded semaphore prevents multiple service instances from loading competing checkpoints concurrently. Logs include stage, model version, runtime and duration/error code. They do not include image bytes or user secrets. The authenticated API upload route invokes the typed inference service, stores the structured result in `analyses.result_data`, and returns it to the owner. Inference failures persist a failed lifecycle state. Processing is currently inline in the request worker thread; durable job queuing and real-artifact API execution remain deployment validation work.

## Reliability, severity and explainability limits

- Probability finiteness, dimensions, ranges, sums, mapping and mask geometry are hard reliability checks. Normalized entropy and selected-class confidence are emitted separately with provisional configurable thresholds. Calibration is incomplete; these signals are not a validated OOD detector. Details: [RELIABILITY_AND_OOD.md](RELIABILITY_AND_OOD.md).
- Severity intersects SegFormer class-1 pixels with the selected SAM leaf mask; its denominator is exactly nonzero valid leaf pixels. Pixel counts accompany the percentage. Empty or misaligned masks make severity explicitly unavailable. The default 15%/35% categories remain provisional. Details: [SEVERITY_METHOD.md](SEVERITY_METHOD.md).
- DINOv2 ViT-B/14 provides a class-specific gradient-weighted final-block attention visualization. It is not causal and its quality has not been evaluated. Attribution failures leave classification intact and set explanation status to unavailable. Details: [EXPLAINABILITY.md](EXPLAINABILITY.md).
- Recommendations remain empty. No treatment advice is generated from an unreviewed source.
- Summary health score is descriptive only and must not be represented as a calibrated plant-health probability.

## Artifact and runtime configuration

API dependencies remain in `backend/requirements.txt`. Install optional model dependencies from `backend/requirements-ml.txt` in a dedicated Python 3.12 environment, selecting the matching PyTorch CPU/CUDA wheel index for the target host. Install the matching PyTorch wheel first; the pinned SAM2 dependency is editable so its official config files remain resolvable. The active Vivobook Python 3.14 environment has no `torch`, `torchvision`, `transformers`, or `safetensors`; no model weights were loaded in this implementation turn.

Runtime variables in `backend/.env.example`:

- `PLANTGUARD_DEVICE=auto` selects CUDA when PyTorch reports CUDA; otherwise CPU. Explicit unsupported devices fail.
- `PLANTGUARD_INFERENCE_TIMEOUT_SECONDS=120` bounds admission wait.
- `PLANTGUARD_MAX_CANDIDATES=8` bounds SAM proposals processed per image (valid range 1–32).
- `PLANTGUARD_SAM_STRATEGY=auto` uses the bounded 8×8 grid on CPU and the 32×32 grid on CUDA. The `cuda_dense` option requires CUDA; `cpu_bounded` uses 8×8.
- `PLANTGUARD_SAM_CONFIG` names the SAM2 package-relative config. Absolute paths and parent traversal are rejected.

SegFormer `config.json` declares `image_size: 224`, while the training summary and preprocessing metadata say 512. The service honors the saved preprocessing metadata and checks label mapping; the input-size discrepancy still requires validation against the original training pipeline before release.

## CPU-safe checks and status

Run from `backend/`:

```powershell
$env:PYTHONPATH = "."
pytest -q app/tests/test_inference_service.py app/tests/test_ml_foundations.py app/tests/test_model_inference_smoke.py app/tests/test_real_model_inference.py app/tests/test_services.py
```

**Vivobook Phase 1 result on 2026-10-26:** `34 passed, 5 skipped, 4 warnings in 1.48s` for the original selected command. Phase 2 CPU-safe tests are recorded in the new reliability, severity, and explainability test module. These mocked/contract checks do not establish checkpoint accuracy, segmentation quality, OOD calibration, or explanation quality.

## RTX 5060 SAM smoke check

Run only on the RTX 5060 host after creating the dedicated environment, installing PyTorch with a supported CUDA build, and installing the pinned SAM2 release. For SAM2's package config lookup, use its official editable source install for the pinned `v1.1.0` release; see the official install guide linked above. Verify the checkpoint checksum before running. From the repository root:

```powershell
Set-Location backend
$env:PYTHONPATH = "."
$env:PLANTGUARD_DEVICE = "cuda:0"
$env:PLANTGUARD_SAM_STRATEGY = "cuda_dense"
python scripts/sam2_gpu_smoke.py --image ..\plant.jpg
```

The command checks CUDA availability, loads only SAM2, runs its real automatic mask generator, validates candidate provenance, prints device/model/candidate count/timing, then unloads the model. It does not test the DINO or SegFormer stages. Do not claim it passed until its output is observed on the RTX host.

## Test and integration gaps

- **BLOCKED:** real SAM2 CUDA load/inference and memory/latency on RTX 5060; SAM package config and checkpoint compatibility have not been exercised here.
- **BLOCKED:** real DINOv2 and SegFormer inference because ML packages are not installed in the active environment. CPU model execution can be tried in the dedicated environment, but was not run.
- **BLOCKED:** accuracy, preprocessing equivalence with training, and OOD/severity calibration because training sources and held-out validation datasets are not available in this repository.
- **Not implemented:** API queue/result persistence, user-scoped mask retrieval, remote inference, video tracking, disease recommendation knowledge base, and causal explainability. Frontend redesign was not started.
