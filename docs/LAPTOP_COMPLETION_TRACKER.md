# PlantGuard AI laptop completion tracker

**Audit date:** 2026-10-27  
**Scope:** application completion on the current Windows laptop. RTX 5060 model validation and the explicitly deferred optimization/OOD calibration work are outside this audit. No checkpoint was modified. Agent orchestration, RAG, and recommendation-agent work remain future scope.

## Phase 5 environment readiness gate

- Existing `backend/.venv` is usable for this phase: Python 3.14.0, all dependencies in `backend/requirements.txt`, `httpx` 0.28.1 and `pytest` 9.1.1 are installed; `pip check` reports no broken requirements; imports of the FastAPI app, scan router, storage factory and application model service succeed.
- No dependency installation or ML/GPU package change was needed. The separate ML environment was not used.
- The configured PostgreSQL database was reachable. Before writing code, `alembic current` reported `0004_analysis_storage_reference`, and read-only schema introspection verified `analyses` and `users` columns/foreign key. The test suite uses SQLite and a local test storage adapter; it does not contact configured cloud storage. The test-only PostgreSQL probe is skipped because `TEST_DATABASE_URL` is unset; five real-model tests are skipped because the compatible ML runtime/config and explicit artifact opt-in are unavailable.
- The configured storage provider is cloud storage, but its credentials/config values were not printed and no live storage request was made. Local storage is injected in lifecycle tests.
- `backend/pytest.ini` and `backend/pyproject.toml` are absent; tests are run directly with the existing pytest install. `pytest-asyncio` is absent but not required by the tests run.

## Status definitions

- **verified** — behavior was directly inspected and an applicable check/test passed in this environment.
- **implemented but unverified** — implementation exists, but its runtime behavior or target environment has not been demonstrated here.
- **blocked** — a concrete external dependency, artifact, service, or hardware limitation prevents verification/completion.
- **future scope** — explicitly deferred product work.

## Subsystem status

| Subsystem | Current implementation and evidence | Verified behavior | Gap / acceptance criteria | Laptop feasibility / status |
|---|---|---|---|---|
| FastAPI startup and non-ML endpoints | `backend/app/main.py`, `backend/app/api/health.py`, `backend/app/core/config.py` | Lifespan does not load model weights. `/api/ping`, `/api/demo`, and root route pass `backend/app/tests/test_api.py`. Startup can import the application without model artifacts. | Run the app against a deployment-like DB/storage configuration and verify operational liveness/readiness separately. | Laptop-feasible; **verified** for route tests/import, deployment config remains unverified. |
| Scan upload and lifecycle | `backend/app/api/v1/analyze.py`, `backend/app/models/analysis.py`, `backend/app/schemas/analysis_lifecycle.py`, `backend/migrations/versions/0005_analysis_failure_data.py`, `backend/app/tests/test_image_upload.py` | Authenticated uploads validate MIME/content, size, and image decoding; store private object; create pending record; run actual inference service; save result only on success; persist `failed` plus safe structured code/stage/message/time and expose it through owner-scoped retrieval. Internal exception details are not returned to clients or saved in the public failure payload. Tests cover valid upload, typed and unexpected model failures, invalid files, storage/database cleanup and retrieval/history ownership. | Inference currently runs synchronously in request worker. Production needs restart recovery, request correlation/idempotency and operational timeout policy. | Laptop-feasible lifecycle **verified** by SQLite/local storage test suite using injected service test doubles only (not real ML). |
| Scan retrieval/history API | `backend/app/api/v1/analyze.py`, `backend/app/api/v1/ownership.py`, `backend/app/tests/test_image_upload.py`, `backend/app/tests/test_ownership.py` | Owner-scoped detail and newest-first history are implemented; unknown and foreign IDs return equivalent 404. | Pagination UI and long histories need product review; no image/mask asset retrieval route. | **verified** for tested API contract. |
| Frontend routing/authentication | `frontend/client/App.tsx`, `frontend/client/auth/AuthContext.tsx`, `frontend/client/pages/AuthPage.tsx`, `frontend/client/lib/auth-api.ts` | Public login/register and authenticated app routes are wired; frontend test suite passes. | Verify against configured FastAPI URL, CORS, token lifetime and production hosting. | **verified** as a local build; live deployment integration **implemented but unverified**. |
| Frontend scan/results contract | `frontend/client/lib/api.ts`, `frontend/shared/api.ts`, `frontend/client/pages/ScanPage.tsx`, `frontend/client/pages/ScanResultsPage.tsx`, `frontend/client/lib/api.spec.ts` | Lifecycle type now includes the backend's `result`; completed results render stored summary, leaf classifications, severity and warnings. Structured 503 errors preserve code/stage/analysis ID, and failed inference navigates to its persisted failed record. Frontend typecheck, Vitest and production build pass. | UI has no authenticated mask or explanation asset download because no corresponding owner-checked API exists. Add component-level rendering tests and verify in a browser against live API. | **verified** by typecheck (static), 12 frontend tests, and client/server builds; live visual/backend integration **implemented but unverified**. |
| Frontend history and plant/product routes | `frontend/client/pages/HistoryPage.tsx`, `frontend/client/pages/PlantsPage.tsx`, `frontend/client/App.tsx` | History uses the real owner-scoped analyses API. Plant records, settings, chat, weather, recommendations and other non-scan sections contain placeholders or static content. | Build actual plant records only with specified data/API requirements. Do not present placeholder routes as complete. | History **verified** by frontend build/API type. Plant records and other placeholder screens are **future scope** or need product requirements. |
| Database schema and migrations | `backend/app/models/analysis.py`, `backend/app/models/user.py`, `backend/migrations/env.py`, `backend/migrations/versions/0001_initial_analysis.py` through `0005_analysis_failure_data.py`, `backend/app/tests/test_database_models.py` | Before changes, live Alembic revision was `0004_analysis_storage_reference`; read-only PostgreSQL introspection confirmed `analyses` and `users` schema. Applied only nullable JSONB column migration `0005_analysis_failure_data`; verified live revision is now head and column is nullable JSONB. SQLite metadata/model tests pass. | Review historical 0003/0004 against legacy populated databases separately. Validate rollback policy before any downgrade; 0005 downgrade removes failure details and must not be used where those records need preservation. | Current additive migration **verified** on configured PostgreSQL; production backup/rollback policy still needs deployment review. |
| Image/object storage | `backend/app/storage/{interface,factory,local,r2,supabase}.py`, `backend/app/tests/test_object_storage.py`, `test_r2_storage.py`, `test_supabase_storage.py`, `test_image_upload.py` | Explicit local/R2/Supabase selection; factory does not silently fall back. Upload/lifecycle tests exercise private local storage and failure cleanup. | Cloud providers/credentials/network behavior and production access policy not verified. Add authenticated image retrieval only if required. | Local storage **verified** by tests; cloud adapter execution **implemented but unverified**. |
| Model interfaces and pipeline | `backend/app/ml/{service,pipeline,contracts,errors,device,registry,variants,runtime,remote}.py`, `backend/app/ml/adapters/*.py`, `backend/app/services/plant_analysis_service.py`, `backend/app/tests/test_inference_service.py`, `test_ml_foundations.py`, `test_device_variants.py` | Required order is encoded: SAM 2.1 → DINOv2 S/14 filter → DINOv2 B/14 classifier → SegFormer-B0 PlantSeg → reliability/severity/explanation/result. Lazy adapter loading, bounded inference slot, explicit typed failure paths and checksum-gated variants exist. CPU contract tests pass. No fallback heuristic/mock is used by production service. | Real load/inference for every artifact, original preprocessing/mapping confirmation, output quality and full API success must be demonstrated on available artifacts/hardware. Current model health is a prerequisite check, not proof weights load or inference works. | CPU contract boundary **verified**; real model pipeline **blocked** pending physical artifacts/runtime. |
| Model artifacts and device runtime | `artifacts/model_manifest.json`, `docs/MODEL_ARTIFACT_INVENTORY.md`, `docs/LOCAL_ML_ENVIRONMENT.md`, `docs/CPU_MODEL_SMOKE_TESTS.md`, `backend/requirements-ml.txt` | Manifest/inventory identify the four original artifacts and required config/mapping locations. CPU stage smoke tooling exists. | Current checkpoint locations are cloud/reparse-point backed and hashes are unset; model runtime dependencies are isolated and not installed in this app environment. Do not mark any model ready from path names alone. | Artifact validation and real inference **blocked** until local bytes and compatible environment are staged; CUDA/SAM verification specifically requires RTX 5060. |
| Reliability, severity, explainability | `backend/app/ml/ood.py`, `backend/app/ml/severity.py`, `backend/app/schemas/inference.py`, `docs/RELIABILITY_AND_OOD.md`, `docs/SEVERITY_METHOD.md`, `docs/EXPLAINABILITY.md` | Typed results distinguish uncertainty/calibration and severity availability; severity consumes segmentation/leaf mask outputs. CPU unit/contract coverage exists. | OOD remains provisional and uncalibrated; severity depends on validated segmentation labels/alignment; explanation quality has not been evaluated with model weights. | Contract tests laptop-feasible; calibration and model-dependent evaluation **blocked** for RTX/data evaluation. |
| Authentication and authorization | `backend/app/api/v1/auth.py`, `backend/app/api/v1/ownership.py`, `backend/app/core/security.py`, `backend/app/tests/test_authentication.py`, `test_ownership.py`, `test_image_upload.py` | JWT auth, password hashing, owner-scoped scan operations and unauthorized behavior have test coverage. The targeted API/ownership suite passed. | No independent security assessment, rate limits, session revocation policy or deployment secret management validation. | **verified** at tested application behavior; production security posture **implemented but unverified**. |
| Runtime diagnostics and readiness | `backend/app/api/admin.py`, `backend/app/api/v1/analyze.py`, `backend/app/ml/runtime.py`, `backend/app/ml/device.py`, `backend/app/tests/test_api.py` | Protected runtime diagnostics avoid returning secrets and artifact paths. Analysis health now reports typed `unavailable` or `unverified` and never reports `ready` based only on path/config prerequisites; inference remains unavailable until integrity and real inference are verified. API liveness and model readiness remain separate. | Readiness currently does not prove actual inference for any profile; add an authenticated staging smoke result only after model loads can be validated. Test remote/CUDA readiness on their target environments. | **verified** for laptop's unavailable and injected unverified cases; target runtime readiness remains blocked. |
| Legacy routes and service adapters | `backend/app/api/scans.py`, `backend/app/api/v1/agentic.py`, `backend/app/services/plant_analysis_service.py`, legacy schemas under `backend/app/schemas/` | Legacy video/scan/agent routes explicitly return unavailable errors; typed model result is adapted through existing service boundary. | Several old paths/schemas remain alongside canonical `/api/v1/analyze/*`. Reconcile only after callers and compatibility requirements are identified. | Laptop-feasible; partial/duplicate API surface **implemented but unverified**. |
| Deployment and startup instructions | `backend/requirements.txt`, `backend/requirements-ml.txt`, `backend/alembic.ini`, root/backend env examples, `MANUAL_SETUP.md`, `docs/LOCAL_ML_ENVIRONMENT.md`, frontend Vite/Netlify configuration, `frontend/README.md` | Separate API and optional ML dependencies are documented. Frontend production bundle builds. There is no root or backend README; the frontend README is a generic Express/Vite starter document. Netlify/Express starter is not itself the FastAPI model deployment. | Select and test a FastAPI deployment topology, DB migration process, object store, frontend API URL/CORS and secrets. Replace starter setup claims with project-specific instructions after topology is chosen. Do not claim the current frontend bundle proves backend deployment. | Configuration work laptop-feasible; production deployment is **blocked** pending topology/credentials. |
| Agent orchestration, RAG, recommendation agent | `backend/app/agent/`, `backend/app/llm/`, `/api/v1/agentic` | Existing code is present; route is disabled/unavailable. | Explicitly excluded from this completion phase. Existing ordinary plant-care content can remain, but no generated recommendations may be presented as active. | **future scope**. |

## Laptop versus RTX 5060 boundary

### Safe laptop work

- Frontend API contract, scan lifecycle display, history, auth/ownership, upload validation and local storage tests.
- CPU-only contracts, config validation, readiness/error behavior, result serialization, migrations on a disposable local database, documentation and deployment configuration.
- No weights need to be loaded for these tasks.

### Must wait for RTX 5060 or real artifact host

- Confirm each checkpoint is physically available and compute its SHA-256 without modifying bytes.
- Install/verify a supported GPU runtime and SAM 2.1 dependencies; load each original model one at a time.
- Run real SAM proposal, DINO filter/classification, and PlantSeg inference; establish trained label mapping and tensor/mask alignment.
- Run real full pipeline/API scan, confirm persisted predictions, collect memory/latency and verify output quality.
- Any CUDA/FP16/compilation/quantization comparison, model optimization or calibration data runs.

## Changes made during this audit

- `frontend/shared/api.ts`: lifecycle response now models the actual optional persisted `FullScanResult`, with versioned summary/leaf/warning fields matching backend Pydantic contracts.
- `frontend/client/lib/api.ts`: structured inference error parsing now preserves safe `message`, `code`, `stage`, and `analysis_id` fields.
- `frontend/client/pages/ScanPage.tsx`: accurate scan copy and navigation to the persisted failure record when the API supplies its ID.
- `frontend/client/pages/ScanResultsPage.tsx`: renders returned completed results and explicit pending, failed, or inconsistent states; does not claim inference is absent or invent a diagnosis.
- `frontend/client/pages/Index.tsx`: removed stale claim that account and scan-history services do not exist.
- `frontend/client/lib/api.spec.ts`: covers structured inference failure and string-detail API errors.
- `backend/app/tests/test_api.py`: updated stale health expectation to assert the current unavailable-artifact/runtime response.
- `backend/app/models/analysis.py`, `backend/app/schemas/analysis_lifecycle.py`, `backend/app/api/v1/analyze.py`: persisted safe structured failure details and included them in scan retrieval; model-internal messages remain generic.
- `backend/migrations/versions/0005_analysis_failure_data.py`: added reversible nullable JSON/JSONB `failure_data` migration.
- `backend/app/tests/test_image_upload.py`, `backend/app/tests/test_api.py`: tested persisted typed/unexpected failures, owner retrieval, and readiness reporting that does not claim unverified inference is ready.
- `frontend/shared/api.ts`, `frontend/client/pages/ScanResultsPage.tsx`: typed and displayed the safe scan failure reason.

## Verification performed

| Check | Result | Notes |
|---|---|---|
| `npm.cmd run typecheck` in `frontend/` | **PASS** | TypeScript check completed after API/result contract changes. |
| `npm.cmd test -- --reporter=dot` in `frontend/` | **PASS** | 4 test files, 12 tests passed. Vite reports existing config-loader warnings. |
| `npm.cmd run build` in `frontend/` | **PASS** | Client and server bundles built. This does not prove FastAPI deployment. |
| `backend/.venv/Scripts/python.exe -m pytest app/tests/test_api.py app/tests/test_inference_service.py app/tests/test_ml_foundations.py app/tests/test_device_variants.py -q` | **PASS** | 55 passed; 5 existing warnings. |
| `backend/.venv/Scripts/python.exe -m pytest -rs app/tests/test_api.py app/tests/test_image_upload.py app/tests/test_ownership.py app/tests/test_database_models.py -q` | **PASS** | 24 passed, 1 skipped because `TEST_DATABASE_URL` is unset; local SQLite/storage test boundary, no real model inference. |
| `backend/.venv/Scripts/python.exe -m pytest -rs app/tests -q` | **PASS** | 176 passed, 6 skipped: 1 live-PostgreSQL test needs `TEST_DATABASE_URL`; 5 genuine model tests need the compatible ML runtime/SAM config and explicit artifact opt-in. Unit/API fakes are test-only. The broader full discovery command still cannot collect `app/agent/tests/test_service.py` due its missing `MLCapabilityUnavailable` import. |
| Complete backend `pytest -q` | **BLOCKED at collection** | `app/agent/tests/test_service.py` imports missing `MLCapabilityUnavailable` from `app/services/plant_analysis_service.py`. Agent orchestration is explicitly future scope; this existing collection issue is recorded and was not changed. |
| `backend/.venv/Scripts/python.exe -m compileall -q app` | **PASS** | Backend source syntax compilation. |
| `alembic upgrade head`, `alembic current`, and PostgreSQL schema introspection | **PASS** | Live DB was at revision 0004 before the additive migration and is at `0005_analysis_failure_data` after; `failure_data` is nullable JSONB. No data was reset or deleted. |
| Real model inference/CUDA | **BLOCKED** | No verified checkpoint bytes/hash or ML runtime demonstrated on this laptop. |

## Remaining work and exact acceptance criteria

1. **Complete local/production API topology:** document FastAPI host, DB, object storage, `VITE_API_URL`, CORS and secret provisioning; acceptance: clean install/startup, `/api/ping`, auth, authenticated upload, history/detail all work in a staging environment.
2. **Migration safety:** review historical migration 0003/0004 compatibility with any legacy populated installation; acceptance: upgrade a disposable copy with representative pre-existing rows and verify owner/storage fields without data loss. The current configured database was already at 0004 and accepted the additive 0005 migration.
3. **Storage asset lifecycle:** define owner-checked image/mask/explanation retrieval if the product needs overlays; acceptance: foreign account cannot fetch assets, and unavailable assets do not invalidate stored inference summaries.
4. **Synchronous scan operational limits:** define request timeout, duplicate retry behavior, cancellation and restart recovery; acceptance: a process interruption cannot leave misleading completed state and duplicate requests have explicit outcomes.
5. **Browser/API integration:** exercise success and typed failure against live FastAPI; acceptance: completed result renders stored response, unavailable model displays persisted failure, history/detail stay owner-scoped.
6. **RTX original-model validation:** see the RTX checklist in `docs/CPU_MODEL_SMOKE_TESTS.md` and `docs/DEVICE_AND_OPTIMIZATION_GUIDE.md`; acceptance: verified hashes, original model load/inference evidence, PlantSeg mapping, API persistence, resource measurements. Optimization and OOD calibration remain separate later work.

## Phase 5 completion and Phase 6 recommendation

The in-scope FastAPI application tests, frontend checks, and additive migration passed. The whole backend test discovery command remains unable to collect because the future-scope agent test imports missing `MLCapabilityUnavailable`. That import failure does not affect the passing `backend/app/tests` suite, but decide whether to repair the test boundary before requiring a repository-wide green test run.

Recommended Phase 6 prompt: “Complete PlantGuard laptop deployment and lifecycle hardening: choose/document the FastAPI + database + object-storage + frontend API topology; validate historical migration compatibility on a disposable populated database; define timeout/idempotency/recovery behavior for the existing synchronous scan endpoint; and run browser/API integration tests. First decide how to handle the existing whole-suite collection failure in the explicitly deferred agent tests, without implementing agent behavior. Do not load or change model weights, optimize models, calibrate OOD, or implement agents/RAG/recommendations.”

PlantGuard AI is **not production-ready**. Real model artifact/runtime validation and deployment environment verification remain outstanding.

## Phase 6 — Model-specific environment setup and integration gate

**Status:** CPU model environment and package imports are **verified**. No model artifacts have been loaded. Model-dependent checkpoint tests and service integration remain gated on artifact integrity and the unresolved WSL status.

| Area | Evidence from this phase | Status / next action |
|---|---|---|
| API environment | `backend/.venv`: Python 3.14.0, application dependencies present, no Torch/Transformers/model dependencies. It remains separate and untouched. | **verified** as a non-ML app environment; not a model runtime. |
| Existing ML environment | `.venv-ml`: Python 3.12.2, Torch 2.14.1+cpu, torchvision 0.29.1+cpu, Transformers 5.20.2. Missing SAM2/hydra/iopath/OpenCV; `pip check` identifies missing `python-dateutil` and `python-dotenv`. Project pins are 2.6.0/0.21.0/4.57.6. | **blocked for project model use**; preserved without repair or deletion. |
| DINOv2 S/14 and B/14 environment | `C:\PlantGuardEnvs\plantguard-vision-cpu`: Python 3.12.2, Torch 2.6.0+cpu, torchvision 0.21.0+cpu. Architecture imports pass. Checkpoint files are reparse points and hashes unset. | Environment **verified**; checkpoint load/inference **blocked** pending hydrated bytes and integrity verification. |
| SegFormer environment | Same verified environment; Transformers 4.57.6/safetensors 0.8.0 import; `pip check` clean; SegFormer model class import passes. Config says image size 224 while preprocessing says 512. | Environment **verified**; real load/inference **blocked** pending hydrated checkpoint and resolving preprocessing provenance. |
| SAM2 environment | User reports enabling Windows optional features and rebooting after WSL2 initially failed. The assistant runtime's WSL query is access denied; latest user-provided WSL output predates that repair. No Ubuntu distribution or SAM package is verified. | **blocked pending WSL status output**; CPU inference not attempted on the 16 GB laptop. RTX host remains preferred for practical inference. |
| Reliability/severity/explainability | Existing code/contracts and docs remain; OOD calibration not performed. Severity depends on validated disease labels/mask overlap; explanation requires actual model evaluation. | **implemented but unverified** on model outputs; CPU contract tests only can be used now. OOD fitting and output quality wait for GPU/data. |
| Model HTTP/subprocess boundary | FastAPI and model pipeline are separate Python environments; no separately verified local inference service was found in the inspected files. | **not implemented**; do not implement until user reports a successful CPU environment setup. Afterward design localhost-only readiness, schema, timeouts and bounded concurrency around the existing service. |
| Checkpoint integrity | Artifact entries are Windows `ReparsePoint`; no SHA-256 computed and no weight file read in this phase. | **blocked / ambiguous availability**; hydrate files or copy from the RTX source, preserve originals, then verify exact byte size and hash before loading. |

### Phase 6 actions and checks

- Inspected current dependency files, environment versions, model adapters, model architecture code, model manifest and relevant configuration/mapping files.
- Created `C:\PlantGuardEnvs\plantguard-vision-cpu` using Python 3.12.2 without changing global Python or existing environments. PowerShell activation was blocked, so the environment executable was used directly.
- Installed CPU Torch 2.6.0/torchvision 0.21.0, the pinned DINO/SegFormer dependencies, then `backend/requirements.txt` because importing the current `app.ml` package also imports storage dependencies.
- Verified Torch 2.6.0+cpu, torchvision 0.21.0+cpu, Transformers 4.57.6, safetensors 0.8.0, CUDA unavailable; `pip check` reports no broken requirements; DINO builder and SegFormer class imports pass from `backend/`.
- WSL initially reported virtualization/Virtual Machine Platform errors. User reports enabling Windows optional features and restarting; fresh `wsl --status` / `wsl --list --verbose` output is still needed. A tool-side WSL query returned access denied, so it is not treated as verification.
- No checkpoint was read, hashed, loaded or inferred; no CUDA test, training, optimization, or conversion run.
- Readable PlantSeg config/mapping currently encodes `0=background`, `1=diseased_region`; this is not independently validated against training metadata/checkpoint. `image_size=224` vs preprocessing `size=512` requires resolution before trusting mask output.

### Exact next action

Next, in regular PowerShell, run `wsl --status` and `wsl --list --verbose` and share both outputs. After that, verify model artifact files are hydrated local files before running any checkpoint smoke test; do not hash or load OneDrive placeholders.

### Next phase after environment verification

Only after reviewing successful setup output: confirm/hydrate checkpoint bytes and hashes, run DINO S/14 and B/14 and SegFormer one at a time with existing smoke tooling, resolve the SegFormer input-size provenance, then implement and test the localhost service/application adapter. SAM2 and CUDA baseline remain for the RTX 5060 host. No production readiness is claimed.
