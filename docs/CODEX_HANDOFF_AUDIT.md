# PlantGuard AI current-state audit

**Audit date:** 2026-10-27  
**Status:** PlantGuard is not production-ready. This audit describes the current working tree and does not treat historical documentation or filenames as proof of model execution.

## Scope and working-tree safety

Inspected repository instructions, current Git status, application routes, model adapters/service, schemas, migrations, storage and authentication code, frontend routes and API use, tests, manifests, runtime declarations, deployment configuration, and project documentation. No model was loaded; no checkpoint bytes were read or hashed; no GPU operation, download, training, export, or quantization was run. The actual `backend/.env` and `frontend/.env` were not read.

The working tree is already heavily modified. `git status --short` reports modifications to root/backend examples, backend config/routes/schemas/services/tests, frontend package manifests, project notes, and untracked ML code, scripts, docs, artifacts, and test images. It also reports tracked deletions under `ml/models/classification/`, `ml/models/disease segmentation/`, and the nested legacy `ml/models/leaf segmentation/PlantGuard/PlantGuard/` tree. Pytest temp directories `backend/.pytest-tmp/` and `backend/.phase2-pytest-tmp/` deny access. These changes were preserved. No reset, restore, cleanup, or model-file mutation was attempted.

The repository root `README.md` is generic Fusion Starter material. `CLAUDE.md`, portions of `PROJECT_BRAIN/`, `docs/PLANTGUARD_CURRENT_STATE.md`, `docs/ARTIFACT_MANIFEST.md`, and earlier audit prose contain stale or historical claims that conflict with current source (for example, describing pending-only uploads, unavailable ML integration, or heuristic SAM success). Current code and the checks recorded below take precedence. Root `AGENTS.md` sets applicable model immutability, model-order, fail-closed, and testing constraints; `frontend/AGENTS.md` and project architecture notes were also read.

## Capability status

**VERIFIED** means source-level behavior or the cited CPU test was actually checked. It does not imply real checkpoint inference. **PARTIAL** means implementation exists but important integration/validation remains. **MISSING** means no implementation was found. **BLOCKED** means this host cannot safely verify or execute the capability.

| Capability | Status | Evidence and limit |
| --- | --- | --- |
| SAM 2.1 Hiera Base Plus candidate masks | **PARTIAL** | `backend/app/ml/adapters/sam_adapter.py` constructs the SAM2 automatic mask generator from the checkpoint and package config, and `predict()` raises a capability error if it is not loaded. The ordered pipeline calls it first (`backend/app/ml/service.py`). No fallback mask is returned. SAM2 is not installed in the active Python environment; the checkpoint is a OneDrive reparse point; real load/inference was not run. |
| DINOv2 ViT-S/14 leaf filter | **PARTIAL** | `backend/app/ml/adapters/leaf_filter.py` builds the ViT-S/14 binary head, uses RGB 224×224 ImageNet normalization, strict state-dict loading, and `[negative, positive]` ordering. Pipeline threshold is positive probability ≥0.5. No checkpoint load, GPU/CPU output test, or v2-specific reproduced evaluation was run. |
| DINOv2 ViT-B/14, 38-class disease classifier | **PARTIAL** | `backend/app/ml/adapters/disease_classifier.py`, `backend/app/ml/architectures/dinov2.py`, and `artifacts/dino_disease/classes.json` define the classifier and ordered mapping; service validates exactly 38 unique class indices/labels before use. Checkpoint loading and model outputs were not run. |
| SegFormer-B0 PlantSeg disease segmentation | **PARTIAL** | `backend/app/ml/adapters/disease_segmentation.py` loads the local Transformers/safetensors checkpoint with config/preprocessing and validates mappings; service expects IDs 0 background and 1 diseased region and aligns output to crop shape. No checkpoint load/inference was run. Config/preprocessing/training metadata need reconciliation on the actual trained environment. |
| Ordered pipeline and typed contracts | **PARTIAL** | `backend/app/ml/service.py` implements SAM → DINO-S filter → DINO-B classification → SegFormer → result assembly with contract checks, bounded single-flight inference and lazy stage loading. CPU contract tests passed; real adapters are blocked. `backend/app/ml/pipeline.py` and `backend/app/ml/service.py` are overlapping orchestration implementations and need a documented single source of truth. |
| Runtime/device capability and variant gating | **PARTIAL** | `backend/app/ml/runtime.py`, `device.py`, `variants.py`, `artifacts/model_manifest.json`, and `/api/admin/runtime` provide CPU/CUDA/remote reporting and checksum-gated selection. Manifest checkpoint SHA-256 values are null, so local artifact selection fails closed. Only PyTorch CPU/CUDA adapters exist; other installed backends are diagnostics, not inference implementations. CUDA compatibility is not verified. `ApplicationPlantAnalysisService.is_ready()` checks file/dependency/config prerequisites but not manifest hashes/model load, so `/api/v1/analyze/health` can overstate readiness. |
| Quantization/optimized variants | **BLOCKED** | No optimized artifact is registered or validated. `docs/DEVICE_AND_OPTIMIZATION_GUIDE.md` marks SAM INT8/ONNX paths unsupported by current adapters and DINO/SegFormer candidates blocked pending runtime, dataset, and comparisons. No conversion/benchmark was run; none is classified “not beneficial.” |
| Reliability and OOD | **PARTIAL** | `backend/app/ml/service.py` validates finite/ranged probabilities, tensor shapes, mapping and mask outputs. `backend/app/ml/ood.py` emits entropy/confidence uncertainty with `calibration_status=incomplete`. No calibrated OOD validation or unsupported-species dataset evaluation was found. This is not a proven OOD detector. |
| Mask-based severity | **PARTIAL** | `backend/app/ml/severity.py` intersects the disease mask with the SAM leaf mask and records pixel counts/percentage; thresholds are configurable/provisional. Pure CPU boundary tests exist and passed. Thresholds are not clinically validated and real mask alignment has not been evaluated on artifacts. |
| Explainability | **PARTIAL** | DINOv2 classifier exposes `predict_with_attention`; pipeline assembles an optional class-specific visualization and tolerates attribution failure. Shape/failure contract tests exist. Explanation quality and faithfulness have not been evaluated; visual attribution is not causal evidence. |
| Authenticated image scan API and persistence | **PARTIAL** | `backend/app/api/v1/analyze.py` validates and privately stores uploads, creates owner-scoped `Analysis`, invokes inference in a threadpool, and persists `FullScanResult` JSON or a failed state. Migrations `0001`–`0004` define owner, storage key, result JSON and lifecycle fields. API test collection is blocked by missing `httpx`; no real-model endpoint request was run. Inference is inline with the HTTP request; no durable queue/recovery exists. |
| Other scan endpoints | **MISSING / disabled** | `backend/app/api/scans.py` returns 503 for `/api/scan` and `/api/scans*`; `/api/v1/analyze/video` returns 501. `backend/app/api/v1/agentic.py` returns 503. Do not confuse these with the authenticated `/api/v1/analyze/image` lifecycle. |
| Frontend authentication/history/upload | **PARTIAL** | `frontend/client/App.tsx`, `auth/AuthContext.tsx`, `AuthPage.tsx`, `ScanPage.tsx`, and `HistoryPage.tsx` implement protected navigation/auth and API calls. The UI currently tells users analysis is unavailable. `ScanResultsPage.tsx` still says inference is not integrated and does not render `result`; `frontend/shared/api.ts` omits the backend's `result` field. Authenticated scan result flow is therefore not completed end to end. |
| Plants, recommendations, weather, chat and profile | **MISSING / placeholders** | Plant and settings pages display unavailable states; recommendations, weather, assistant and profile routes are placeholder screens. No corresponding product APIs/persistence were found. |
| Security | **PARTIAL** | Auth code uses Argon2id and JWT bearer tokens; analysis lookups are owner-scoped; object storage providers are explicit with no provider fallback; uploads validate size/type/content; remote image transfer requires HTTPS/token/explicit authorization; diagnostics are protected and redact secrets/absolute paths. Frontend bearer tokens are held in `sessionStorage`, so XSS prevention is important. Production rate limits, durable job authorization/lifecycle, retention/deletion, end-to-end result/mask access policy, and deployed security posture remain unverified. |
| Deployment/operations | **PARTIAL / BLOCKED** | Frontend has Vite and Netlify configuration. Netlify function wraps the Express starter server, which only provides `/api/ping` and `/api/demo`; no FastAPI deployment target or proxy is configured in the checked-in Netlify files. No Docker/compose/worker deployment or production model artifact delivery was found. |

`backend/app/ml/pipeline.py` is a compatibility facade over `backend/app/ml/service.py`, not a second independent pipeline. `backend/app/ml/registry.py` still provides a separate size/existence inventory/readiness report; do not treat that coarse legacy report or `backend/app/ml/smoke_check.py` as equivalent to checksum-gated variant selection or a real load/inference smoke test.

## Artifact inventory finding

The expected path/size metadata and mapping/config facts are in [`MODEL_ARTIFACT_INVENTORY.md`](MODEL_ARTIFACT_INVENTORY.md). The four active checkpoint paths are present as filesystem entries but marked OneDrive reparse points:

- `artifacts/sam2/sam2.1_hiera_base_plus.pt` — 323,606,802 bytes.
- `artifacts/dino_leaf_filter/dino_leaf_filter_v2.pt` — 88,300,869 bytes.
- `artifacts/dino_disease/dino_disease_classifier.pt` — 346,516,841 bytes.
- `outputs/segformer_plantseg/best_model/model.safetensors` — 14,884,776 bytes.

Their manifest hashes are null/blocked; `backend/app/ml/variants.py` requires a valid hash and verified config/mapping identity before loading. Small mapping/config hashes are recorded in the manifest. File presence/size does not prove the checkpoint content, training history, or inference quality. The owner reports that the models were trained/tested on an RTX 5060; that report was not reproduced in this environment. SAM is a foundation checkpoint rather than a PlantGuard-trained model.

## Tests and commands checked

From `backend/`:

```powershell
$env:PYTHONPATH='.'
pytest -q app/tests/test_device_variants.py app/tests/test_inference_service.py app/tests/test_ml_foundations.py app/tests/test_reliability_severity_explainability.py
```

**Result: 69 passed in 2.11s.** These are CPU-safe contract/unit tests and do not load real artifacts. Compilation check:

```powershell
python -m compileall -q app\ml app\api\v1 app\api\admin.py app\services\plant_analysis_service.py app\schemas\inference.py scripts
```

**Result: passed.** Runtime inspection reported Windows 11, Python 3.14.0; `torch`, `torchvision`, `transformers`, `safetensors`, and `sam2` are absent; `httpx` is absent. `app/tests/test_image_upload.py` therefore cannot collect through Starlette `TestClient` here (`RuntimeError` because `httpx` is missing). Real model tests are explicitly opt-in/skipped or blocked by runtime/artifact requirements. No GPU availability/inference claim is made.

Other inspection commands: `git status --short`; `rg --files`; `Get-Content` for project instructions, manifests, source and deployment files; `Get-Item` for checkpoint path/size/attributes; `rg -n "TODO|FIXME|NotImplemented|placeholder|mock|fake|heuristic|fallback|disabled" ...`; `git diff --check`. Git checks report access denied for existing pytest temp directories and line-ending warnings. No secrets were read or recorded.

## Laptop-resolvable work

1. Synchronize the backend `AnalysisLifecycleResponse` with `frontend/shared/api.ts`; replace stale unavailable-analysis copy and render status, classification, severity, warnings and available explanation/results without inventing values.
2. Make API lifecycle tests runnable by supplying the missing test client dependency in a test/dev dependency set, then verify upload success, persisted failure, ownership and error response cases.
3. Consolidate `backend/app/ml/pipeline.py` and `backend/app/ml/service.py` ownership; remove or update stale route/status statements in project docs after source tests establish the current behavior.
4. Define durable worker/job semantics and object cleanup/retry behavior; make timeouts and failed state transitions explicit. Keep this separate from model weights.
5. Review duplicate package lock files, generated output and already-deleted tracked legacy model files with the owner; do not reset, restore, or remove these as part of the audit.

## RTX 5060/model-artifact work

1. Use a dedicated supported Python 3.12 environment and compatible PyTorch/CUDA build; install the pinned SAM2 package/config and optional ML requirements.
2. Ensure the four expected paths reference fully hydrated checkpoint bytes. Generate SHA-256 through `backend/scripts/hash_model_manifest.py` under the documented byte budget; never rewrite checkpoints.
3. Run `backend/scripts/gpu_environment_check.py --require-cuda`, then original model/SAM smoke and full ordered pipeline on approved fixtures. Record runtime, hashes, model outputs, latency, RAM/VRAM and artifact-specific evaluation evidence.
4. If supporting CPU/other targets, validate each original/optimized variant separately. Do not select quantized/compiled formats unless their compatibility and quality are measured and recorded in the manifest.

## Risks and unresolved questions

- Are OneDrive checkpoint entries hydrated on the RTX host, or must original bytes be transferred? The current host cannot establish that without reading/hydrating them.
- Which exact ViT-S checkpoint and evaluation correspond? The adapter chooses v2; historical evaluation metadata refers to v1.
- Does SegFormer `config.json`'s image size match the preprocessing/training path? Verify against the actual trained preprocessing on the originating environment.
- What API host will run CUDA inference? Netlify's function is Express-only and cannot host the Python/FastAPI model runtime as configured.
- Synchronous inference can exceed proxy/client timeouts and leave `pending` rows on process interruption. No worker recovery/lease mechanism exists.
- Frontend shared types and result display do not match the backend response. Its current upload copy is stale.
- Previous project docs claim measured results/hashes that are not represented by the current checksum-gated manifest or reproduced checks.

## Exact next implementation phase

**Complete the existing scan API/frontend result contract on the laptop.** Update the TypeScript response type and results screen/copy, add the missing test client dependency to the test environment, and run the authenticated scan lifecycle suite with fake model adapters. Keep real artifacts out of those tests. After that contract is verified, the next hardware step is checksum and original-model smoke validation on RTX 5060.

PlantGuard is not production-ready.
