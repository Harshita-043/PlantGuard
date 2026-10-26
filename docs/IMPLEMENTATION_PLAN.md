# PlantGuard AI implementation plan

This plan continues the existing application and model code. Keep the pipeline order fixed: SAM 2.1 Hiera Base Plus → DINOv2 ViT-S/14 leaf filter → DINOv2 ViT-B/14 classifier → SegFormer-B0 PlantSeg segmentation → reliability/OOD → mask-based severity → explainability and structured result. Preserve all existing checkpoint files. No model retraining or weight changes are part of this plan.

## Current state — 2026-10-27

The typed model service, lazy stage adapters, checksum-gated variant selection, runtime diagnostics and explicitly configured remote client exist. The authenticated upload route now calls the service and persists a typed result/failure. CPU contract tests passed (69); compilation passed. No real checkpoint inference has been verified in this environment.

The immediate user-visible gap is the frontend: its API lifecycle type omits the returned `result`, scan page says diagnosis is unavailable, and results page still says inference is not integrated and renders only lifecycle metadata. API route tests cannot currently collect because `httpx` is missing. The backend performs inference inline in the request worker; there is no durable job queue/recovery. Current checkpoint paths are OneDrive reparse points with unset hashes, so integrity checks block model loading. The present host is Windows 11/Python 3.14 and has none of the optional model runtime packages.

See [`CODEX_HANDOFF_AUDIT.md`](CODEX_HANDOFF_AUDIT.md) for evidence, blockers, and exact commands; [`MODEL_ARTIFACT_INVENTORY.md`](MODEL_ARTIFACT_INVENTORY.md) for artifact identities; and [`DEVICE_AND_OPTIMIZATION_GUIDE.md`](DEVICE_AND_OPTIMIZATION_GUIDE.md) for target-device steps.

## Next phase — finish scan API/frontend contract

**Status: not complete. Do this next on the laptop.**

1. Add the backend lifecycle `result` field to `frontend/shared/api.ts` using the versioned inference contract (avoid maintaining a second divergent schema where feasible).
2. Update `ScanPage.tsx`, `ScanResultsPage.tsx`, and `HistoryPage.tsx` to describe the synchronous behavior accurately, show failure states and render only available structured values. Parse structured API errors safely.
3. Add `httpx` to a test/dev dependency file, not the production API requirements solely for `TestClient`.
4. Run the authenticated upload/detail/history route suite against a fake inference service and local temporary storage. Verify completed result persistence, failed model state, owner isolation, and absence of false-success UI.
5. Preserve FastAPI as the model host. The Netlify Express function is not a FastAPI deployment. Decide and document the API hosting topology before calling the frontend path deployable.

**Exit:** frontend types match API; scan upload, history and detail represent real completed/failed result contracts; route tests pass with fakes; model inference remains clearly marked unverified until target-hardware runs.

## Following phase — stable scan lifecycle and operations

1. Decide whether to keep synchronous inference or add a durable queue/worker. If queued, define queued/running/completed/failed transitions, leases, retry policy, idempotency and restart recovery.
2. Handle the failure boundary across source image storage, mask/explanation asset writes and DB commits. Add owner-checked asset retrieval if the UI needs stored masks/overlays.
3. Add request correlation, bounded upload/inference concurrency, rate limits and operational metrics. Keep readiness distinct from liveness and from “weights loaded/validated.”
4. Reconcile legacy `/api/scan*` and agentic endpoints with the canonical `/api/v1/analyze/*` contract; retain explicit 503/501 responses until backed by working implementations.
5. Replace stale project-state copy and claims in root README, `PROJECT_BRAIN/`, and historical docs only after implementation evidence is updated.

**Exit:** upload and result lifecycle is restart-safe, owner-scoped, observable and exercised at API level; unavailable capabilities remain explicit.

## RTX 5060 phase — artifact and original-model verification

This is separate from frontend/API contract work and does not require training.

1. Prepare a dedicated Python 3.12 environment with a PyTorch build compatible with the installed NVIDIA driver/CUDA runtime. Install `backend/requirements-ml.txt` and confirm SAM2's package config is present.
2. Confirm checkpoint paths resolve to actual local bytes, not cloud placeholders. Use `backend/scripts/hash_model_manifest.py --root .. --max-total-bytes 1000000000` from `backend/` after checking disk space; update hashes only from the files actually verified.
3. Run `backend/scripts/gpu_environment_check.py --require-cuda`, then original SAM2 GPU smoke and the full model baseline on approved fixtures within measured RAM/VRAM/time limits.
4. Save logs/reports with source revision, hashes, model versions, dataset/split, latency, peak RAM/VRAM and quality metrics. A passing smoke image is not dataset validation.
5. Confirm original preprocessing, class mapping, PlantSeg mask mapping/alignment, pipeline order, no-leaf/error behavior and API persistence under the target runtime.

**Exit:** all four original artifacts load from verified hashes on the target host; end-to-end API inference succeeds on approved fixtures; measured baseline and known quality limitations are recorded.

## Cross-device variant phase

1. Measure the original baseline first. Keep original checkpoints immutable.
2. Establish runtime compatibility and a target resource budget per device. CPU, NVIDIA CUDA, and remote GPU are distinct profiles; Intel/integrated graphics do not establish CUDA support.
3. Evaluate one architecture-compatible optimization at a time (for example, FP16 on verified CUDA hardware, or quantized/exported variants only when operator support exists). Do not assume INT8/ONNX/OpenVINO benefits.
4. Compare outputs against the original checkpoint on the same representative held-out inputs: class agreement/confidence drift, segmentation metrics, mask alignment/severity difference, latency, model load time, RAM and VRAM.
5. Register a variant only after its hashes, runtime, quality, compatibility, provenance and rollback target are complete and independently reviewed. The selector must continue to fail closed for unvalidated variants.

**Exit:** each supported profile has explicit validated variants and resource limits; untested devices return capability errors or use the explicitly authorized remote path.

## Product and release phase

1. Implement plant records and recommendation sources only after product behavior, ownership and evidence requirements are specified. Current pages are placeholders.
2. Validate explanation quality; keep uncertainty and attribution separate from predictions. Do not call provisional entropy a calibrated OOD detector.
3. Choose deployment topology for the FastAPI model backend, artifact storage, database, secrets, scaling, backup, migrations and worker lifecycle. Current Netlify configuration only wraps the Express starter server.
4. Run API/frontend/migration/integration/resource/security tests in the intended deployment environment. Publish actual outputs and blockers.
5. Make production readiness a release decision based on the deployed system, not code presence or historical claims.

## Laptop versus target-hardware work

Laptop-resolvable: frontend contract/copy, mocked API lifecycle tests, route/service design, docs cleanup, source-level compatibility checks, normal CPU unit tests and job lifecycle design.

RTX 5060 or equivalent CUDA host: access/checksum the current cloud-backed checkpoints, verify CUDA/PyTorch/SAM2 compatibility, load real models, run GPU inference, measure CUDA memory/latency, reproduce model metrics, and evaluate CUDA/FP16/compilation variants. Additional CPU/other-device hardware is needed to verify those profiles empirically. No GPU check has been claimed from this laptop.

## Release blockers

- Checkpoint hashes are null and OneDrive entries are reparse points; variant selection refuses them until bytes are available and verified.
- Optional ML dependencies and compatible CUDA runtime are absent here; Python 3.14 is outside the documented ML environment.
- Real artifact loading, end-to-end quality/latency and CUDA checks have not been reproduced.
- Frontend response type and result display are behind the backend contract; API route suite lacks `httpx` in this environment.
- No durable inference worker, FastAPI deployment target, production rate limiting or operational recovery has been verified.
- OOD calibration and explainability quality validation remain incomplete; no disease recommendations are generated by the model service.

PlantGuard AI is not production-ready.
