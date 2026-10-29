# PlantGuard AI

> An enterprise-grade, multi-stage computer vision platform and diagnostic dashboard for high-precision plant leaf analysis and disease detection.

---

## 🌿 Overview & Key Features

PlantGuard AI provides end-to-end plant health diagnosis by combining modern foundation vision models with strict inference boundaries, asynchronous multi-storage support, and an authenticated interactive web interface:

- **Multi-Stage Computer Vision Pipeline**:
  1. **Leaf Segmentation & Mask Proposals**: SAM 2.1 Hiera Base Plus first; MobileSAM ViT-T is used only when SAM 2 cannot load because its runtime, config, or checkpoint is unavailable.
  2. **Leaf Validation & Background Rejection**: DINOv2 ViT-S/14 leaf classifier filtering out non-leaf proposals.
  3. **Disease Classification**: DINOv2 ViT-B/14 multi-class disease classifier with out-of-distribution (OOD) uncertainty estimation.
  4. **Lesion Segmentation**: NVIDIA SegFormer-B0 PlantSeg semantic segmentation for granular disease boundary mapping.
  5. **Reliability, Severity & Explainability**: Mask-derived affected leaf area percentage, uncertainty scoring, and DINOv2 Attention Rollout heatmaps.
- **Strict Architecture Boundaries**: High-performance model inference encapsulated behind `backend/app/ml/service.py` with typed runtime contracts.
- **Enterprise Storage Options**: Native adapters for Local Disk Storage, Cloudflare R2, and Supabase S3-compatible Object Storage.
- **Robust Security & Auth**: JWT access tokens signed with Argon2 password hashing and owner-scoped analysis retrieval.
- **Modern Responsive Dashboard**: Interactive React 18 single-page application built with Vite, Tailwind CSS, Lucide icons, and Radix UI primitives.

---

## 🛠 Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend API** | Python 3.11+, FastAPI, Uvicorn, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| **Inference / ML** | PyTorch, torchvision, HuggingFace Transformers, SAM 2, MobileSAM, ONNX Runtime, OpenCV, Pillow |
| **Frontend** | TypeScript, React 18, Vite, Tailwind CSS, Radix UI, TanStack Query, Vitest |
| **Infrastructure** | Docker, Docker Compose, GitHub Actions CI |

---

## 📋 Prerequisites

- **Python**: 3.11, 3.12, or 3.14 for the API; Python 3.12 is required by the verified SAM 2/DINO/SegFormer inference runtime. MobileSAM supports PyTorch CPU, CUDA, and Apple MPS execution.
- **Node.js**: v18.0.0+ or v20.0.0+ (with npm)
- **Database**: PostgreSQL 14+ (or SQLite in-memory for testing)
- **Optional GPU**: NVIDIA GPU with CUDA 12+ for accelerated model inference

---

## ⚙️ Environment Variables

Copy `.env.example` to `backend/.env` for local configuration:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `BACKEND_CORS_ORIGINS` | JSON list | `["http://localhost:8080"]` | Allowed CORS origins for frontend requests. |
| `DATABASE_URL` | string | `postgresql+psycopg://postgres:postgres@localhost:5432/plantguard` | SQLAlchemy database connection URI. |
| `OBJECT_STORAGE_PROVIDER` | string | `local` | Storage provider: `local`, `supabase`, or `r2`. |
| `LOCAL_STORAGE_ROOT` | string | `.local-storage` | Filesystem root directory for local file storage. |
| `JWT_SECRET_KEY` | string | *None* | 32+ byte secret key used for signing JWT access tokens. |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | int | `30` | JWT token validity expiration window in minutes. |
| `PLANTGUARD_DEVICE` | string | `auto` | Target device for ML inference (`auto`, `cpu`, `cuda`, `mps`). Auto prefers CUDA, then Apple MPS, then CPU. |
| `PLANTGUARD_SAM_STRATEGY` | string | `auto` | Retained compatibility setting; proposals always try SAM 2 first, then MobileSAM if SAM 2 is unavailable. |
| `PLANTGUARD_INFERENCE_PROFILE` | string | `auto` | Inference profile (`auto` for local discovery, `remote` for remote worker). |
| `PLANTGUARD_LEAF_FILTER_VERSION` | string | `v2` | Selects the manifest-verified DINOv2 ViT-S/14 leaf-filter artifact. |
| `PLANTGUARD_DISEASE_CLASSIFIER_VARIANT` | string | `original-pytorch-fp32` | Exact manifest variant for DINOv2 ViT-B/14 classification; unregistered variants fail explicitly. |
| `PLANTGUARD_SEGFORMER_VARIANT` | string | `original-transformers-fp32` | Exact manifest variant for SegFormer-B0 PlantSeg. |
| `PLANTGUARD_OOD_CALIBRATION_PATH` | path | repository calibration artifact | Optional path to the required OOD calibration NPZ; a matching JSON metadata file is required. |
| `R2_BUCKET_NAME` | string | `""` | Bucket name when using Cloudflare R2 storage. |
| `R2_ENDPOINT_URL` | string | `""` | S3 API endpoint URL for Cloudflare R2. |
| `SUPABASE_STORAGE_BUCKET` | string | `""` | Bucket name when using Supabase Storage. |
| `SUPABASE_STORAGE_ENDPOINT` | string | `""` | S3 API endpoint URL for Supabase Storage. |

---

## 🚀 Installation & Setup

### 1. Clone the repository
```bash
git clone <repository-url>
cd "PLANTGUARD AI"
```

### 2. Backend Setup
Create and activate a Python virtual environment:
```bash
python -m venv backend/.venv

# Windows (PowerShell)
.\backend\.venv\Scripts\Activate.ps1

# Linux / macOS
source backend/.venv/bin/activate
```

Install the API runtime dependencies:
```bash
pip install -r backend/requirements.txt
```

*(Optional)* If running full GPU/CPU vision models locally, install the ML dependencies:
```bash
pip install -r backend/requirements-ml.txt
python scripts/download_models.py
```

The optional ML requirements pin the official SAM-2 and MobileSAM sources, PyTorch, and the `timm` dependency required by MobileSAM. Use Python 3.12 for the complete SAM 2/DINO/SegFormer pipeline. MobileSAM is the CPU-capable leaf-proposal fallback and can also use CUDA or Apple MPS when available.

The MobileSAM ViT-T checkpoint is stored at `artifacts/mobilesam/mobile_sam.pt` (40.7 MB). If it is absent, obtain the official checkpoint from the [MobileSAM repository](https://github.com/ChaoningZhang/MobileSAM/blob/master/weights/mobile_sam.pt) and save it at that path. Verify the download before running inference:

```powershell
Invoke-WebRequest `
  -Uri "https://raw.githubusercontent.com/ChaoningZhang/MobileSAM/master/weights/mobile_sam.pt" `
  -OutFile "artifacts/mobilesam/mobile_sam.pt"
Get-FileHash "artifacts/mobilesam/mobile_sam.pt" -Algorithm SHA256
```

The expected SHA-256 is `6dbb90523a35330fedd7f1d3dfc66f995213d81b29a5ca8108dbcdd4e37d6c2f`. Completed scans identify the leaf-proposal variant actually used and indicate whether MobileSAM fallback was applied.

### 3. Frontend Setup
```bash
cd frontend
npm install
cd ..
```

---

## 💻 Running the Application

### Persisted workflows and metric semantics

- The authenticated dashboard reads user-scoped data from `GET /api/v1/dashboard/metrics`; it does not display sample metrics.
- Plant records are stored through `/api/v1/plants`. Scans may be associated with an owned plant during upload, or linked later through the plant API.
- Analysis history and artifact retrieval are owner-scoped. Object-storage buckets remain private; providers use short-lived signed downloads, while local storage is served through the authenticated API.
- The displayed health score is descriptive only: `100 - mean measured per-leaf severity`. It is not a validated agronomic measurement and is unavailable when aligned severity masks are unavailable.
- The OOD artifact records an in-distribution 99th-percentile threshold. OOD performance has not been independently validated, so those results remain explicitly unvalidated and must not be interpreted as confirmed OOD diagnoses.

### Running Locally

1. **Start Backend**:
```bash
# From workspace root
.\backend\.venv\Scripts\uvicorn.exe backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
API docs will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

2. **Start Frontend**:
```bash
cd frontend
npm run dev
```
Open [http://localhost:8080](http://localhost:8080) in your browser.

### Running with Docker Compose
```bash
docker-compose up --build
```

---

## 🧪 Testing & Verification

### Backend Tests (Pytest)
```bash
# Run the complete CPU-safe unit and API integration suite
pytest
```

### Frontend Typecheck, Lint & Unit Tests
```bash
cd frontend
npm run typecheck
npm test
npm run build
```

---

## 📁 Repository Structure

```text
├── .github/workflows/          # GitHub Actions CI workflow (backend, frontend, docker)
├── app/                        # Root namespace shim for clean package resolution
├── artifacts/                  # Verified model checkpoints, configs & SHA-256 manifests
│   ├── dino_disease/           # DINOv2 disease classifier checkpoints & classes
│   ├── dino_leaf_filter/       # DINOv2 leaf filter checkpoints
│   ├── mobilesam/              # MobileSAM fallback weights
│   ├── optimized/              # INT8 and FP32 ONNX variants
│   ├── sam2/                   # SAM 2.1 Hiera Base Plus weights
│   └── model_manifest.json     # Verified model inventory manifest
├── backend/                    # FastAPI application service
│   ├── app/
│   │   ├── agent/              # Multi-step diagnosis agent & tools
│   │   ├── api/v1/             # Endpoints (auth, analysis, health, models, agent)
│   │   ├── core/               # Configuration, database engine, JWT security
│   │   ├── ml/                 # Pipeline stages, model registry, CAM explainability
│   │   ├── models/             # SQLAlchemy ORM models (User, AnalysisRecord)
│   │   ├── schemas/            # Pydantic v2 schemas and validation models
│   │   ├── storage/            # Object storage providers (Local, Supabase, R2)
│   │   └── tests/              # Comprehensive test suite
│   ├── migrations/             # Alembic database migrations
│   ├── Dockerfile.cpu          # CPU production container
│   ├── requirements.txt        # API runtime requirements
│   └── requirements-ml.txt     # Optional inference runtime requirements
├── frontend/                   # React + TypeScript frontend application
│   ├── client/                 # Pages (Scan, Results, History, Plants), UI components
│   ├── server/                 # Express SSR & production static handler
│   ├── shared/                 # Shared TypeScript interfaces & types
│   ├── Dockerfile              # Production container build
│   └── package.json            # Frontend scripts and dependencies
├── scripts/                    # Model download helper (download_models.py)
├── docker-compose.yml          # Container composition definition
├── pytest.ini                  # Root pytest configuration
└── README.md                   # Project documentation
```

---

## 📄 License

This project is licensed under the terms chosen by the project maintainers. See `LICENSE` for details.
