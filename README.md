# PlantGuard AI

> Enterprise-grade, multi-stage computer vision platform and diagnostic web application for precision plant health monitoring, leaf segmentation, disease classification, and lesion severity estimation.

---

## 1. Project Overview

PlantGuard AI delivers high-precision plant pathology diagnostics from uploaded leaf images. Built on a strict sequential inference pipeline, the application moves beyond standard classification by isolating individual leaf instances, rejecting non-leaf candidates, classifying disease across 38 distinct plant-pathogen classes, generating pixel-level lesion segmentation masks, evaluating out-of-distribution (OOD) boundaries, and calculating true geometric mask coverage.

### Key Capabilities
- **Hierarchical Computer Vision Pipeline:** Integrates Meta SAM 2.1 Hiera Base Plus, DINOv2 ViT-S/14, DINOv2 ViT-B/14, and SegFormer-B0 PlantSeg without mock inference or heuristics.
- **Fail-Closed Safety:** If out-of-distribution (OOD) distance exceeds calibrated bounds or required models fail, provisional diagnoses are withheld and the plant is marked `UNKNOWN` rather than fabricating false-positive treatments.
- **Multi-Cloud Storage & Persistence:** S3-compatible private object storage (Supabase Storage, Cloudflare R2, or authenticated local storage) paired with PostgreSQL relational tracking.
- **Owner-Scoped Security:** JWT authentication with Argon2 password hashing, strict asset access policies, and short-lived signed URLs.
- **Responsive Web Dashboard:** React 18, Vite 8, and Tailwind CSS interface with live scan status tracking, interactive leaf overlay inspection, and historical health telemetry.

---

## 2. System Architecture

```mermaid
flowchart TD
    subgraph Client["Frontend Client (React 18 + Vite)"]
        UI["Web Dashboard & Scan Interface"]
        AuthUI["JWT Session Management"]
    end

    subgraph Backend["Backend API (FastAPI + Uvicorn)"]
        Router["API Gateway / v1 Routers"]
        AuthSvc["Auth & User Ownership Engine"]
        StorageAdapter["Object Storage Adapter (Supabase / R2 / Local)"]
        InferenceSvc["PlantAnalysisService Boundary"]
    end

    subgraph Data["Persistence & Object Storage"]
        PG[("PostgreSQL Database")]
        Storage[("Supabase Storage / R2 Bucket")]
    end

    subgraph MLPipeline["Inference Pipeline (.venv-ml312 Runtime)"]
        SAM["SAM 2.1 Hiera Base+\n(Candidate Leaf Proposal)"]
        MobileSAM["MobileSAM ViT-T\n(CPU Fallback)"]
        LeafFilter["DINOv2 ViT-S/14\n(Leaf Validation Filter)"]
        Classifier["DINOv2 ViT-B/14\n(38-Class Classification + 768-D CLS)"]
        OOD["Mahalanobis OOD\n(Calibrated 99th Percentile)"]
        SegFormer["SegFormer-B0 PlantSeg\n(Lesion Segmentation)"]
        Severity["Geometric Severity Engine\n(|Lesion ∩ Leaf| / |Leaf|)"]
        Rollout["DINOv2 Attention Rollout\n(Visual Explainability)"]
    end

    UI -->|1. Upload Image (Multipart)| Router
    Router -->|2. Verify Auth| AuthSvc
    Router -->|3. Save Source Image| StorageAdapter
    StorageAdapter --> Storage
    Router -->|4. Create Pending Record| PG
    Router -->|5. Forward to ML Boundary| InferenceSvc

    InferenceSvc --> SAM
    SAM -.->|Fallback on error| MobileSAM
    SAM --> LeafFilter
    LeafFilter --> Classifier
    Classifier --> OOD
    Classifier --> Rollout
    Classifier --> SegFormer
    SegFormer --> Severity
    Severity --> InferenceSvc

    InferenceSvc -->|6. Persist Completed Result & Assets| PG
    InferenceSvc -->|7. Store Visual Assets| StorageAdapter
    Router -->|8. Structured Analysis JSON| UI
```

---

## 3. Actual ML Pipeline Execution Order

The model execution strictly follows this sequential contract behind `backend/app/ml/service.py`:

```
Input Image (RGB)
      │
      ▼
1. SAM 2.1 Hiera Base Plus (Candidate Leaf Mask Generation)
   [Fallback: MobileSAM ViT-T if SAM 2 runtime or config is unavailable]
      │
      ▼
2. DINOv2 ViT-S/14 (Leaf Candidate Filtering: Positive / Negative)
   [Rejects non-leaf geometric proposals, pots, background cloth, or stems]
      │
      ▼
3. DINOv2 ViT-B/14 (38-Class Disease Classification + 768-D CLS Extraction)
   [Evaluates crop species and disease identity; extracts latent CLS vector]
      │
      ▼
4. Out-of-Distribution (OOD) Reliability Scoring
   [Class-conditional Mahalanobis distance vs 99th-percentile threshold (~2474.64)]
      │
      ▼
5. SegFormer-B0 PlantSeg (Lesion Semantic Segmentation)
   [512x512 input with bilinear upsampling to crop resolution; binary lesion mask]
      │
      ▼
6. Mask-Based Severity Estimation
   [Exact ratio: (Lesion Pixels ∩ Valid Leaf Pixels) / (Valid Leaf Pixels)]
      │
      ▼
7. Architecture-Appropriate Explainability
   [DINOv2 Attention Rollout across ViT blocks from CLS token to patch embeddings]
      │
      ▼
8. Result Assembly & Verification
   [Persisted to PostgreSQL; private visual assets saved to storage]
```

---

## 4. Repository Structure

```text
PLANTGUARD AI/
├── .venv-ml312/                # Primary unified ML inference and backend runtime (Python 3.12.7)
├── artifacts/                  # Verified model checkpoints and SHA-256 manifests
│   ├── dino_disease/           # DINOv2 disease classifier weights, classes.json, ood.npz/json
│   ├── dino_leaf_filter/       # DINOv2 leaf filter PyTorch checkpoints (v1 & v2)
│   ├── mobilesam/              # MobileSAM fallback weights (mobile_sam.pt)
│   ├── optimized/              # INT8 ONNX optimized models (leaf filter, SegFormer)
│   ├── sam2/                   # SAM 2.1 Hiera Base Plus weights (sam2.1_hiera_base_plus.pt)
│   ├── manifest.json           # Model artifact manifest
│   └── model_manifest.json     # Comprehensive SHA-256 checksum registry
├── backend/                    # FastAPI application server
│   ├── .venv/                  # Optional lightweight API-only runtime (Python 3.14.0)
│   ├── app/
│   │   ├── api/                # API route controllers (v1: analyze, auth, plants, admin)
│   │   ├── core/               # Configuration, database engine, security settings
│   │   ├── ml/                 # Adapters (sam, leaf_filter, disease_classifier, segformer), service
│   │   ├── models/             # SQLAlchemy ORM definitions (User, Plant, Analysis)
│   │   ├── schemas/            # Pydantic v2 validation contracts
│   │   ├── storage/            # Object storage providers (Supabase, R2, Local)
│   │   └── tests/              # Automated unit, integration, and model test suite
│   ├── migrations/             # Alembic database migrations
│   ├── requirements.txt        # Lightweight API runtime dependencies
│   └── requirements-ml.txt     # Complete ML inference runtime dependencies
├── configs/                    # SAM 2 YAML configuration files
│   └── sam2.1/                 # sam2.1_hiera_b+.yaml
├── docs/                       # Project verification reports and documentation
│   ├── FINAL_AUDIT_REPORT.md
│   ├── MODEL_SELECTION_AND_LIMITATIONS.md
│   ├── ENVIRONMENT_CLEANUP_REPORT.md
│   └── PLANTGUARD_END_TO_END_AUDIT.md
├── frontend/                   # React 18 TypeScript web client
│   ├── client/                 # Pages (ScanPage, ScanResultsPage, HistoryPage, PlantsPage)
│   ├── server/                 # Production SSR server
│   ├── shared/                 # Shared TypeScript interfaces
│   └── package.json            # Node.js dependencies and build scripts
├── outputs/                    # SegFormer-B0 PlantSeg checkpoints
│   └── segformer_plantseg/     # model.safetensors, config.json, preprocessing.json
├── scripts/                    # Model download helper (download_models.py)
├── .env                        # Local root environment configuration
├── IMAGE_APP.jpg               # Standard test image fixture
└── README.md                   # Primary project guide
```

---

## 5. Prerequisites

- **Operating System:** Windows 10/11 (64-bit), Linux (Ubuntu 22.04+), or macOS.
- **Python:** **Python 3.12.7** is required for the ML inference runtime (`.venv-ml312`). (Python 3.11+ is supported for the lightweight API-only runtime).
- **Node.js:** Node.js v18.x, v20.x, or v22.x with npm.
- **Database:** PostgreSQL 14+ (hosted on Supabase, AWS RDS, Docker, or local install).
- **Object Storage:** Supabase Storage (S3 API), Cloudflare R2, or authenticated local storage.
- **Hardware:**
  - *Minimum (CPU-only):* 16 GB RAM, Quad-Core CPU (inference ~40-60s per full image).
  - *Recommended (GPU):* NVIDIA GPU with 8 GB+ VRAM, CUDA 12.1+ (inference ~300ms).

---

## 6. Environment Setup

All commands below use **Windows PowerShell**.

### 1. Clone & Position Workspace
```powershell
Set-Location "C:\Users\Asus\PLANTGUARD AI"
```

### 2. Primary ML Runtime Setup (`.venv-ml312`)
The unified `.venv-ml312` runtime contains PyTorch 2.6.0+cpu, torchvision 0.21.0+cpu, Transformers 4.57.6, SAM 2, MobileSAM, and all API requirements.
```powershell
# Verify Python 3.12.7 executable
.\.venv-ml312\Scripts\python.exe --version

# Verify PyTorch and Transformers
.\.venv-ml312\Scripts\python.exe -c "import torch, torchvision, transformers; print('PyTorch:', torch.__version__, 'Transformers:', transformers.__version__)"
```

### 3. Frontend Dependencies Setup
```powershell
Set-Location frontend
npm.cmd install
Set-Location ..
```

---

## 7. Environment Variables

Create `.env` in the repository root and `backend/.env` with your deployment credentials:

```ini
# Database (PostgreSQL)
DATABASE_URL=postgresql+psycopg://<username>:<password>@<host>:5432/<database>

# Security
JWT_SECRET_KEY=generate-a-secure-random-32-byte-secret-key-here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
BACKEND_CORS_ORIGINS=["http://localhost:8080","http://127.0.0.1:8080"]

# Storage Configuration (Supabase S3-compatible)
OBJECT_STORAGE_PROVIDER=supabase
SUPABASE_STORAGE_ENDPOINT=https://<project-ref>.supabase.co/storage/v1/s3
SUPABASE_STORAGE_REGION=us-east-1
SUPABASE_STORAGE_BUCKET=plantguard-storage
SUPABASE_STORAGE_ACCESS_KEY_ID=<your-access-key-id>
SUPABASE_STORAGE_SECRET_ACCESS_KEY=<your-secret-access-key>

# ML Hardware & Variant Settings
PLANTGUARD_DEVICE=auto
PLANTGUARD_INFERENCE_PROFILE=auto
PLANTGUARD_LEAF_FILTER_VERSION=v1
PLANTGUARD_DISEASE_CLASSIFIER_VARIANT=fp32
PLANTGUARD_SEGFORMER_VARIANT=plantseg-b0
PLANTGUARD_REMOTE_IMAGE_UPLOAD_AUTHORIZED=false
```

---

## 8. Database Setup & Migrations

Non-destructive commands to verify and migrate the database:

```powershell
# 1. Test database connection
.\.venv-ml312\Scripts\python.exe -c "from sqlalchemy import create_engine, text; from app.core.config import settings; engine=create_engine(settings.DATABASE_URL); print('Connected:', engine.connect().execute(text('SELECT 1')).scalar() == 1)"

# 2. Check current Alembic migration head
Set-Location backend
..\.venv-ml312\Scripts\python.exe -m alembic -c alembic.ini heads

# 3. Apply migrations up to head (non-destructive)
..\.venv-ml312\Scripts\python.exe -m alembic -c alembic.ini upgrade head
Set-Location ..
```

---

## 9. Object Storage Setup & Connectivity Probe

To verify your object storage without modifying existing scan assets:

```powershell
.\.venv-ml312\Scripts\python.exe -c "
from app.storage.factory import create_object_storage
import uuid
storage = create_object_storage()
print('Storage Provider Class:', type(storage).__name__)
print('Bucket Ready:', storage.check_ready())
# Safe round-trip check
key = f'test-{uuid.uuid4().hex}'
storage.put(b'plantguard-storage-probe', object_key=key, content_type='text/plain')
assert storage.exists(key) is True
storage.delete(key)
print('Live Storage Round-Trip: SUCCESS')
"
```

---

## 10. Model Artifact Placement

The verified original checkpoints and configurations must reside at these exact relative paths:

| Model | Path | Expected File Size | Expected SHA-256 |
|---|---|---|---|
| **SAM 2.1 Hiera Base+** | `artifacts/sam2/sam2.1_hiera_base_plus.pt` | 323,606,802 bytes | `a2345aede8715ab1d5d31b4a509fb160c5a4af1970f199d9054ccfb746c004c5` |
| **SAM 2.1 Config** | `configs/sam2.1/sam2.1_hiera_b+.yaml` | Configuration YAML | Validated YAML |
| **MobileSAM Fallback** | `artifacts/mobilesam/mobile_sam.pt` | 40,728,226 bytes | `6dbb90523a35330fedd7f1d3dfc66f995213d81b29a5ca8108dbcdd4e37d6c2f` |
| **DINOv2 Leaf Filter v1** | `artifacts/dino_leaf_filter/dino_leaf_filter.pt` | 88,300,314 bytes | `fa2207b53a067c26aa3346e9dfbc7fbf86d38e21a4f3cefd3980c98f986641ae` |
| **DINOv2 Filter INT8** | `artifacts/optimized/dino_leaf_filter/onnx_int8/dino_leaf_filter_dynamic_int8.onnx` | 24,951,130 bytes | `60814f923bca327916ef4242699298e16db73eb5547dd5698b6aa55490bf9961` |
| **DINOv2 Disease Classifier** | `artifacts/dino_disease/dino_disease_classifier.pt` | 344,016,841 bytes | `446ee9cf1da3d6118bfa934372a912bb0fb1a7efec1781fe563ef31d0442e3f6` |
| **38-Class Mapping** | `artifacts/dino_disease/classes.json` | 1,215 bytes | Validated JSON |
| **OOD Calibration** | `artifacts/dino_disease/ood.npz` | 2,177,452 bytes | `a940f5d96ca44fbf8d135beea9e801cf3d8650df6866ec532ae1046168536f61` |
| **OOD Metadata** | `artifacts/dino_disease/ood.json` | 1,108 bytes | `89f5bc335f6f45ff5804efbb2fa9856f6ba50aa0ce6294d35eb7b372fbf6ec25` |
| **SegFormer-B0 Safetensors** | `outputs/segformer_plantseg/best_model/model.safetensors` | 14,884,776 bytes | `be1cf5b4260d2d326f59ee9fc928f64560ea511c59c5d011f05cefcab2a2c5a1` |
| **SegFormer INT8 ONNX** | `artifacts/optimized/segformer/onnx_int8/segformer_dynamic_int8.onnx` | 7,907,030 bytes | `0dc2323e198642a8b945cae7c51480c598000be05c040d6c48325a7a92265f24` |

To verify that all required checkpoints are present and readable:
```powershell
.\.venv-ml312\Scripts\python.exe -c "from app.ml.registry import ModelRegistry; reg=ModelRegistry(); print('All model artifacts present:', all(c['artifact_exists'] for c in reg.get_readiness_report()['components'].values()))"
```

---

## 11. FINAL TERMINAL RUN COMMANDS

Use these exact copy-paste-ready commands to start the application.

### Terminal 1: Backend API Server
```powershell
# Open Windows PowerShell
Set-Location "C:\Users\Asus\PLANTGUARD AI\backend"
..\.venv-ml312\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*API docs will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).*

### Terminal 2: Frontend Web Application
```powershell
# Open a second Windows PowerShell
Set-Location "C:\Users\Asus\PLANTGUARD AI\frontend"
npm.cmd run dev
```
*Web application interface will be live at [http://localhost:8080](http://localhost:8080).*

---

## 12. Complete Scan Workflow

1. **User Authentication:** User registers or logs in via `/login`. The client receives a JWT access token stored in memory/session.
2. **Image Upload:** On `/scan`, the user selects a plant image (JPEG, PNG, WebP $\le 10$ MB) and optionally selects a tracked plant.
3. **Upload Validation & Storage:** FastAPI checks image headers, MIME type, and decodes the image. The original image is written to private object storage under the user's namespace (`plantguard/...`).
4. **Database Record Creation:** An `analyses` row is persisted with `status: pending`.
5. **Inference Pipeline Execution:**
   - SAM 2.1 segments candidate leaf masks in image coordinates.
   - High-containment duplicates are pruned.
   - DINOv2 ViT-S/14 filters out non-leaf artifacts.
   - DINOv2 ViT-B/14 extracts 38 disease class probabilities and the 768-D CLS feature.
   - Mahalanobis OOD evaluates latent feature distance against the 99th percentile threshold.
   - SegFormer-B0 PlantSeg segments disease lesions.
   - Geometric severity is computed as diseased pixels over valid leaf area.
   - DINOv2 Attention Rollout generates visual attention maps.
6. **Persistence & Response:** The complete diagnostic result and asset paths are saved to the PostgreSQL database. The API returns HTTP 201 with the completed scan payload.
7. **Frontend Presentation:** On `/scan/results/:id`, the dashboard visualizes the segmented leaves, provisional lesion coverage, OOD status, and technical diagnostics.

---

## 13. Testing and Verification

### 1. Run Complete Backend Unit & Contract Suite
```powershell
# Executes 250+ CPU-safe tests across auth, storage, database, and contracts
.\.venv-ml312\Scripts\python.exe -m pytest -q
```

### 2. Run Real-Model Inference Tests (Opt-In)
```powershell
# Runs SAM 2.1, MobileSAM, DINOv2, SegFormer, and end-to-end pipeline on test image
$env:PLANTGUARD_RUN_REAL_MODEL_TESTS="1"
.\.venv-ml312\Scripts\python.exe -m pytest -q backend\app\tests\test_model_inference_smoke.py
.\.venv-ml312\Scripts\python.exe -m pytest -q backend\app\tests\test_real_model_inference.py backend\app\tests\test_real_authenticated_lifecycle.py
```

### 3. Run Frontend Verification
```powershell
Set-Location frontend
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
Set-Location ..
```

---

## 14. Troubleshooting

- **PowerShell Script Execution Error (`about_Execution_Policies`):**  
  *Cause:* Windows PowerShell restricts running unsigned `.ps1` wrapper scripts.  
  *Fix:* Directly invoke the binary or `.cmd` extension (e.g., use `npm.cmd` instead of `npm`, and invoke `.\.venv-ml312\Scripts\python.exe` directly rather than running `Activate.ps1`).

- **PyTorch `weights_only` Deserialization Error:**  
  *Cause:* Git LFS pointer text file loaded as model weights, or untrusted class deserialization.  
  *Fix:* Run `git lfs pull` to hydrate binary weights. Checkpoints in this repository are verified with strict `weights_only=True` loading.

- **CUDA Not Available / Intel Graphics:**  
  *Cause:* Laptop possesses integrated Intel Iris Xe graphics, which does not support CUDA.  
  *Fix:* The pipeline automatically selects CPU bounded chunking. For GPU acceleration, deploy on an NVIDIA RTX host.

- **OOD Threshold Exceeded / All Leaves Flagged:**  
  *Cause:* Test image feature distance exceeds the 99th percentile in-distribution threshold.  
  *Fix:* This is the intended fail-closed safety design. The disease label is withheld from the accepted plant-level diagnosis rather than guessing.

- **Supabase Storage 403 Forbidden:**  
  *Cause:* Missing or misconfigured S3 access keys or incorrect bucket name.  
  *Fix:* Verify `SUPABASE_STORAGE_ACCESS_KEY_ID` and `SUPABASE_STORAGE_SECRET_ACCESS_KEY` in `.env`.

---

## 15. Known Limitations & Future Scope

### Known Limitations
- **CPU Inference Latency:** Running SAM 2.1 with full automatic mask generation on CPU requires ~30–50 seconds per high-resolution image.
- **OOD Field Calibration:** The Mahalanobis threshold is calibrated on curated PlantVillage embeddings; natural field images with harsh sunlight or soil clutter may trigger provisional OOD warnings.
- **Lesion Binary Segmentation:** SegFormer identifies lesion vs healthy leaf tissue, but does not segment multi-class pathogen species individually.

### Future Scope (Explicitly Deferred)
- Autonomous Multi-Agent Diagnosis Orchestration.
- Retrieval-Augmented Generation (RAG) agronomic treatment knowledge base.
- Live automated weather radar alerts and agronomic micro-climate forecasting.
