# PlantGuard AI Completion Report

Date: 2026-10-27

## What changed

- Audited the full application structure and documented its architecture, model sequence, data flow, current implementations, blockers and prioritized plan in [AUDIT.md](AUDIT.md).
- Fixed the repository-root Python namespace shim so `app.core` and `app.main` import from the backend package.
- Added a local Vite `/api` proxy to FastAPI, installed after Vite's own proxy middleware so it takes precedence over the starter Express endpoints.
- Restored a backward-compatible `MLCapabilityUnavailable` error as a typed `ModelCapabilityError` for the disabled legacy agent route. The API continues to fail closed and does not return fabricated inference.
- Applied EXIF orientation during inference image decode without rewriting the uploaded original; added a no-checkpoint regression test.
- Added `/api/health`, `/api/ready`, and `/api/models`. Readiness checks DB, configured storage reachability and actual loaded adapters; model metadata omits absolute paths, remote URLs, and secrets. `/api/ready` correctly remains 503 until prerequisites and loaded-model checks pass. Remote readiness accepts only an `available` health response.
- Added owner-scoped asset links: Supabase/R2 URLs expire after 300 seconds; local assets stream through the authenticated API. Added owner-scoped analysis deletion with cleanup of original and referenced result assets. The results UI displays the original image and leaf, lesion and CAM assets when available.
- Recorded SHA-256 values for the four original model files in `artifacts/model_manifest.json`. Only the manifest changed; checkpoint files were not rewritten. The hashes establish byte identity, not model provenance or accuracy.

## Verification

| Check | Result |
|---|---|
| Root package import smoke (`app`, `app.core.config`, `app.main`) | Passed |
| Frontend TypeScript (`npm run typecheck`) | Passed |
| Frontend tests (`npm test`) | 12 passed |
| Frontend production build (`npm run build`) | Client and server bundles passed |
| Local Vite proxy smoke (`GET /api/ping` through port 8080) | Passed; returned FastAPI `pong` |
| Health/readiness/models/storage-probe/asset-lifecycle tests | Passed; included in full backend suite |
| Backend CPU-safe suite (`python -m pytest -q -rs -p no:cacheprovider app/tests app/agent/tests app/llm/tests`) | 208 passed, 6 skipped |
| Real model inference | Blocked; compatible SAM2 runtime/config and explicit opt-in are unavailable |
| Live PostgreSQL test | Skipped; `TEST_DATABASE_URL` was not supplied |
| Supabase live storage test | Not run; no remote write was attempted |

The 6 backend skips comprise one live PostgreSQL connection check and five real-model smoke checks. The configured Python 3.12 ML environment currently has PyTorch, torchvision, Transformers and safetensors, but does not have SAM2, Hydra, iopath, OpenCV or ONNX Runtime. The available API environment is Python 3.14 and lacks the ML runtime. Therefore model load, end-to-end inference, CPU/GPU latency, RAM/VRAM use, accuracy, CAM quality, and quantization parity are unverified. No quantization or hardware performance figures are claimed.

## How to run locally

Open two terminals from `C:\Users\Asus\PLANTGUARD AI`.

Backend (use the configured backend virtual environment):

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev
```

The Vite development server proxies `/api` to `http://127.0.0.1:8000`; verified live by requesting `/api/ping` through Vite and receiving FastAPI `pong`. Set `VITE_API_URL` to the deployed API origin for production builds. Authentication and configured database/storage services still need to be reachable, and inference returns a typed unavailable error until the ML environment is prepared.

CPU-safe verification:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider app/tests app/agent/tests app/llm/tests
cd ..\frontend
npm run typecheck
npm test
npm run build
```

## Deployment and hardware status

No CPU/GPU deployment image, Compose stack, CI workflow or ONNX/INT8 profile is present. Current base checkpoints alone total 773,309,288 bytes. The ViT-B classifier checkpoint is approximately 347 MB and SAM2 Hiera Base Plus approximately 324 MB; loaded model RAM and CPU latency have not been measured. This is not sufficient to publish reliable minimum RAM/VRAM or expected latency requirements. The 38-class classifier and segmentation have no independently reproduced held-out metrics in this run.

Do not describe the current setup as “runs on any device.” The actual guarantee is fail-closed behavior when required inference capabilities are missing. CPU-only execution needs a compatible PyTorch/SAM2 dependency set and a real model smoke run on the target machine. GPU acceleration additionally requires a compatible CUDA/PyTorch installation; integrated graphics are not CUDA.

## Manual actions needed

1. Grant the configured S3 credentials `s3:ListBucket` permission needed by `HeadBucket` on the selected bucket so cloud storage readiness can verify bucket access.
2. Choose a supported ML execution target (native Windows with compatible wheels, or WSL2/Linux) and install the versions from `backend/requirements-ml.txt`, including SAM2 and its package config.
3. Run the documented real-model smoke tests with explicit opt-in and check available memory before attempting full CPU SAM inference.
4. Supply `TEST_DATABASE_URL` for live PostgreSQL verification; confirm migrations and backup/rollback against the intended database before rollout.
5. Confirm Supabase private bucket names, policy/RLS strategy and credentials, then exercise storage with a test project. No remote writes were performed here.
6. Provide held-out labeled calibration/evaluation data and provenance for OOD thresholds, temperature scaling, severity thresholds, CAM validation and any quality-gated quantization.
7. Configure the production frontend API origin and deploy FastAPI separately from the existing Netlify Express function.

## Deferred, in priority order

1. Real SAM2/DINOv2/SegFormer startup and inference verification on the chosen CPU/GPU target; profile RAM, latency and output sanity.
2. Resize/blur/multi-leaf rejection, startup model cache policy, true execution timeouts and pending-job recovery.
3. Feedback/corrections and model-version persistence; add retention and a durable cleanup retry queue for partial storage-delete failures.
4. Held-out calibration/evaluation, OOD fitting, temperature scaling and validation of CAM/severity results.
5. Quality-gated ONNX export/quantization with parity and accuracy reports; keep FP32 fallback until evidence supports variants.
6. Postgres RLS/storage policies, rate limits, request IDs, structured metrics, security/load tests, production migrations and durable work queue.
7. Docker/Compose, CI, E2E browser flow, deployment docs and unfinished product pages (weather, recommendations, chat, settings).
