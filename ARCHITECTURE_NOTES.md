# Architecture Notes

## Repository Overview (top‑level)
- `.env.example` – example backend environment variables.
- `backend/` – FastAPI backend source.
- `frontend/` – React frontend source.
- `artifacts/` – Model checkpoint files and optimized ONNX models.
- `configs/`, `reports/`, `outputs/`, `src/` – auxiliary scripts and documentation.
- `.venv-ml/` – Python virtual environment used for ML inference (currently incomplete).

## Key Backend Modules
- **Entry point**: `backend/app/main.py` – creates the FastAPI app, includes routers, and runs with uvicorn.
- **Configuration**: `backend/app/core/config.py` – loads settings from `.env` via `pydantic‑settings`. Important variables:
  - `DATABASE_URL`
  - `OBJECT_STORAGE_PROVIDER`
  - Supabase storage credentials (`SUPABASE_STORAGE_*`)
  - `JWT_SECRET_KEY`
  - Device/inference flags (`PLANTGUARD_DEVICE`, `PLANTGUARD_INFERENCE_PROFILE`, …).
- **Database session**: `backend/app/core/database.py` – builds a SQLAlchemy engine from `DATABASE_URL` and provides `get_db()`.
- **Authentication**: `backend/app/api/v1/auth.py` – JWT creation/verification using `settings.JWT_SECRET_KEY`.
- **Storage adapter**: `backend/app/storage/supabase.py` (and `backend/app/storage/local.py`) – implements upload, download and signed‑URL generation for Supabase.
- **ML Service**: `backend/app/ml/service.py` – orchestrates the pipeline (SAM segmenter, leaf filter, disease classifier, SegFormer, OOD, CAM, etc.). It loads model files from the `artifacts/` directory.

## Frontend Integration
- API client resides in `frontend/client/` (generated TypeScript client). It talks to the backend under the `/api/v1` prefix and passes the `Authorization: Bearer <jwt>` header for protected endpoints.

## Environment Variables (names only)
- `BACKEND_CORS_ORIGINS`
- `DATABASE_URL`
- `OBJECT_STORAGE_PROVIDER`
- `LOCAL_STORAGE_ROOT`
- `R2_BUCKET_NAME`, `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`
- `SUPABASE_STORAGE_ENDPOINT`, `SUPABASE_STORAGE_REGION`, `SUPABASE_STORAGE_BUCKET`, `SUPABASE_STORAGE_ACCESS_KEY_ID`, `SUPABASE_STORAGE_SECRET_ACCESS_KEY`
- `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`
- `PLANTGUARD_DEVICE`, `PLANTGUARD_INFERENCE_PROFILE`, `PLANTGUARD_CPU_MEMORY_LIMIT_GB`, `PLANTGUARD_CUDA_MEMORY_LIMIT_GB`, `PLANTGUARD_MAX_CONCURRENCY`
- `PLANTGUARD_REMOTE_INFERENCE_URL`, `PLANTGUARD_REMOTE_INFERENCE_TOKEN`, `PLANTGUARD_REMOTE_IMAGE_UPLOAD_AUTHORIZED`, `PLANTGUARD_REMOTE_MAX_IMAGE_BYTES`, `PLANTGUARD_REMOTE_TIMEOUT_SECONDS`, `PLANTGUARD_REMOTE_MAX_CONCURRENCY`
- `PLANTGUARD_DIAGNOSTICS_TOKEN`

## Observations
- The backend `.env` is present (see `backend/.env`) and contains proper Supabase credentials and a JWT secret.
- The SQLAlchemy engine is built using the `postgresql+psycopg` driver – the required driver (`psycopg2`/`psycopg`) must be installed.
- The ML inference environment (`.venv-ml`) currently lacks heavy packages such as `torch`, `torchvision`, `transformers`, `onnxruntime`, `sam2`, `mobile_sam`, and `opencv-python`. These are required for the pipeline.
- The repository includes a separate virtual environment for the backend (`backend/.venv`) which runs Python 3.14; the ML code specifies a 3.12 runtime in the documentation.

The next steps will recreate a clean Python 3.12 ML virtual environment, install the pinned ML dependencies, verify imports, then address DB connectivity and authentication.

