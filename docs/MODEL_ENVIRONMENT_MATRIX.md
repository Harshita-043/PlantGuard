# PlantGuard AI model environment matrix

**Audit date:** 2026-10-27  
**Scope:** Runtime/environment readiness audit and manual CPU environment setup. The dedicated CPU environment is now verified for imports and package consistency. No checkpoint bytes were read or hashed, and no model was loaded or run.

## Evidence and current environment state

| Environment | Observed state | Decision |
|---|---|---|
| Application: `backend/.venv` | Python 3.14.0; FastAPI 0.118.3, HTTPX 0.28.1, pytest 9.1.1; no PyTorch, torchvision, Transformers, safetensors, or SAM2. Application requirements pass `pip check`. | Keep as the lightweight API environment. It cannot import/run model adapters that require Torch. |
| Existing ML: `.venv-ml` | Python 3.12.2; Torch 2.14.1+cpu, torchvision 0.29.1+cpu, Transformers 5.20.2, safetensors 0.8.0; no SAM2/hydra/iopath/OpenCV. CUDA unavailable. `pip check` reports missing `python-dateutil` (botocore) and `python-dotenv` (pydantic-settings). | Preserve unchanged. It does not match `backend/requirements-ml.txt` (Torch 2.6.0/torchvision 0.21.0/Transformers 4.57.6), so do not use as evidence or repair it in place. |
| CPU vision runtime: `C:\PlantGuardEnvs\plantguard-vision-cpu` | Python 3.12.2; Torch 2.6.0+cpu, torchvision 0.21.0+cpu, Transformers 4.57.6, safetensors 0.8.0, NumPy 2.3.4, Pillow 12.3.0. `pip check`: no broken requirements. DINO architecture and SegFormer imports passed after installing `backend/requirements.txt` into this environment. | Environment/import checks **verified**. No checkpoint was loaded and no inference was run. PowerShell activation is blocked by policy; invoke the environment Python by full path. |
| WSL SAM runtime | WSL was initially missing/blocked. User reports enabling the two Windows optional features and restarting; follow-up `wsl --status` output has not yet been provided. No Ubuntu distribution is verified. | Ask user to rerun `wsl --status` and `wsl --list --verbose`. WSL2 still does not provide CUDA on Intel Iris. |
| RTX 5060 runtime | Not inspected; machine not available in this audit. | Tomorrow, first record OS, Python, NVIDIA driver, `nvidia-smi`, and CUDA runtime. Do not carry over a CUDA package choice from the Vivobook. |

The current workspace is under OneDrive. Checkpoint paths below are present as Windows `ReparsePoint` entries; this audit did not prove they contain hydrated local checkpoint bytes, and the manifest hashes are unset. Treat each weight artifact as **ambiguous / not verified** until it is hydrated/copied and independently size/hash checked. Readable config/label files do not prove the checkpoint is present or trained as expected.

## Per-model matrix

| Stage/model | Environment name | Python / framework requirements | Device and laptop feasibility | Artifact/configuration paths | Current integration/readiness |
|---|---|---|---|---|---|
| SAM 2.1 Hiera Base Plus candidate masks | `plantguard-sam-gpu` (RTX machine; final OS/runtime choice pending host inspection) | Repository ML pin is Python 3.12 runtime expectation, Torch 2.6.0, torchvision 0.21.0 and SAM-2 source tag `v1.1.0`, plus Hydra/OmegaConf/iopath/OpenCV. SAM2 source installation and Windows compatibility are not verified. RTX 5060 is Blackwell; project’s Torch 2.6 pin must not be assumed compatible with it. | CPU inference not attempted and not approved on this 16 GB laptop. Intel Iris is not CUDA. GPU setup and real inference are **deferred to RTX**. | Weight: `artifacts/sam2/sam2.1_hiera_base_plus.pt` (323,606,802 listed bytes; reparse point; hash not verified). Config: `configs/sam2.1/sam2.1_hiera_b+.yaml` (path required by adapter). | Adapter is in existing pipeline; no SAM package installed in inspected envs. **Not loaded; inference untested; blocked** on valid bytes and compatible RTX runtime. |
| DINOv2 ViT-S/14 leaf candidate filter | `plantguard-vision-cpu` (shared) | Python 3.12; CPU Torch 2.6.0 + torchvision 0.21.0 per project pins. Native PyTorch architecture in `backend/app/ml/architectures/dinov2.py`; no Transformers dependency for this stage. | CPU contract supported; one-model-at-a-time smoke is laptop-feasible after local checkpoint availability. | Selected adapter path: `artifacts/dino_leaf_filter/dino_leaf_filter_v2.pt` (listed 88,300,869 bytes; reparse point; hash unverified). Legacy `artifacts/dino_leaf_filter/dino_leaf_filter.pt` also exists (88,300,314 bytes); do not substitute without manifest/metadata confirmation. 224x224 RGB, ImageNet normalization; negative/positive output. | Environment/imports **verified**. Existing adapter uses strict state-dict loading. **Checkpoint not loaded; inference untested.** |
| DINOv2 ViT-B/14 disease classifier (38 classes) | `plantguard-vision-cpu` (shared) | Same Python/Torch stack as DINO S. Native PyTorch architecture; no separate model package is evident. | Small single-image CPU smoke is feasible once artifact gate passes; it is not an accuracy evaluation. | Weight: `artifacts/dino_disease/dino_disease_classifier.pt` (listed 346,516,841 bytes; reparse point; hash unverified). Classes: `artifacts/dino_disease/classes.json` (readable; 38 ordered names). Adapter expects 224x224 RGB/ImageNet normalization and strict class-order metadata. | Environment/imports **verified**. Existing adapter checks 38 outputs and label ordering. **Checkpoint not loaded; inference untested.** |
| SegFormer-B0 PlantSeg segmentation | `plantguard-vision-cpu` (shared) | Same Torch stack plus Transformers 4.57.6, safetensors `>=0.5,<1`, NumPy/Pillow. Model uses local Hugging Face `from_pretrained(..., local_files_only=True)`. | One bounded CPU inference is feasible after artifact check; RAM and latency have not been measured. | `outputs/segformer_plantseg/best_model/model.safetensors` (listed 14,884,776 bytes; reparse point; hash unverified), `config.json`, `preprocessing.json`. Config maps 0 background/1 diseased_region and says `image_size=224`; preprocessing says size 512. Adapter trusts preprocessing size. This discrepancy needs confirmation against actual trained setup before interpreting output/severity. | Environment/imports **verified**. **Checkpoint not loaded; label semantics and inference unverified.** |
| Reliability/OOD, severity, explainability and result assembly | `backend/.venv` for contracts/API; `plantguard-vision-cpu` only when actual model tensors are required | Python application dependencies; Torch only for architecture-specific DINO attribution path. OOD fitting/calibration requires representative labeled validation data and is out of laptop scope. | Contracts/unit tests CPU-feasible. Real mask severity depends on validated SegFormer mapping and selected leaf mask. OOD calibration and explanation evaluation deferred to model/data evaluation. | Configuration/docs under `backend/app/ml/`, `backend/app/schemas/`, and `docs/RELIABILITY_AND_OOD.md`, `docs/SEVERITY_METHOD.md`, `docs/EXPLAINABILITY.md`. | Provisional reliability only; OOD calibration incomplete. Severity/explainability contract exists but model-dependent validity is not established. |

## Sharing decision

DINOv2 S, DINOv2 B, and SegFormer can share a single Python 3.12 CPU environment based on the inspected loaders: the DINO implementations are native PyTorch, while SegFormer adds Transformers/safetensors. No dependency conflict is visible at the repository pins. The existing `.venv-ml` is not that environment: its Torch/Transformers versions differ materially, so it remains untouched.

SAM2 is kept out of the Vivobook CPU environment. It brings a source/native dependency chain, the Windows/WSL runtime is absent, and an expensive SAM CPU run is not justified on a 16 GB laptop. The main FastAPI environment stays separate and lightweight. A local service/subprocess integration boundary has not yet been implemented; that is explicitly gated on successful environment verification.

## CPU environment setup record

The environment was created outside OneDrive at `C:\PlantGuardEnvs\plantguard-vision-cpu`. PowerShell activation was blocked by execution policy; no policy change was made. Commands were run directly through that environment's `Scripts\python.exe`. It has CPU-only PyTorch and the project backend requirements. `pip check` and model-class import checks passed. Package installation required adding `backend/requirements.txt`, because the existing `app.ml` package import initializes backend/storage modules (including `boto3`).

The following package commands are retained for reproducibility. **They have already been run; do not recreate the environment.**

Open a VS Code PowerShell terminal at:

`C:\Users\Asus\OneDrive\Desktop\PLANTGUARD AI\backend`

Use the full Python executable because PowerShell activation is restricted. These commands do not touch checkpoints or run inference.

```powershell
C:\PlantGuardEnvs\plantguard-vision-cpu\Scripts\python.exe -m pip install --upgrade pip
C:\PlantGuardEnvs\plantguard-vision-cpu\Scripts\python.exe -m pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu
C:\PlantGuardEnvs\plantguard-vision-cpu\Scripts\python.exe -m pip install numpy==2.3.4 pillow==12.3.0 transformers==4.57.6 "safetensors>=0.5,<1" "psutil>=5.9,<8" pydantic==2.12.5 pydantic-settings==2.11.0 python-dotenv==1.0.0
C:\PlantGuardEnvs\plantguard-vision-cpu\Scripts\python.exe -m pip install -r "C:\Users\Asus\OneDrive\Desktop\PLANTGUARD AI\backend\requirements.txt"
C:\PlantGuardEnvs\plantguard-vision-cpu\Scripts\python.exe -m pip check
C:\PlantGuardEnvs\plantguard-vision-cpu\Scripts\python.exe -c "import torch, torchvision, transformers, safetensors; print(torch.__version__, torchvision.__version__, transformers.__version__, safetensors.__version__, 'CUDA', torch.cuda.is_available())"
# Run from the repository backend directory:
C:\PlantGuardEnvs\plantguard-vision-cpu\Scripts\python.exe -c "from transformers import SegformerForSemanticSegmentation; from app.ml.architectures.dinov2 import build_dino_leaf_filter, build_dino_disease_classifier; print('DINO and SegFormer imports OK')"
```

The last import command uses the repository source, so run it from the stated `backend` directory. Observed: Python 3.12.2, Torch 2.6.0+cpu, torchvision 0.21.0+cpu, Transformers 4.57.6, safetensors 0.8.0, CUDA False, `pip check` reports no broken requirements, and `DINO and SegFormer imports OK`. **This is environment/import verification only. It is not checkpoint loading or inference.**

PowerShell activation is blocked by policy, so use the direct executable form shown above and do not change execution policy. No checkpoint tests have run; first confirm checkpoint files are hydrated and integrity-checked.

## RTX 5060 work boundary

Tomorrow, first run `nvidia-smi`, `py -0p`, and `py -3.12 --version` on the RTX computer and record OS/build, driver, GPU name, and installed CUDA runtime. The current repository pin Torch 2.6.0 must not be assumed to support the RTX 5060 (Blackwell). Select a compatible PyTorch/CUDA build only after that evidence and SAM2 source/install compatibility are checked. Then load original checkpoints one at a time, capture SHA-256 and outputs, run real SAM baseline, remaining stages, and full pipeline. Optimization/quantization and OOD calibration are later experiments; keep variants separate and preserve originals.

## Sources checked for moving compatibility facts

- [SAM 2 official installation guide](https://github.com/facebookresearch/sam2/blob/main/INSTALL.md) — current upstream installation guidance; the repository's exact `v1.1.0` source/tag was not independently validated here.
- [PyTorch 2.6 previous versions](https://docs.pytorch.org/get-started/previous-versions/) — project pinned CPU wheel command reference.
- [PyTorch 2.7 release notes](https://pytorch.org/blog/pytorch-2-7/) and [NVIDIA compute capability table](https://developer.nvidia.com/cuda/gpus) — Blackwell/PyTorch compatibility must be evaluated on the RTX host; no claim of RTX readiness is made.
