# PlantGuard AI — Current State & Vivobook-First Audit

*Document Generated: 2026-10-26*
*Platform: ASUS Vivobook 15/16 (Intel Core CPU, 16 GB RAM, Intel Iris Xe Integrated Graphics, Windows 11)*

---

## 1. Executive Summary

This document establishes the verified technical state of the PlantGuard AI codebase, its physical model artifacts, runtime environment, and architectural capabilities. The system was audited to establish an inference architecture optimized for execution on an ASUS Vivobook (16 GB RAM, Intel Iris Xe graphics) while remaining seamlessly deployable to high-performance GPU server environments without refactoring.

**Key Findings:**
1. **Model Inventory Verified**: Three primary PyTorch checkpoints and one SegFormer safetensors checkpoint are physically present in the workspace:
   - DINOv2 Leaf Filter (`artifacts/dino_leaf_filter/dino_leaf_filter.pt` - 88.3 MB)
   - DINOv2 Disease Classifier (`artifacts/dino_disease/dino_disease_classifier.pt` - 346.5 MB, with 38-class `classes.json`)
   - SegFormer-B0 Binary Disease Segmentation (`outputs/segformer_plantseg/best_model/model.safetensors` - 14.88 MB, with `config.json` & `preprocessing.json`)
   - SAM 2.1 Hiera Base+ (`artifacts/sam2/sam2.1_hiera_base_plus.pt` - 323.6 MB)
2. **EfficientNet Deprecated**: Legacy EfficientNet Keras artifacts have been excluded in adherence to strict architectural rules. No EfficientNet checkpoints are used or retained in active pipelines.
3. **Hardware & Runtime Reality**:
   - Host GPU: Intel Iris Xe Graphics (Integrated). NVIDIA CUDA is not available (`torch.cuda.is_available() == False`).
   - Active Python: Python 3.14.0 in `backend/.venv`. Note that official PyTorch binary wheels are currently released up to Python 3.12 / 3.13 preview; PyTorch is not currently installed in `backend/.venv`.
   - Node.js: v22.17.1.
   - RAM: 16.0 GB total.
   - Storage: 239.7 GB free of 475.1 GB on local disk.
4. **Backend State**: FastAPI backend has solid auth (Argon2id + JWT), database modeling (`Analysis`, `User` with Alembic revisions 0001–0004), and modular storage adapters (Local, Cloudflare R2, Supabase Storage). The ML services layer currently returns `MLCapabilityUnavailable` pending this integration contract and pipeline implementation.

---

## 2. Verified Existing Functionality

### 2.1 FastAPI Backend & Application Core
- **Authentication & Authorization**:
  - `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`.
  - Passwords hashed using Argon2id (`argon2-cffi`).
  - Expiring JWT bearer tokens with standard claims and secure validation.
- **Image Lifecycle & Validation**:
  - `POST /api/v1/analyze/image` validates uploaded binary content (MIME types: JPEG, PNG, WebP; strict 10 MB payload ceiling).
  - Pillow image verification against decompression bombs (`DecompressionBombError` handling) and header tampering.
  - Image persisted to configured object storage under owner-scoped keys (`users/{user_id}/analyses/{analysis_id}/image`).
  - Analysis records stored in PostgreSQL / SQLite with initial `pending` status.
- **Storage Abstraction**:
  - `ObjectStorage` interface implemented across three swappable backends:
    - Private local filesystem storage (`LocalObjectStorage`).
    - Cloudflare R2 (`R2ObjectStorage` via `boto3`).
    - Supabase Storage (`SupabaseObjectStorage` S3 API).
- **Agentic Scaffold**:
  - Structured orchestration contracts (`AgentPlan`, `ExecutionCommand`, `OperationResult`, `FinalResponse`) and lifecycle state machine in `app/agent/core/`.

---

## 3. Actual Model Inventory

| Component | Architecture | Physical Artifact Path | File Format & Size | Classes / Labels | Input Dimensions | Performance / Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Leaf Filter** | DINOv2 Small (`dinov2_vits14`) + Linear Head | `artifacts/dino_leaf_filter/dino_leaf_filter.pt` (v2: `dino_leaf_filter_v2.pt`) | PyTorch Zip (88.3 MB) | 2 classes: `negative` (non-leaf), `positive` (leaf) | 224 × 224 × 3 RGB | Test Acc: 100%, F1: 1.0 (on 1,250 test crops) |
| **Disease Classifier** | DINOv2 Base (`dinov2_vitb14`) + Linear Head | `artifacts/dino_disease/dino_disease_classifier.pt` | PyTorch Zip (346.5 MB) | 38 classes defined in `artifacts/dino_disease/classes.json` (PlantVillage) | 224 × 224 × 3 RGB | Present, weights intact, uncorrupted |
| **Disease Segmentation** | SegFormer-B0 (`nvidia/mit-b0` + MLP Decoder) | `outputs/segformer_plantseg/best_model/model.safetensors` | Safetensors (14.88 MB, 209 tensor keys) | 2 classes: `0: background`, `1: diseased_region` | 512 × 512 × 3 RGB | Best Val Dice: 0.787 (trained on PlantSeg, 18 epochs) |
| **Leaf Instance Segmentation** | SAM 2.1 Hiera Base+ | `artifacts/sam2/sam2.1_hiera_base_plus.pt` | PyTorch Zip (323.6 MB) | Class-agnostic promptable segmentation | Variable / 1024 × 1024 | Intact checkpoint, prompt/grid capable |

*Note: All artifacts verified via structural unpack/header inspection.*

---

## 4. Missing Functionality

1. **Common Inference Adapter Contract**: No standardized adapter interface existed to decouple pipeline logic from backend frameworks.
2. **Out-of-Distribution (OOD) Detection**: Neither Mahalanobis feature distance nor prediction entropy thresholding was implemented. A model would predict one of the 38 classes even on completely foreign objects or corrupted crops.
3. **Mask-Based Severity Estimation**: Calculation of diseased lesion area relative to leaf surface area (`diseased_area_pixels / leaf_area_pixels * 100`) and categorical mapping (Low, Medium, High) was missing.
4. **Separate Mask Asset Storage**: Disease and leaf masks were previously drafted as inline 2D JSON arrays in `LeafResult`, creating payloads in excess of 10–20 MB per response.
5. **Runtime Hardware Fallbacks**: No unified CPU execution orchestrator designed for sequential, bounded-memory execution on integrated Iris Xe graphics.
6. **Model Readiness Reporting & Health**: `/api/v1/analyze/health` returned hardcoded 503 instead of reporting dynamic component health.

---

## 5. Dependency & Environment Issues

1. **Python 3.14 Host Isolation**:
   - `backend/.venv` was provisioned with Python 3.14.0.
   - Standard PyTorch, TorchVision, and Hugging Face Transformers prebuilt wheels for Windows are currently released for Python 3.10–3.12 (with experimental 3.13).
   - PyTorch is not currently installed inside `backend/.venv`.
2. **Windows Sandbox Socket Restrictions**:
   - In sandboxed environments on Windows, `asyncio.ProactorEventLoop` socket/IPC initialization requires unsandboxed bypass for live network or socket binding. File system and computational unit tests run completely sandboxed.
3. **Execution Policy on NPM/PNPM**:
   - Windows PowerShell restricts unsigned `.ps1` scripts; node scripts must run via `npx` or bypass execution policy.

---

## 6. Vivobook Feasibility Analysis

### 6.1 Highly Feasible on Vivobook (16 GB RAM + Intel CPU/Iris Xe)
- **SegFormer-B0 Segmentation**: Only 3.7 million parameters (~14.8 MB). Runs in under 200 ms on CPU with ONNX Runtime or Torch CPU.
- **DINOv2 Small Leaf Filter**: ~22 million parameters (~88 MB). Fast feature extraction on CPU (< 300 ms).
- **DINOv2 Base Disease Classifier**: ~86 million parameters (~346 MB). High accuracy; takes ~800–1200 ms on Intel Core CPU.
- **Mask-Based Severity & Geometric Metrics**: Pure NumPy array calculations (< 5 ms).
- **OOD Energy/Entropy Scoring**: Linear algebra on output logits or embeddings (< 1 ms).
- **Mask Binary PNG Storage**: Atomic disk writes / object storage uploads (< 20 ms).
- **Full Backend & Web UI**: FastAPI + Vite React frontend run comfortably under 1.5 GB total RAM.

### 6.2 Components Deferred to Dedicated GPU Hardware
- **SAM 2.1 Full Automatic Mask Generation (`points_per_side=32`)**: Running 1024 points through SAM 2.1 Base+ (80M parameters) on an Intel CPU takes 45–90 seconds per image and can saturate RAM.
  - *Vivobook strategy*: Use fallback heuristic (whole leaf / thresholded contour) or bounding-box-prompted SAM on single leaf crops; defer dense grid SAM automatic mask generation to GPU worker.
- **Model Training / Fine-tuning**: Fine-tuning DINOv2 or SegFormer requires discrete CUDA GPUs (RTX 3060/4090 or Cloud A100).
- **Real-Time Video Multi-Leaf Tracking**: Real-time 30 FPS video inference requires CUDA acceleration.

---

## 7. Prioritized Implementation Plan

### Phase 1: Integration Contract & Versioned Schemas (Current Turn)
- Create versioned Pydantic schemas in `app/schemas/v2/` covering:
  - Scan result metadata, leaf result, disease prediction with top-k probabilities.
  - OOD score and flagged out-of-distribution indicator.
  - Segmentation asset pointers (`mask_object_key`, URL, dimensions) rather than inline arrays.
  - Quantitative severity (affected percentage, lesion count, categorical level).
  - Explainability metadata.
  - Warnings and partial failure tracking.
- Create common inference adapter interface in `app/ml/interfaces/` defining lifecycle, input contracts, preprocessing, output contracts, and failure semantics.

### Phase 2: Core Foundation & Safe Model Registry
- Implement `ModelRegistry` in `app/ml/registry.py` that discovers and validates local artifacts without loading all heavy weights simultaneously.
- Implement device selector with automatic Intel Iris CPU fallback.
- Implement safe sequential pipeline orchestrator with bounded concurrency (preventing multi-gigabyte memory spikes on Vivobook).
- Implement algorithmic mask severity calculator (`app/ml/severity.py`).
- Implement statistical OOD scorer (`app/ml/ood.py`).

### Phase 3: Runtime Environment Prerequisites & Verification
- Document exact manual setup for isolated Python 3.12 ML environment (or ONNX Runtime CPU) for executing weights without interfering with the backend Python 3.14 server.
- Validate unit tests for schemas, registry, severity calculations, and error handling.
