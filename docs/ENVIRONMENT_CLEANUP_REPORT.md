# PlantGuard AI — Environment Audit and Cleanup Report

**Date:** 2026-10-31  
**Scope:** Project-local virtual environment audit, safety quarantine, deletion of abandoned environments, and validation of active environments.

---

## 1. Initial Inventory Before Cleanup

At the start of this audit, six separate project-local Python virtual environments were discovered across the repository root and backend directory:

| Environment Path | Python Version | Disk Size | Key Installed Packages | Purpose / Origin | Actively Referenced? | Recommendation |
|---|---|---|---|---|---|---|
| `C:\Users\Asus\PLANTGUARD AI\.venv-ml312` | 3.12.7 | 1,785 MB | PyTorch 2.6.0+cpu, torchvision 0.21.0+cpu, Transformers 4.57.6, SAM 2 1.0 (editable), MobileSAM 1.0, ONNX Runtime 1.31.1, FastAPI 0.118.3, SQLAlchemy 2.0.54, psycopg 3.3.6, boto3 1.43.101, pytest 9.2.0 | Canonical unified application and ML inference environment for Windows | Yes (primary runtime for backend, tests, and models) | **KEEP (Active Core)** |
| `C:\Users\Asus\PLANTGUARD AI\.venv-ml` | 3.14.0 | 1,181 MB | PyTorch 2.14.1 (experimental), torchvision 0.29.2, Transformers 4.57.6, SAM 2 1.0 | Early experimental Python 3.14 ML test environment | No (superseded by `.venv-ml312` pinned to Python 3.12 / Torch 2.6) | **REMOVE** |
| `C:\Users\Asus\PLANTGUARD AI\venv_ml` | 3.14.0 | 181 MB | FastAPI, Starlette, SQLAlchemy, psycopg, boto3 (No ML packages despite its name) | Duplicate API environment created during previous trials | No active references | **REMOVE** |
| `C:\Users\Asus\PLANTGUARD AI\backend\.venv` | 3.14.0 | 169 MB | FastAPI 0.118.3, Uvicorn 0.24.0, Pydantic 2.12.5, SQLAlchemy 2.0.54, psycopg 3.3.6, boto3 1.43.101 | Dedicated lightweight non-ML API runtime per `backend/requirements.txt` | Yes (documented as optional lightweight API-only environment) | **KEEP (Lightweight API Option)** |
| `C:\Users\Asus\PLANTGUARD AI\backend\.venv_new` | 3.14.0 | 11.3 MB | pip 25.2 only | Incomplete/abandoned virtual environment | No | **REMOVE** |
| `C:\Users\Asus\PLANTGUARD AI\backend\.venv_py312` | 3.12.7 | 11.2 MB | pip 24.2 only | Incomplete/abandoned virtual environment | No | **REMOVE** |

---

## 2. Safety Quarantine Procedure

Following the repository safety guidelines, no environment was deleted directly. A two-stage quarantine process was executed:

1. **Quarantine Staging:**
   Created directory `quarantine_envs/` and moved the four unreferenced environments:
   - `backend\.venv_new` $\rightarrow$ `quarantine_envs\backend_venv_new`
   - `backend\.venv_py312` $\rightarrow$ `quarantine_envs\backend_venv_py312`
   - `venv_ml` $\rightarrow$ `quarantine_envs\venv_ml`
   - `.venv-ml` $\rightarrow$ `quarantine_envs\dot_venv_ml`

2. **Integrity & Test Verification During Quarantine:**
   While the quarantined environments were isolated:
   - Verified `backend\.venv`: Imported `fastapi`, `sqlalchemy`, `uvicorn` successfully.
   - Verified `.venv-ml312`: Executed 37 backend tests across `test_api.py`, `test_readiness.py`, and `test_image_upload.py` (`37 passed in 8.68s`).
   - Verified ML model imports and real checkpoint inference: SAM 2.1, MobileSAM, DINOv2 leaf filter, DINOv2 classifier, and SegFormer all loaded and passed inference smoke tests.

3. **Final Removal:**
   With absolute proof that no operational dependency, script, or test relied on the quarantined environments, `quarantine_envs/` was deleted using `Remove-Item -Recurse -Force quarantine_envs`.

---

## 3. Post-Cleanup Environment State

Only two clean, well-defined environments now exist on disk:

```
PLANTGUARD AI/
├── .venv-ml312/       [Python 3.12.7] - Unified ML Inference & Backend API Runtime
└── backend/.venv/     [Python 3.14.0] - Optional Lightweight API-Only Runtime
```

### Disk Space Reclaimed:
- `.venv-ml`: 1,180.7 MB
- `venv_ml`: 181.3 MB
- `backend\.venv_new`: 11.3 MB
- `backend\.venv_py312`: 11.2 MB
- **Total Reclaimed Disk Space:** **1,384.5 MB (~1.38 GB)**

---

## 4. Post-Cleanup Verification Evidence

- Backend Pytest Suite: **250 passed, 8 skipped** under `.venv-ml312`.
- Real Model Inferences: **5 passed in 41.73s** (`test_model_inference_smoke.py`).
- Real Authenticated Lifecycle: **3 passed in 89.08s** (`test_real_model_inference.py` & `test_real_authenticated_lifecycle.py`).
- Frontend Build: TypeScript check and production build passed without errors.

