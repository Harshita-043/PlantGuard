# PlantGuard End-to-End Audit

**Audit status: Real local inference verified; not production-certified.** This audit preserves the existing model artifacts and database. No migrations or remote object writes were performed.

## 1. Executive summary

The authenticated image-analysis path, database persistence, configured storage readiness, and frontend build are present. A serious OOD fail-open path was found and fixed: missing or invalid calibration and unavailable classifier features can no longer be converted into a negative OOD decision. A provisional threshold exceedance now withholds the predicted class, and the UI identifies the result as a potential OOD input.

The configured PostgreSQL database responded to a read-only query and is at the repository migration head. The configured Supabase bucket passed its read-only readiness probe. All five model checkpoints listed in the model manifest match their recorded SHA-256 values.

The `.venv-ml312` Python 3.12 environment includes the required runtime. The CPU-safe backend suite passed (240 passed, 7 skipped). A full local CPU inference run on `IMAGE_APP.jpg` completed using the exact variants in the manifest: original SAM 2.1, DINOv2 ViT-S/14, DINOv2 ViT-B/14, and SegFormer. Candidate counts were 24 generated → 8 valid → 8 deduplicated → 7 leaf-filter accepted → 7 classifier eligible. All seven exceeded the provisional OOD threshold, so classifications were withheld and the plant summary was `unknown`. This image's class/source is not established, so this is not evidence that the image is OOD or that the threshold works. An opt-in authenticated API lifecycle test also passed with real inference, temporary SQLite, and local temporary storage; it retrieved the uploaded assets and completed result after disposing and recreating the database engine. This is not a browser test, backend-process restart, or remote-storage verification. The readiness endpoint verifies DB/storage, OOD calibration, runtime-compatible variants, and artifact identities without loading model weights. No remote-storage upload/readback or live frontend-to-backend real scan was performed.

## 2. Architecture and observed execution flow

1. The frontend scan page calls the authenticated `/api/v1/analyze/image` route.
2. FastAPI checks authentication and optional plant ownership, limits uploads to 10 MiB, checks MIME and decoded image format, and rejects malformed images.
3. The selected storage adapter writes the source image under the authenticated user's analysis namespace. The API now verifies the returned key and confirms object existence before creating the database record.
4. An `analyses` row is committed as `pending`; model inference runs in a worker thread.
5. `PlantAnalysisService` runs candidate generation (SAM 2, with the established MobileSAM fallback), mask contract checks and near-duplicate suppression, DINOv2 leaf filtering, DINOv2 disease classification, OOD scoring, then SegFormer segmentation and result assembly. Required inference errors mark the persisted analysis failed; a downstream SegFormer failure preserves available classification/OOD results as a partial analysis and explicitly leaves segmentation/severity unavailable.
6. Successful results are stored as JSON. History and asset routes enforce owner access; private remote assets use short-lived signed URLs and local assets use the authenticated proxy.

The separate legacy `/api/scan` endpoints are explicitly unavailable stubs. The active persisted workflow is under `/api/v1/analyze/image`, `/api/v1/analyses`, and `/api/v1/analysis/{analysis_id}`.

The configured variant settings were not connected to the selector: ONNX variant requests were ignored while the manifest selected original PyTorch/Transformers artifacts. No ONNX Runtime inference adapter exists. Variant settings now select an exact registered manifest variant; unregistered values fail with a typed capability error instead of silently selecting a different backend. The checked-in manifest still authorizes only original variants.

## 3. Findings

| Severity | Status | Finding |
|---|---|---|
| High | Fixed | OOD calibration and feature failures could previously produce `is_ood=false`, allowing a classifier result to appear complete. They now fail closed with typed errors. |
| High | Open | OOD calibration is an in-distribution 99th-percentile threshold only. The artifact metadata explicitly requires separate OOD evaluation; no external OOD performance or false-rejection rate is established. |
| Medium | Partially verified | Supabase bucket access passed a read-only HEAD probe, and local/test storage round trips pass. A live remote upload/retrieval was not attempted because no dedicated remote test namespace was confirmed. |
| Medium | Open | No source-attributed, held-out image manifest and external field/OOD evaluation set were verified or created. Real-world generalization remains unknown. |
| Medium | Fixed | `/api/ready` previously treated model residency as a prerequisite despite the intentionally lazy sequential lifecycle. It now distinguishes required capabilities from `models_resident`, verifies selectable variants and checksums without loading weights, and accepts the documented MobileSAM fallback when primary SAM 2 is unavailable. |
| Medium | Fixed | Model variant configuration was ignored, so ONNX requests silently ran original PyTorch/Transformers variants. Configuration now selects exact manifest entries and fails explicitly for unregistered variants. |
| Medium | Fixed | A SegFormer execution failure previously discarded valid classifier results. It now returns `partial`, preserves classification/OOD, and marks segmentation and severity unavailable. |
| Low | Fixed | SAM outputs had no service-level duplicate suppression or structured stage counts. High-containment duplicate masks are now removed before the leaf filter, and counts are returned through the compatible result contract. |

**Generalization root cause:** not established. No source-attributed, labeled, held-out real-world set was available to separate crop/segmentation errors, domain shift, and OOD threshold behavior. The one full-pipeline image is unlabeled and all seven candidate leaves were provisionally rejected; this is a single diagnostic observation, not an accuracy or OOD metric. Existing capped PlantVillage benchmark reports are not verified as independent held-out evidence and cannot explain the reported field-image failures.

The classifier currently receives the rectangular crop around each SAM bounding box; pixels outside the candidate mask are not suppressed. This may leave background or neighboring foliage in the classifier input, but changing mask/compositing policy without training-time preprocessing evidence could introduce a new mismatch. Evaluate this with labeled, source-separated images before changing preprocessing or lowering an OOD boundary.

**SAM configuration regression.** The fail-closed test had depended on ML prerequisites being absent; with `.venv-ml312` installed, SAM load attempts can reach the documented MobileSAM fallback. The end-to-end regression now explicitly uses a missing SAM config and unavailable fallback checkpoint, so it asserts failure rather than relying on environment-dependent skips or fabricated proposals. Separate loader tests verify both package-relative config success and a missing-config `INVALID_CONFIGURATION` failure before model construction. Readiness reports primary SAM 2 and MobileSAM fallback independently; missing SAM 2 alone does not make the application unavailable when a verified fallback and all essential stages are usable.

**Results UI and diagnostic semantics.** The actual persisted-scan results page now separates scan metadata, the primary diagnostic state, overview metrics, per-leaf cards, saved visual evidence, next steps, and expandable technical diagnostics. An OOD-rejected label is not rendered as a disease diagnosis; any visible class is explicitly a provisional candidate because OOD performance and classifier confidence are unvalidated. Severity categories are not shown as validated; mask coverage is shown only when segmentation counts, ratio, and severity pixel counts agree, and is labeled provisional (especially unvalidated for OOD inputs). Entropy, Mahalanobis distance/threshold, calibration state, segmentation counts, model versions, timings, and non-summary warnings are available on demand. Repeated backend prose was removed from the main results flow. The API already provided the required structured fields, so no duplicate API fields were introduced.

The reported `99.92% affected (high)` value is a ratio of SegFormer lesion pixels intersected with the selected leaf mask, divided by valid leaf-mask pixels. The counts and ratio are contract-checked before the interface shows this as **provisional lesion-mask coverage**; the categorical `high` severity is not presented because severity thresholds are not agronomically validated. This is a pixel measurement from a model mask, not a confirmed disease-severity assessment.

## 4. Files changed

- `backend/app/ml/ood.py`: validates NPZ and paired JSON calibration metadata, dimensions, class indices, finite values, covariance symmetry/positive-definiteness, threshold, and fails closed.
- `backend/app/ml/errors.py`: adds a typed OOD-calibration-unavailable error code.
- `backend/app/ml/service.py`: requires OOD results, suppresses the class when the provisional distance exceeds threshold, and excludes abstained leaves from the plant diagnosis summary.
- `backend/app/ml/service.py`: returns partial classification results when downstream disease segmentation fails, with severity explicitly unavailable.
- `backend/app/ml/service.py`, `backend/app/ml/variants.py`, and `backend/app/core/config.py`: connect variant configuration to exact registered manifest entries and reject unregistered backend requests rather than silently falling back.
- `backend/app/ml/adapters/sam_adapter.py`, `backend/app/ml/adapters/mobile_sam_adapter.py`, `backend/app/ml/service.py`, and `backend/app/schemas/inference.py`: record candidate funnel counts and suppress masks with at least 95% containment overlap.
- `backend/app/ml/service.py`: copies inputs into writable contiguous RGB buffers to avoid the PyTorch/torchvision warning observed on real-image inference.
- `backend/app/services/plant_analysis_service.py`: rejects OOD abstentions in the legacy response adapter instead of emitting an empty disease class.
- `backend/app/ml/adapters/disease_classifier.py`: adds feature extraction separate from attention so explainability failure does not bypass required OOD scoring.
- `backend/app/core/config.py`, `.env.example`, and `README.md`: document an optional OOD calibration path override, its paired metadata requirement, and treat an empty optional path as unset.
- `backend/app/api/v1/analyze.py`: verifies successful object storage writes before persisting a scan and maps OOD calibration unavailability to a sanitized service error.
- `backend/app/api/readiness.py`: separates required model prerequisites from residency and reports primary SAM 2 and optional MobileSAM fallback independently.
- `backend/app/services/plant_analysis_service.py`: checks that required DINOv2/SegFormer stages and at least one candidate-generator variant are selectable and integrity-verified; validates the configured SAM package config.
- `backend/app/ml/variants.py`: shares cached SHA-256 verification results across readiness requests without loading checkpoint tensors.
- `frontend/client/pages/ScanResultsPage.tsx`: displays potential OOD abstention separately from a disease class.
- `frontend/client/pages/ScanResultsPage.tsx`: visibly flags partial analysis outside the collapsed diagnostics section.
- `frontend/client/pages/ScanResultsPage.tsx` and `frontend/shared/api.ts`: expose stage candidate counts in technical diagnostics.
- `frontend/client/pages/ScanResultsPage.tsx`: restructures actual persisted results into a responsive dashboard, gates diagnosis labels by OOD state, and moves low-level diagnostics into expandable sections.
- `frontend/client/components/scan/LeafOverlay.tsx`: lists only visual assets present in the saved result, with consistent aspect-preserving image layout and explicit empty/load-failure states.
- `frontend/client/lib/scan-results.ts` and `scan-results.spec.ts`: centralize candidate/coverage/visualization presentation rules and test OOD rejection and mask consistency.
- `backend/app/tests/test_api.py`, `backend/app/tests/test_image_upload.py`, `backend/app/tests/test_inference_service.py`, `backend/app/tests/test_ood_mahalanobis.py`, `backend/app/tests/test_readiness.py`, `backend/app/tests/test_services.py`, `backend/app/tests/test_device_variants.py`, and `backend/app/tests/test_ml_foundations.py`: cover storage verification, OOD failure/abstention, lazy readiness, variant integrity, and valid/missing SAM config behavior.

Pre-existing worktree edits to the SAM 2 package-config lookup and its readiness test were retained; they were not reverted.

## 5. Configuration

Configuration values and credentials are intentionally excluded. The read-only probe confirmed that the runtime has a PostgreSQL URL, selects Supabase storage, and has a JWT secret configured. The OOD path override is unset, so the repository artifact path is used.

### Canonical Python runtime

- Use `.venv-ml312\Scripts\python.exe` (Python **3.12.7**) for backend startup, tests, and real inference.
- Verified versions: FastAPI 0.118.3, Uvicorn 0.24.0, Pydantic 2.12.5, SQLAlchemy 2.0.54, psycopg 3.3.6, PyTorch 2.6.0, torchvision 0.21.0, Transformers 4.57.6, SAM 2 1.0, pytest 9.2.0, and safetensors 0.8.0. MobileSAM is importable.
- PyTorch reports `torch.cuda.is_available() == False`; the validated inference run was CPU-only. No CUDA/GPU capability is claimed.
- `.venv-ml` is Python 3.14.0 with PyTorch 2.14.1/torchvision 0.29.2; it does not match the repository's tested Python 3.12/PyTorch 2.6 model compatibility and was not selected.
- `backend\.venv` is Python 3.14.0 without the backend or ML dependencies and is not a usable test/runtime environment.

Relevant setting names:

- `DATABASE_URL`
- `OBJECT_STORAGE_PROVIDER`
- `SUPABASE_STORAGE_ENDPOINT`, `SUPABASE_STORAGE_REGION`, `SUPABASE_STORAGE_BUCKET`, `SUPABASE_STORAGE_ACCESS_KEY_ID`, `SUPABASE_STORAGE_SECRET_ACCESS_KEY`
- `R2_ENDPOINT_URL`, `R2_BUCKET_NAME`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` when using R2
- `JWT_SECRET_KEY`, `BACKEND_CORS_ORIGINS`
- `PLANTGUARD_DEVICE`, `PLANTGUARD_INFERENCE_PROFILE`
- `PLANTGUARD_LEAF_FILTER_VERSION`, `PLANTGUARD_DISEASE_CLASSIFIER_VARIANT`, `PLANTGUARD_SEGFORMER_VARIANT` select exact registered manifest variants; a setting for an unregistered variant fails explicitly.
- Optional `PLANTGUARD_OOD_CALIBRATION_PATH`; the NPZ must have a matching JSON file with the same base name.
- An empty `PLANTGUARD_OOD_CALIBRATION_PATH` is treated as unset so copying `.env.example` does not replace the repository default with the current directory.

## 6. Database and migrations

- Read-only `SELECT 1`: **passed**.
- Live Alembic revision: **`0006_plants`**, matching repository head **`0006_plants`**.
- Live `analyses` table and `user_id` column: **present**.
- No migration was applied. No reset, data update, or destructive operation was run.
- Owner-scoped API tests and persisted-history tests passed in the test suite. Live history across a backend restart was not separately exercised.

## 7. Object storage

- Configured Supabase bucket readiness (`HEAD`): **passed**.
- Local storage upload/readback equality and analysis lifecycle tests: **passed**.
- Each new upload now verifies the provider-returned key and object existence before database persistence; failed verification is cleaned up and returns a sanitized 503.
- Live Supabase upload/readback equality: **blocked/not run** because the configured bucket was not confirmed to be a dedicated test namespace. No remote object was created or deleted.
- Private asset proxying, ownership checks, signed-URL bounds, and provider error handling have CPU-safe tests; a live signed download was not exercised.

## 8. DINOv2 classifier and artifacts

- The configured class map contains 38 unique class names. The classifier adapter specifies RGB input, 224×224 resizing, ImageNet mean/std normalization, and a 38-score output contract.
- Actual classifier execution uses the strict PyTorch checkpoint loader (`torch.load(..., weights_only=True)`, strict state-dict load, `eval()`, softmax). The configured ONNX variant request previously had no effect. The available ONNX export has an export-parity report, but it is not registered in the model manifest and no ONNX Runtime inference path exists; it is therefore not selected.
- The runtime selected `original-pytorch-fp32` for the leaf filter and disease classifier and `original-transformers-fp32` for SegFormer in the post-fix full-pipeline run. The configured leaf-filter version now matches the manifest-verified v2 checkpoint; the repository does not currently register a v1 leaf-filter variant.
- The classifier architecture exposes a 768-dimensional CLS feature used by Mahalanobis scoring. The calibrated embedding's exact training/preprocessing provenance could not be independently reproduced because the calibration-fitting code is unavailable.
- Runtime inventory: SAM 2.1 automatic mask generation consumes raw RGB `uint8 (H,W,3)` and returns masks in source-image coordinates; MobileSAM uses an 8×8 positive-point grid only as fallback. The DINOv2 ViT-S/14 v2 filter resizes RGB crops to 224×224, ImageNet-normalizes, applies sigmoid to one logit, and accepts positive probability ≥0.5. The ViT-B/14 classifier uses the same RGB/224/ImageNet preprocessing and returns 38 softmax probabilities plus a 768-D CLS feature. OOD uses class-conditional Mahalanobis distance on that feature and a strict distance-over-threshold decision; its operating quality is unvalidated. SegFormer-B0 consumes RGB/512/ImageNet-normalized crops and returns a binary background/disease mask aligned to the crop.
- The service-level duplicate rule removes a lower-ranked mask when at least 95% of the smaller mask's area overlaps. The `generated` count is the raw proposal count from the selected segmentation adapter; `valid` counts candidates passing service contracts and the candidate cap.
- DINOv2 Attention Rollout is computed from CLS-to-patch attention across transformer blocks. It is not class-conditioned; the UI labels it as an attention visualization, not causal evidence or proof of the predicted class.
- SHA-256 comparison against `artifacts/model_manifest.json`: **match for all five listed original checkpoints** (DINOv2 classifier, DINOv2 leaf filter, SAM 2.1, MobileSAM, and SegFormer). Hashing was read-only; no checkpoint was modified.
- In `.venv-ml312`, real DINOv2 leaf-filter and disease-classifier loading/output-contract tests passed; the classifier emitted the expected 38-class distribution on a synthetic smoke-test input.
- SegFormer real-checkpoint output/mask-shape smoke passed. The full pipeline loaded and executed the original SAM 2.1, DINOv2 ViT-S/14, DINOv2 ViT-B/14, and SegFormer variants on `IMAGE_APP.jpg` on CPU; it returned 24 raw proposals, 8 valid and deduplicated masks, and 7 classifier-eligible leaves with no MobileSAM fallback.
- The test image has no verified label/source in this audit. Its seven provisional OOD threshold exceedances led to seven withheld class labels and an `unknown` summary; this observation requires investigation, not a claim about correctness.

## 9. OOD calibration and behavior

- `artifacts/dino_disease/ood.npz` was present and read without loading model checkpoints: 38 class-index entries, means shaped 38×768, inverse covariance shaped 768×768, finite values, and a positive threshold near 2474.644.
- Paired metadata identifies class-conditional Mahalanobis scoring, 768 features, class indices 0–37, and the in-distribution 99th percentile. The score is the quadratic distance from the predicted class mean using the stored inverse covariance; the decision uses strict `distance > threshold`.
- Calibration loads once into a validated cache. Missing, corrupt, incompatible, non-finite, or unscorable calibration/features fail closed. A threshold exceedance withholds the class and leaves the plant summary unknown when no classified leaves remain.
- The threshold remains explicitly **unvalidated for OOD detection**. The interface labels the result provisional; a threshold exceedance is not represented as a validated OOD diagnosis.
- Controlled tests cover scores below, at, and above the threshold; missing/corrupt calibration; invalid dimensions and NaNs; OOD scoring exceptions; and class withholding. No genuine supported, unseen-disease, non-leaf, or unrelated natural images were evaluated.
- One local end-to-end image run exercised the true OOD scoring path; its unverified image provenance prevents using it as an OOD evaluation.

## 10. Test-image manifest and provenance

No new test images or labels were fabricated or added. The repository's calibration metadata references a PlantVillage validation source, but this audit did not establish access to a held-out test split or independently inspect image hashes/duplicates. No reproducible source/license-attributed image manifest was available, so the requested `supported_in_distribution`, `healthy_supported`, `unseen_disease_or_plant`, `non_leaf_objects`, and `corrupt_or_invalid` dataset suite remains **not created / not verified**. Synthetic images used by unit tests are limited to deterministic contract tests and are not accuracy evidence.

## 11. Commands and observed results

- `.venv-ml312\Scripts\python.exe -m pytest -q` — **240 passed, 7 skipped**, one dependency deprecation warning plus third-party `timm`/MobileSAM warnings. The skipped tests require explicit real-model opt-in.
- `Set-Location backend; ..\.venv-ml312\Scripts\python.exe -m pytest -q app\tests\test_device_variants.py app\tests\test_readiness.py app\tests\test_inference_service.py app\tests\test_api.py app\tests\test_services.py` — **68 passed** before candidate-count coverage was added; the final full-suite result below includes the additional tests.
- `Set-Location frontend; npm.cmd run typecheck` — **passed**.
- `Set-Location frontend; npm.cmd test` — **5 files, 24 tests passed**, including tests for OOD rejection (including contradictory flag/score handling), candidate labeling, mask consistency, and visualization availability.
- `Set-Location frontend; npm.cmd run build` — **client and server production builds passed**.
- Real DINOv2 leaf-filter/classifier and SegFormer checkpoint contract tests were previously recorded as **3 passed**; the post-change full CPU inference run additionally exercised all four selected model stages.
- Full local inference run using `.venv-ml312\Scripts\python.exe` on `IMAGE_APP.jpg` after explicit variant wiring — **completed** on CPU; exact manifest variants selected, original SAM 2.1 used, counts `24 → 8 → 8 → 7 → 7`, seven provisional threshold exceedances, all classes withheld, all seven SegFormer masks produced.
- `Set-Location backend; ..\.venv-ml312\Scripts\python.exe -m alembic -c alembic.ini heads` — **`0006_plants (head)`**.
- Read-only configured dependency probe under `.venv-ml312` — database `SELECT 1` **passed**; live revision `0006_plants` and `analyses.user_id` checked; Supabase bucket readiness **passed**. No secrets or endpoint values were emitted.
- `Set-Location backend; ..\.venv-ml312\Scripts\python.exe -c "from fastapi.testclient import TestClient; from app.main import app; r=TestClient(app).get('/api/ready'); print(r.status_code); print(r.json())"` — **200 ready**; database/storage/prerequisites/SAM2/MobileSAM checks `true`, `models_resident=false`. The endpoint SHA-256-verified selected variants without loading model tensors.
- Manifest SHA-256 verification — **all five model entries matched**.
- `git diff --check` — **passed**.

## 12. Verification status

**Passed:** Python 3.12 backend suite; focused variant/readiness/inference/API regression tests; real DINOv2/SegFormer checkpoint smoke tests previously recorded in this audit; local end-to-end original-model CPU pipeline on `IMAGE_APP.jpg` after variant wiring; SegFormer-failure partial-result tests; opt-in authenticated API upload/inference/persistence/retrieval lifecycle using temporary SQLite and local storage, including database-engine dispose/recreate; valid/missing SAM config regressions; readiness probe with artifact integrity and fallback checks; results UI TypeScript checks, 24 frontend tests, and production build; FastAPI import; live database connectivity and migration-head check; configured storage readiness probe; checkpoint manifest hashes; local storage round-trip and owner-scoped lifecycle tests.

**Failed:** none in the final test runs.

**Blocked:** live remote storage object round trip; browser-based frontend-to-real-model journey; a backend-process restart persistence check; external OOD evaluation; source-attributed held-out test-image evaluation. No separate remote test namespace or external evaluation set was verified.

**Not run:** migrations, database writes in the configured live database, uploads to configured live storage, signed-download retrieval from the live provider, backend restart/history against the live database, and destructive or cleanup operations against external infrastructure.

## Acceptance criteria status

- **PASS:** Canonical Python 3.12 CPU runtime; integrity-checked original checkpoints; actual integrated local inference on one unlabelled image; fail-closed OOD abstention; readiness matching lazy lifecycle; SAM missing-config behavior; severity shown as provisional mask coverage only; actual results page uses structured persisted API results; diagnostics are collapsed and repeated narrative is removed; backend/frontend test and build checks listed above.
- **PARTIAL:** Class/plant interpretation, segmentation semantics, uncertainty, and severity. Unit contracts and real checkpoint execution are verified, but no independently labeled held-out dataset establishes accuracy, calibration, or generalization. The lone end-to-end image is unlabelled and is not an evaluation result.
- **PARTIAL:** Authenticated API-to-real-inference-to-local-persistence journey, including completed-result and asset retrieval after recreating the SQLite engine, is verified with temporary local resources. Browser-based frontend coverage, an actual backend-process restart, live remote upload/readback in a dedicated test bucket, and source-attributed in-distribution/OOD image evaluation remain blocked.
- **NOT CERTIFIED:** Production readiness and agronomic diagnosis quality. Do not use the reported provisional scores as validated treatment guidance.

## 13. Remaining risks

- Readiness preflight hashes required checkpoint/identity files and caches successful or failed results by path, size, modification time, and expected digest. It does not load model weights, so transient memory/runtime failures during a later inference still surface on the analysis request rather than being predicted by `/api/ready`.
- Evaluate OOD detection with a separately sourced and held-out set, including supported field images and genuinely unsupported plants/diseases. Do not tune on the final evaluation set.
- Establish a dedicated storage test bucket/prefix and run a real upload/readback equality check before certifying remote storage.
- Run an authenticated browser journey against a dedicated test database/storage profile and verify the same completed result after a backend restart.
- Verify training-to-inference preprocessing and the exact embedding extraction used to fit calibration in the original training/calibration code.
- Build the source/license-aware image manifest and verify no training/test leakage before reporting model accuracy.
- Live database schema verification in this task confirmed the migration head and ownership column; a complete schema/index/constraint comparison was not performed.

## 14. Start and test commands

From the repository root, following the documented setup:

```powershell
Set-Location backend
..\.venv-ml312\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal:

```powershell
Set-Location frontend
npm run dev
```

Backend CPU-safe tests:

```powershell
.venv-ml312\Scripts\python.exe -m pytest -q
```

Frontend checks:

```powershell
Set-Location frontend
npm run typecheck
npm test
npm run build
```

Real-model contract tests require `PLANTGUARD_RUN_REAL_MODEL_TESTS=1`; setting that flag alone does not establish that the environment is suitable. The full local pipeline run above used original checkpoint variants without writing to configured remote infrastructure.
