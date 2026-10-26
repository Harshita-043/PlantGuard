# Device profiles, variants, optimization, and GPU handoff

**Status:** safe laptop-side code and CPU contract checks are complete. Real model runtime and CUDA validation are blocked on this host. No original checkpoint was loaded, converted, or modified in this phase.

## Runtime profiles

`PLANTGUARD_INFERENCE_PROFILE` selects `auto`, `cpu`, `cuda`, or `remote`. `auto` honors the legacy `PLANTGUARD_DEVICE` setting and otherwise uses CUDA only when PyTorch reports a usable NVIDIA CUDA runtime; integrated graphics are not treated as CUDA. Explicit `cuda` stays CUDA and produces a typed capability failure if the installed build/driver/device is unusable. It does not fall through to CPU. The current four adapters execute through the PyTorch CPU or CUDA path; ONNX Runtime, OpenVINO, and DirectML are diagnostics only, not usable PlantGuard model backends.

Runtime reporting is read-only and does not load checkpoints. It reports OS/architecture, CPU, RAM when `psutil` is available, Python and inference package versions, PyTorch CUDA build, available NVIDIA device/VRAM where detectable, per-model prerequisites, memory limits, configured concurrency, and remote service status. Static prerequisites do not prove a model loads or runs; fields mark runtime validation as `not_smoke_tested` until a real smoke run is recorded.

The protected `GET /api/admin/runtime` endpoint uses the bearer value configured by `PLANTGUARD_DIAGNOSTICS_TOKEN`. When unset the endpoint returns 404; invalid credentials return 401. It does not return secrets, remote URLs, or artifact filesystem paths. It reports configured candidates and a last-selected variant ID, if a service has selected one. The authenticated image upload route now invokes the configured `FullScanResult` inference service after recording the scan. It returns and persists the typed result on success; model/runtime errors persist `failed` and return a typed error response. The model call runs in a worker thread and shares the bounded inference slot. A durable background queue is still absent, so deployment request timeouts and worker restart behavior need review before production.

Relevant `.env` keys are listed in `backend/.env.example`: `PLANTGUARD_INFERENCE_PROFILE`, legacy `PLANTGUARD_DEVICE`, CPU/CUDA memory limits, and concurrency. A configured memory cap is enforced only when the registry has a measured peak-memory result for that variant; absent measurements fail closed with `resource_limit`.

## Variant selection and immutability

`artifacts/model_manifest.json` registers the original model variants for SAM 2.1 Hiera Base Plus, DINOv2 ViT-S/14 leaf filtering, DINOv2 ViT-B/14 classification, and SegFormer-B0 PlantSeg. Each record has checkpoint/source identity, preprocessing and label-map identities, backend/device/precision/quantization requirements, validation and benchmark slots, creation metadata, and a rollback target. Unknown values remain null or explicitly unverified.

Checkpoint files in this checkout are OneDrive reparse points. Their hashes are **BLOCKED** here because C: reports no free space; this turn did not read/hydrate those checkpoints. The small DINO label map and SegFormer config/preprocessing files have recorded SHA-256 values. Run the bounded streaming hash script on a host with local artifact access before any real model load:

```powershell
Set-Location backend
$env:PYTHONPATH = "."
python scripts/hash_model_manifest.py --root .. --max-total-bytes 1000000000
```

The script refuses cloud/reparse points unless `--allow-reparse-points` is explicitly passed. Use that option only when the files are intentionally hydrated and the host has sufficient disk headroom. It reads in 8 MiB chunks, loads no tensors, and writes only the manifest. Checkpoints are not overwritten.

At inference, a baseline can be selected only when runtime prerequisites are present, original and variant file checksums match, and associated mapping/config checksums match. An optimized variant is considered only when its manifest says `validation.status=validated`, the selected runtime has a `verified` compatibility result, required quality/benchmark metadata is present, and any configured memory limit is met by recorded peak usage. Baseline benchmarking can force `--variant-preference original`. Selection is deterministic. The registry never guesses a hash or marks an optimized variant validated based on package presence.

## Laptop optimization assessment

No conversion, compilation, quantization, or repeated benchmark was run. The active Python 3.14 environment lacks Torch, torchvision, Transformers, safetensors, SAM2, ONNX Runtime, and OpenVINO. Probe support without loading checkpoints:

```powershell
Set-Location backend
$env:PYTHONPATH = "."
python scripts/optimization_probe.py --output ..\outputs\optimization_probe.json
```

Current variant dispositions:

| Variant family | Status | Evidence / next gate |
| --- | --- | --- |
| Original PyTorch FP32 checkpoints | **BLOCKED** for execution; registered baseline | Checkpoint hashes and compatible runtime need verification. Original files remain untouched. |
| SAM dynamic INT8 | **UNSUPPORTED** by the current adapter | No quantized SAM path; operator, mask-quality, and resource compatibility unverified. |
| SAM ONNX/OpenVINO | **UNSUPPORTED** by the current adapter | No export/runtime path is present; architecture/operator support has not been demonstrated. |
| DINO dynamic INT8 | **BLOCKED** on this laptop | No Torch runtime, calibration set, representative dataset, or classifier agreement evaluation. |
| SegFormer dynamic INT8 | **BLOCKED** on this laptop | No Torch runtime, operator check, PlantSeg test set, mask agreement or severity-drift evaluation. |
| DINO/SegFormer CUDA FP16 | **BLOCKED** on this laptop | Requires RTX runtime and original-output comparison for class confidence, masks, severity, latency, and VRAM. |
| ONNX Runtime/OpenVINO variants | **BLOCKED** on this laptop | Backends are not installed. Installation alone will not establish architecture/operator compatibility. |
| **NOT BENEFICIAL** | None classified | No candidate has been measured, so no optimization can be called beneficial or not beneficial yet. |
| **VERIFIED** optimized variants | None | No optimized artifacts or passing validation gates exist. |

Do one candidate at a time on the target runtime, starting with original checkpoints. Preserve the original baseline report. The comparison script reports same-input label agreement, confidence drift, disease-mask IoU, and mask-based severity difference. Its default gates (label/leaf count agreement, mask IoU >= 0.99, severity difference <= 1 percentage point) are engineering regression gates for screening; they are not clinical thresholds and a one-image smoke comparison is not a validation dataset. A candidate still requires the agreed representative held-out dataset and independent quality review before its manifest status can be changed to `validated`.

## Optional remote GPU profile

Remote inference is absent by default. Sending an image requires all of the following: `PLANTGUARD_INFERENCE_PROFILE=remote`, an HTTPS origin in `PLANTGUARD_REMOTE_INFERENCE_URL`, `PLANTGUARD_REMOTE_INFERENCE_TOKEN`, and explicit deployment authorization `PLANTGUARD_REMOTE_IMAGE_UPLOAD_AUTHORIZED=true`. Configuration is held as a secret where appropriate; logs and diagnostics omit token and URL. Remote inference accepts one encoded PNG request at `/v1/inference`, requires bearer authentication, caps encoded images at `PLANTGUARD_REMOTE_MAX_IMAGE_BYTES` (10 MiB default, 50 MiB maximum), caps JSON responses at 2 MiB, applies a request timeout and bounded concurrency, verifies TLS, and refuses redirects so the bearer token cannot be forwarded to another host. The authenticated diagnostics probe sends only `GET /health`, never an image.

An endpoint must return the versioned `FullScanResult` contract and implement the same ordered PlantGuard stages. The upload route uses `RemoteInferenceClient` only when the remote profile, HTTPS URL, bearer token, and explicit deployment authorization are configured. Image upload to a remote endpoint remains disabled otherwise.

## RTX 5060 execution checklist

Run in a dedicated Python 3.12 ML environment, with PyTorch built for the installed NVIDIA driver/CUDA combination. Use approved, non-sensitive fixtures and record their source/split. Do not run these commands until the output directory is confirmed new and resource budgets are chosen from the live device report.

### 1. Establish environment and checksums

From a repository checkout on the RTX host:

```powershell
Set-Location backend
$env:PYTHONPATH = "."
python scripts/gpu_environment_check.py --require-cuda --output ..\outputs\gpu_validation\environment.json
python scripts/hash_model_manifest.py --root .. --max-total-bytes 1000000000
```

Expected environment output includes `cuda.available: true`, NVIDIA model, total/free VRAM where supported, installed package versions, and `prerequisites_present` per model. A nonzero check exit means **BLOCKED**; do not continue to a model benchmark. The checksum command prints manifest path, artifact count, and bytes read. Inspect the generated manifest and verify checksums before inference.

### 2. Run the original baseline once, under budgets

Use a known approved image and a new output folder. Example limits below are placeholders; set them no higher than the free RAM/VRAM reported in step 1, reserving capacity for Windows and other workloads.

```powershell
python scripts/model_benchmark.py `
  --image ..\test.jpg `
  --output ..\outputs\gpu_validation\baseline-original `
  --profile cuda `
  --variant-preference original `
  --max-seconds 240 `
  --max-ram-gb 12 `
  --max-vram-gb 6
```

Expected success writes `benchmark.json`, `worker.log`, and binary leaf/disease mask PNGs under the new directory. The report includes checkpoint hashes/variant IDs, model load time, stage and total latency, sampled peak RAM, CUDA peak reserved VRAM, predictions, and severity pixel counts. The parent terminates the worker on timeout or observed RAM/VRAM budget overrun. Resource sampling is approximate; retain a margin. Exit code 2 or `benchmark_status.json` means the run was blocked/failed, not passed.

### 3. Probe and evaluate one supported candidate

```powershell
python scripts/optimization_probe.py --output ..\outputs\gpu_validation\optimization-probe.json
```

Only proceed when a model-specific candidate has an actual supported export/runtime path and an approved validation dataset. The probe does not convert or load models. For an implemented candidate, run `model_benchmark.py` once with `--variant-preference automatic` and a separate clean output directory, then compare:

```powershell
python scripts/compare_benchmark_reports.py `
  --baseline ..\outputs\gpu_validation\baseline-original\benchmark.json `
  --candidate ..\outputs\gpu_validation\candidate\benchmark.json `
  --output ..\outputs\gpu_validation\comparison.json
```

Expected report includes class agreement, confidence difference, disease-mask IoU, and mask-based severity percentage-point difference. A gate failure rejects the candidate. Gate pass on one image only permits continuation to full validation; it does not approve a production variant. Record dataset/split, source/runtime versions, repeated latency statistics, peak memory, and quality metrics in the manifest before setting `validation.status=validated` and `compatibility_results[profile]=verified`.

### 4. Export only approved variants

```powershell
python scripts/export_variant_bundle.py --output ..\outputs\gpu_validation\variant-bundle
```

The script requires a new output directory, refuses unvalidated or checksum-mismatched optimized artifacts, copies only validated optimized files, writes a manifest and `SHA256SUMS.txt`, and never includes or modifies original checkpoints. If there are no approved optimized variants, the bundle states that none were exported. Merge `variant-bundle\artifacts\` into the repository while preserving existing artifact files, verify `SHA256SUMS.txt`, and retain the manifest's original checkpoint paths as rollback targets. Keep the reports, environment record, source revision, fixtures/split metadata, and checksum file together as the GPU handoff.

## Remaining limitations

- The checkpoint paths are present in this checkout, but Windows marks all four weight files as OneDrive reparse points. Their content hashes remain unset in the manifest, so integrity-gated variant selection will refuse to load them until the actual files are hydrated/copied to local storage and hashed. This host's available disk could not be read through the current environment.
- Actual CUDA driver/PyTorch/SAM2 extension compatibility, SAM masks, full pipeline latency, CPU/CUDA output agreement, GPU peak memory, and FP16 behavior are **BLOCKED** pending RTX execution.
- There are no optimized variants, no classification/segmentation benchmark suite, and no representative validation data here. Nothing is classified **NOT BENEFICIAL** because no candidate was benchmarked.
- Model provenance and SegFormer preprocessing-size reconciliation remain outstanding from the earlier artifact audit. Variant manifests must preserve those unknowns rather than infer them.
- API scan inference and typed result persistence are now connected. Real-artifact API execution, durable job processing across server restarts, and production request-timeout behavior still need validation.
