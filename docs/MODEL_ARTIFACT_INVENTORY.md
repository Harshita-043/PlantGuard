# PlantGuard AI model artifact inventory

**Inspection:** 2026-10-27 (Phase 3 staging check). No checkpoint bytes were copied, hashed, or loaded. Windows reports the `ReparsePoint` attribute on each of the four checkpoint paths. Their content hydration is not established, so each checkpoint is treated as unavailable for inference. The small class/configuration files listed below were read and re-hashed safely. No approved image fixtures were found in the repository.

## Required files and present status

| Stage | Exact expected repository path | Additional required files | Current status |
|---|---|---|---|
| SAM 2.1 Hiera Base Plus | `artifacts/sam2/sam2.1_hiera_base_plus.pt` (metadata length 323,606,802 bytes) | `configs/sam2.1/sam2.1_hiera_b+.yaml` is supplied by pinned editable SAM2 package v1.1.0, not checked into this repository. SAM runtime/package absent. | **BLOCKED.** Checkpoint entry is a reparse point; SHA-256 and physical hydration unknown. Package config unavailable until SAM2 is installed. Do not start CPU inference. SAM's official installer recommends WSL on Windows. |
| DINOv2 ViT-S/14 leaf filter | `artifacts/dino_leaf_filter/dino_leaf_filter_v2.pt` (88,300,869 bytes metadata) | No external metadata file is required by the loader. Architecture/head and preprocessing are in `backend/app/ml/architectures/dinov2.py` and `backend/app/ml/adapters/leaf_filter.py`. RGB 224x224, ImageNet mean/std, index 0 negative/index 1 positive, positive threshold 0.5. | **BLOCKED.** Checkpoint entry is a reparse point; SHA-256 unknown. `artifacts/dino_leaf_filter/evaluation/evaluation_results.json` names an older `dino_leaf_filter.pt` from another checkout and cannot validate v2. |
| DINOv2 ViT-B/14 disease classifier | `artifacts/dino_disease/dino_disease_classifier.pt` (346,516,841 bytes metadata) | `artifacts/dino_disease/classes.json` (38 unique labels; actual file SHA-256 matches manifest). Preprocessing: adapter code, RGB 224x224, ImageNet mean/std. | **BLOCKED.** Checkpoint entry is a reparse point; its hash and correspondence to class mapping are unverified. Class-name file itself is verified. |
| SegFormer-B0 PlantSeg | `outputs/segformer_plantseg/best_model/model.safetensors` (14,884,776 bytes metadata) | `outputs/segformer_plantseg/best_model/config.json`; `outputs/segformer_plantseg/best_model/preprocessing.json`; training evidence at `outputs/segformer_plantseg/training_summary.json`. No separate processor directory is used by the current adapter. | **BLOCKED for inference; PARTIAL provenance.** Checkpoint is a reparse point with no verified hash. Config/preprocessing hashes match manifest. The config maps 0=`background`, 1=`diseased_region`, but says image_size 224; preprocessing/training summary say 512. Training summary records 18 epochs and validation disease Dice 0.787 for nvidia/mit-b0, but does not cryptographically establish that the `best_model` checkpoint is that trained output. |
| Reliability / severity metadata | None currently required for inference | Provisional thresholds in `backend/app/ml/ood.py`, `backend/app/ml/severity.py`, and `backend/app/ml/service.py`. No calibration dataset or validated threshold file found. | **PARTIAL.** Configured provisional signals only; calibration and threshold validation are missing. |
| Approved smoke-test images | No repository path found | User-approved leaf crops/images required for model-specific inference. | **MISSING.** No PNG/JPG/JPEG/WebP test fixtures found by `rg --files`. Do not use randomly selected/private images without approval. |

## Safe metadata checksum results

On 2026-10-27, `Get-FileHash -Algorithm SHA256` returned values matching the existing manifest:

- `artifacts/dino_disease/classes.json`: `F8988B3E341ACB2E461EA8DD1CAF9D3492A925405A32BCC57A79113237842AA4`
- `outputs/segformer_plantseg/best_model/config.json`: `2CC0AB73A3B2B2E1007E0A8A60CD340DB6F1953E54B514AD945E07D635493CA7`
- `outputs/segformer_plantseg/best_model/preprocessing.json`: `18A4464B70DD698FAFA5333C54C0BFD21ABD889A29E294C66042064CA49EC4C8`

These are metadata-file checks only. No checkpoint hash is inferred from file size, path, historical report, or the manifest's null value. `artifacts/model_manifest.json` therefore retains null checkpoint SHA-256 values and a blocked status.

## How to establish artifact availability

Run this from the repository root after using OneDrive's **Always keep on this device** option on the four existing checkpoint files, or after arranging a non-destructive copy from the RTX PC. Do not use a checkpoint while its contents remain cloud-only. This check reports attributes and length; it does not load model tensors:

```powershell
$paths = @(
  'artifacts/sam2/sam2.1_hiera_base_plus.pt',
  'artifacts/dino_leaf_filter/dino_leaf_filter_v2.pt',
  'artifacts/dino_disease/dino_disease_classifier.pt',
  'outputs/segformer_plantseg/best_model/model.safetensors'
)
foreach ($path in $paths) {
  $item = Get-Item -Force -LiteralPath $path
  [pscustomobject]@{
    Path = $item.FullName
    Bytes = $item.Length
    ReparsePoint = [bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint)
    IsFile = $item -is [IO.FileInfo]
  }
}
```

A `ReparsePoint = True` result means do not claim physical staging based on this check alone. After the file is confirmed local, use `Get-FileHash -Algorithm SHA256 -LiteralPath <path>` and record the result. Check source and destination hashes before declaring a copy verified. The manifest must only be updated with an observed hash of the actual bytes.

## Loading and source evidence

- SAM loader: `backend/app/ml/adapters/sam_adapter.py`; actual SAM2 automatic mask generator, config from installed package, CPU grid 8 points per side. It has no heuristic fallback. The official SAM2 v1.1.0 install guide recommends WSL with Ubuntu for Windows hosts.
- Leaf filter: `backend/app/ml/adapters/leaf_filter.py`; strict checkpoint load into repository ViT-S/14 binary head.
- Classifier: `backend/app/ml/adapters/disease_classifier.py`; strict checkpoint load and exact 38-label order from `classes.json`.
- Segmenter: `backend/app/ml/adapters/disease_segmentation.py`; local Transformers/safetensors directory, mapping/config validation, preprocessing metadata size 512 and output alignment.
- Pipeline: `backend/app/ml/service.py`; order SAM -> ViT-S filter -> ViT-B classifier -> SegFormer -> reliability/severity/explainability/result.

Current host: Windows 11, Python 3.14.0 active; Python 3.12.2 is installed but has none of torch, torchvision, transformers, safetensors, SAM2, NumPy, or Pillow. The C: free-space query is denied in this environment. No environment was created and no package was installed because free space cannot be established and checkpoints/images are not verified available.

## Exact expected artifact paths for RTX transfer

```text
artifacts/sam2/sam2.1_hiera_base_plus.pt
artifacts/dino_leaf_filter/dino_leaf_filter_v2.pt
artifacts/dino_disease/dino_disease_classifier.pt
artifacts/dino_disease/classes.json
outputs/segformer_plantseg/best_model/model.safetensors
outputs/segformer_plantseg/best_model/config.json
outputs/segformer_plantseg/best_model/preprocessing.json
outputs/segformer_plantseg/training_summary.json
outputs/segformer_plantseg/evaluation/<versioned report, if available>
```

Copy only the listed checkpoints/configuration/mapping files and an approved tiny smoke image. Do not copy datasets or caches. Keep originals on the source PC. SAM package YAML is installed from the pinned SAM2 source dependency rather than copied from an unverified source.
