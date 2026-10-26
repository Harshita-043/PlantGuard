# PlantGuard AI model artifact inventory

**Inspected:** 2026-10-27. Artifact contents were not loaded or hashed during this audit. The four checkpoint paths below exist as filesystem entries and Windows marks them as reparse points. Sizes are metadata only. The owner reports model training/testing on an RTX 5060; that report is not independently reproduced here. SAM 2.1 is a pretrained foundation model, not a PlantGuard-trained checkpoint.

## Active pipeline artifacts

| Order | Model and repository path | Metadata/contract found in code | Current verification |
| --- | --- | --- | --- |
| 1 | SAM 2.1 Hiera Base Plus: `artifacts/sam2/sam2.1_hiera_base_plus.pt` (323,606,802 bytes) | SAM2 automatic mask generator, config name `configs/sam2.1/sam2.1_hiera_b+.yaml` from the editable pinned SAM2 package; adapter emits real SAM masks and refuses unloaded inference. | **PARTIAL.** File path/size present; reparse point; SHA-256 null; package/config/checkpoint compatibility and GPU inference not tested here. |
| 2 | DINOv2 ViT-S/14 leaf filter: `artifacts/dino_leaf_filter/dino_leaf_filter_v2.pt` (88,300,869 bytes) | `backend/app/ml/adapters/leaf_filter.py`; RGB 224×224, ImageNet mean/std, output index 0 negative and 1 positive; pipeline accepts positive probability ≥0.5. Adapter constructs a ViT-S/14 binary head and strict-loads the checkpoint. | **PARTIAL.** Owner-reported RTX testing; file reparse point and SHA-256 null. Existing historical evaluation file is for v1, not proof for selected v2. |
| 3 | DINOv2 ViT-B/14 classifier: `artifacts/dino_disease/dino_disease_classifier.pt` (346,516,841 bytes) | `backend/app/ml/adapters/disease_classifier.py`; RGB 224×224, ImageNet normalization; ordered 38 class names from `artifacts/dino_disease/classes.json`, validated against head/output. | **PARTIAL.** Owner-reported RTX testing; file reparse point and SHA-256 null. No reproduced real checkpoint output. |
| 4 | SegFormer-B0 PlantSeg: `outputs/segformer_plantseg/best_model/model.safetensors` (14,884,776 bytes) | `config.json`: `id2label`/`label2id` map 0=`background`, 1=`diseased_region`, `image_size=224`; `preprocessing.json`: size 512, ImageNet mean/std and matching class map. Adapter uses preprocessing size 512 and checks mapping agreement. | **PARTIAL.** Training summary reports 18 epochs and validation Dice ≈0.787 (historical metadata, not reproduced). Owner-reported RTX testing; checkpoint reparse point and SHA-256 null. Config/preprocessing size disagreement (224 vs 512) remains to reconcile with training-time preprocessing. |

## Manifest and integrity state

`artifacts/model_manifest.json` is the runtime selection source. It registers the above original variants and small label/config identities. The original checkpoint `sha256` values are null with `blocked_cloud_placeholder`; there are no registered optimized variants. `backend/app/ml/variants.py` rejects a variant without a 64-character hash, verifies the file and any referenced preprocessing/config/label files, and rejects unvalidated optimized entries. Thus the path being present does **not** mean the service can select or load it.

Small file SHA-256 identities currently recorded in the manifest:

- `artifacts/dino_disease/classes.json`: `F8988B3E341ACB2E461EA8DD1CAF9D3492A925405A32BCC57A79113237842AA4`
- `outputs/segformer_plantseg/best_model/config.json`: `2CC0AB73A3B2B2E1007E0A8A60CD340DB6F1953E54B514AD945E07D635493CA7`
- `outputs/segformer_plantseg/best_model/preprocessing.json`: `18A4464B70DD698FAFA5333C54C0BFD21ABD889A29E294C66042064CA49EC4C8`

SAM config is not a checkpoint in the repository; `backend/requirements-ml.txt` installs the pinned SAM2 source package and adapter/runtime checks for its package-relative config. Do not put model checkpoints in Git or overwrite them as part of this audit.

## Runtime and loading evidence

- SAM adapter: `backend/app/ml/adapters/sam_adapter.py`, true SAM2 generator path; load errors fail closed. No foliage/color/frame heuristic is returned as SAM output.
- Leaf filter: `backend/app/ml/adapters/leaf_filter.py`; expects `torch.load(..., weights_only=True)` state dict and exact binary head shape.
- Disease classifier: `backend/app/ml/adapters/disease_classifier.py`; consumes the 38-label JSON and has a class-specific final-block attention attribution path.
- Segmenter: `backend/app/ml/adapters/disease_segmentation.py`; reads config and preprocessing JSON, validates both label mappings, resizes logits to requested crop shape.
- Orchestration: `backend/app/ml/service.py`; enforces model order and output contracts, and delegates selected path/identity validation to `backend/app/ml/variants.py` before load.
- Compatibility facade: `backend/app/ml/pipeline.py` wraps `service.py`; it is not a separate model implementation. `backend/app/services/plant_analysis_service.py` adapts the typed service to a legacy response contract and remote client.

No checkpoint was deserialized; no tensor keys, model variants, inference quality or latency were inspected during this audit. Current host runtime is Windows 11 / Python 3.14.0, with no PyTorch, torchvision, Transformers, safetensors, or SAM2 package available. CUDA is **not tested**; because PyTorch is absent, no CUDA availability claim is made.

## Exact RTX-host follow-up paths

On the RTX 5060 checkout, ensure these paths point to local, readable bytes before running the checksum utility. If OneDrive shows cloud-only placeholders, hydrate the files or transfer them without changing the originals. Compare hashes before/after any copy. Use `backend/scripts/hash_model_manifest.py` only after confirming available disk and its required byte budget.

```text
artifacts/sam2/sam2.1_hiera_base_plus.pt
artifacts/dino_leaf_filter/dino_leaf_filter_v2.pt
artifacts/dino_disease/dino_disease_classifier.pt
artifacts/dino_disease/classes.json
outputs/segformer_plantseg/best_model/model.safetensors
outputs/segformer_plantseg/best_model/config.json
outputs/segformer_plantseg/best_model/preprocessing.json
outputs/segformer_plantseg/best_model/training_summary.json
outputs/segformer_plantseg/evaluation/<versioned report, if available>
```

After hashing, run `backend/scripts/gpu_environment_check.py --require-cuda`, then the original SAM2 smoke and end-to-end pipeline benchmark in `docs/DEVICE_AND_OPTIMIZATION_GUIDE.md`. Keep source revision, dataset/split, model hashes, runtime versions, output comparisons, timing, and peak memory with the results. Do not register a runtime variant as verified from a single successful load.
