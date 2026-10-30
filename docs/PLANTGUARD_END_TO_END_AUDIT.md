# PlantGuard End-to-End Audit

**Audit status: Real local inference verified; not production-certified.** This audit preserves the existing model artifacts and database. No migrations or remote object writes were performed.

## 1. Executive summary

The authenticated image-analysis path, database persistence, configured storage readiness, and frontend build are present. A serious OOD fail-open path was found and fixed: missing or invalid calibration and unavailable classifier features can no longer be converted into a negative OOD decision. The classifier output is retained as an unverified candidate when the provisional OOD threshold is exceeded; the OOD flag remains visible, and the candidate is excluded from accepted plant-level diagnosis metrics.

The configured PostgreSQL database responded to a read-only query and is at the repository migration head. The configured Supabase bucket passed its read-only readiness probe. The manifest records the true Git LFS object SHA-256 values. The configured local model artifacts were initially LFS pointers; on 2026-10-30, the needed original objects were hydrated from the verified local LFS cache and their hashes rechecked. Runtime selection still rejects pointer text in unhydrated checkouts.

The `.venv-ml312` Python 3.12 environment includes the required runtime. After local hydration, real CPU inference tests passed with the original SAM 2.1, MobileSAM fallback, both DINOv2 stages, and SegFormer. Authenticated local API persistence was separately verified using temporary SQLite/storage resources. The known image exceeded the provisional OOD boundary for every resulting leaf, so disease labels were withheld. This image's class/source is not established, so this is not evidence that it is OOD or that the threshold works. No CUDA/GPU capability, browser-based frontend journey, or remote-storage upload/readback is claimed.

### 2026-10-30 runtime repair

- The canonical runtime is Python 3.12.7, PyTorch 2.6.0+cpu, SAM 2 1.0, and MobileSAM 1.0; CUDA is unavailable.
- Before hydration, reproducing the reported PyTorch 2.6 `weights_only` exception on `artifacts/sam2/sam2.1_hiera_base_plus.pt` (134-byte pointer) and `artifacts/mobilesam/mobile_sam.pt` (133-byte pointer) showed `Unsupported operand 118`. Those files began with the Git LFS pointer header `version ...`; they were not serialized model data. The exception therefore did not establish that the real model checkpoints were incompatible.
- The pointer OIDs match the manifest's original checkpoint hashes. Their trusted local LFS objects were safely loaded with `weights_only=True`: SAM 2.1 is a wrapper with a `model` state dictionary (323,606,802 bytes; SHA-256 `a2345aede8715ab1d5d31b4a509fb160c5a4af1970f199d9054ccfb746c004c5`); MobileSAM is a 439-entry tensor `OrderedDict` (40,728,226 bytes; SHA-256 `6dbb90523a35330fedd7f1d3dfc66f995213d81b29a5ca8108dbcdd4e37d6c2f`). The SAM 2 package uses `map_location="cpu", weights_only=True` and strict state loading. The pinned MobileSAM package called `torch.load(f)` without explicit arguments, relying on the PyTorch-version default.
- The MobileSAM adapter now explicitly deserializes with `weights_only=True` and `map_location="cpu"`, checks checkpoint keys and tensor shapes against `vit_t`, then loads strictly. It never uses `weights_only=False`. Variant and inventory code reject LFS pointer text even if a manifest hash is made to match that text.
- Real CPU inference on `IMAGE_APP.jpg` passed for SAM 2 (24 generated proposals; 14 adapter candidates with source-image-aligned masks) and MobileSAM (14 adapter candidates with aligned masks). A real full-service primary-SAM run completed in about 54 seconds; the MobileSAM fallback run completed in about 33 seconds. Both exercised DINOv2 filtering/classification, OOD, SegFormer, and severity. Primary path: 7 leaves, all 7 provisionally OOD, labels withheld, no stage failures. Fallback path: MobileSAM selected and reported distinctly, 1 leaf, OOD label withheld, no stage failures.
- Authenticated local API upload used the same real primary path and temporary verified model copies: HTTP 201/completed, 7 OOD rejections and 7 withheld labels, 43 saved assets, owner-visible history, and persisted result/assets readable after recreating the temporary SQLite engine.
- The required local artifacts were hydrated from their SHA-256-verified LFS objects using `git lfs checkout` without modifying checkpoint contents. The current configured model paths contain those original objects. The runtime's pointer detection remains in place for fresh or partially hydrated checkouts.
- Hydration also exposed the next LFS blockers: the selected DINOv2 v2 leaf-filter checkpoint, classifier checkpoint, OOD calibration, and SegFormer weights. These required original artifacts were likewise hydrated from the local cache; the unused DINOv2 v1 and optimized ONNX artifacts remain unhydrated.
- The attached `artifacts/dino_disease/classes.json` is the 38-label classifier mapping. It was not the cause of the variant-selection error; that occurs before classification, at leaf proposal. It is an input to the downstream classifier label mapping.

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

**Results UI and diagnostic semantics.** The actual persisted-scan results page now separates scan metadata, the primary diagnostic state, overview metrics, per-leaf cards, saved visual evidence, next steps, and expandable technical diagnostics. When the provisional OOD threshold is exceeded, the classifier's top class remains visible as an unverified model candidate beside the OOD flag; it is not counted as an accepted plant-level diagnosis. OOD performance and classifier confidence remain unvalidated. Severity categories are not shown as validated; mask coverage is shown only when segmentation counts, ratio, and severity pixel counts agree, and is labeled provisional (especially unvalidated for OOD inputs). Entropy, Mahalanobis distance/threshold, calibration state, segmentation counts, model versions, timings, and non-summary warnings are available on demand. Repeated backend prose was removed from the main results flow. The API already provided the required structured fields, so no duplicate API fields were introduced.

The reported `99.92% affected (high)` value is a ratio of SegFormer lesion pixels intersected with the selected leaf mask, divided by valid leaf-mask pixels. The counts and ratio are contract-checked before the interface shows this as **provisional lesion-mask coverage**; the categorical `high` severity is not presented because severity thresholds are not agronomically validated. This is a pixel measurement from a model mask, not a confirmed disease-severity assessment.

## 4. Files changed

- `backend/app/ml/ood.py`: validates NPZ and paired JSON calibration metadata, dimensions, class indices, finite values, covariance symmetry/positive-definiteness, threshold, and fails closed.
- `backend/app/ml/errors.py`: adds a typed OOD-calibration-unavailable error code.
- `backend/app/ml/service.py`: requires OOD results, retains class candidates when the provisional distance exceeds threshold, flags them for review, and excludes flagged leaves from accepted plant diagnosis summary metrics.
- `backend/app/ml/service.py`: returns partial classification results when downstream disease segmentation fails, with severity explicitly unavailable.
- `backend/app/ml/service.py`, `backend/app/ml/variants.py`, and `backend/app/core/config.py`: connect variant configuration to exact registered manifest entries and reject unregistered backend requests rather than silently falling back.
- `backend/app/ml/adapters/sam_adapter.py`, `backend/app/ml/adapters/mobile_sam_adapter.py`, `backend/app/ml/service.py`, and `backend/app/schemas/inference.py`: record candidate funnel counts and suppress masks with at least 95% containment overlap.
- `backend/app/ml/service.py`: copies inputs into writable contiguous RGB buffers to avoid the PyTorch/torchvision warning observed on real-image inference.
- `backend/app/services/plant_analysis_service.py`: rejects OOD results in the legacy response adapter because that contract cannot carry classifier output and OOD status together.
- `backend/app/ml/adapters/disease_classifier.py`: adds feature extraction separate from attention so explainability failure does not bypass required OOD scoring.
- `backend/app/core/config.py`, `.env.example`, and `README.md`: document an optional OOD calibration path override, its paired metadata requirement, and treat an empty optional path as unset.
- `backend/app/api/v1/analyze.py`: verifies successful object storage writes before persisting a scan and maps OOD calibration unavailability to a sanitized service error.
- `backend/app/api/readiness.py`: separates required model prerequisites from residency and reports primary SAM 2 and optional MobileSAM fallback independently.
- `backend/app/services/plant_analysis_service.py`: checks that required DINOv2/SegFormer stages and at least one candidate-generator variant are selectable and integrity-verified; validates the configured SAM package config.
- `backend/app/ml/variants.py`: shares cached SHA-256 verification results across readiness requests without loading checkpoint tensors.
- `backend/app/ml/variants.py` and `backend/app/ml/registry.py`: detect Git LFS pointer documents and report them as unavailable artifacts, including when a pointer-text hash is configured; artifact diagnostics use workspace-relative paths.
- `backend/app/ml/adapters/mobile_sam_adapter.py`: explicitly loads trusted MobileSAM tensor state with `weights_only=True` on CPU, validates keys and shapes against ViT-T, and performs strict state loading.
- `backend/app/api/admin.py`: reports selected/loaded model identities, artifact and initialization status, device, and supported operations through protected diagnostics without returning secrets or absolute paths.
- `frontend/client/pages/ScanResultsPage.tsx`: displays retained classifier candidates beside provisional OOD flags.
- `frontend/client/pages/ScanResultsPage.tsx`: visibly flags partial analysis outside the collapsed diagnostics section.
- `frontend/client/pages/ScanResultsPage.tsx` and `frontend/shared/api.ts`: expose stage candidate counts in technical diagnostics.
- `frontend/client/pages/ScanResultsPage.tsx`: restructures actual persisted results into a responsive dashboard, shows retained classifier candidates beside OOD flags without treating them as accepted diagnoses, and moves low-level diagnostics into expandable sections.
- `frontend/client/components/scan/LeafOverlay.tsx`: lists only visual assets present in the saved result, with consistent aspect-preserving image layout and explicit empty/load-failure states.
- `frontend/client/lib/scan-results.ts` and `scan-results.spec.ts`: centralize candidate/coverage/visualization presentation rules and test OOD flagging and mask consistency.
- `backend/app/tests/test_mobile_sam_adapter.py`, `backend/app/tests/test_real_model_inference.py`, `backend/app/tests/test_api.py`, `backend/app/tests/test_image_upload.py`, `backend/app/tests/test_inference_service.py`, `backend/app/tests/test_ood_mahalanobis.py`, `backend/app/tests/test_readiness.py`, `backend/app/tests/test_services.py`, `backend/app/tests/test_device_variants.py`, and `backend/app/tests/test_ml_foundations.py`: cover safe checkpoint loading, CPU initialization, invalid/missing artifacts, variant integrity, storage verification, OOD failure and candidate reporting, and valid/missing SAM config behavior. Real checkpoint inference tests require explicit opt-in.

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
- The runtime selected `original-pytorch-fp32` for the leaf filter and disease classifier and `original-transformers-fp32` for SegFormer in the recorded post-fix full-pipeline run. The configured leaf-filter preference has since changed to v1.
- The classifier architecture exposes a 768-dimensional CLS feature used by Mahalanobis scoring. The calibrated embedding's exact training/preprocessing provenance could not be independently reproduced because the calibration-fitting code is unavailable.
- Runtime inventory: SAM 2.1 automatic mask generation consumes raw RGB `uint8 (H,W,3)` and returns masks in source-image coordinates; MobileSAM uses an 8×8 positive-point grid only as fallback. The DINOv2 ViT-S/14 v2 filter resizes RGB crops to 224×224, ImageNet-normalizes, applies sigmoid to one logit, and accepts positive probability ≥0.5. The ViT-B/14 classifier uses the same RGB/224/ImageNet preprocessing and returns 38 softmax probabilities plus a 768-D CLS feature. OOD uses class-conditional Mahalanobis distance on that feature and a strict distance-over-threshold decision; its operating quality is unvalidated. SegFormer-B0 consumes RGB/512/ImageNet-normalized crops and returns a binary background/disease mask aligned to the crop.
- The service-level duplicate rule removes a lower-ranked mask when at least 95% of the smaller mask's area overlaps. The `generated` count is the raw proposal count from the selected segmentation adapter; `valid` counts candidates passing service contracts and the candidate cap.
- DINOv2 Attention Rollout is computed from CLS-to-patch attention across transformer blocks. It is not class-conditioned; the UI labels it as an attention visualization, not causal evidence or proof of the predicted class.
- All six required original inference artifacts (SAM 2.1, MobileSAM fallback, DINOv2 leaf filter, DINOv2 classifier, OOD calibration, and SegFormer weights) are present at their configured paths and match their manifest/LFS SHA-256 values. Their checkpoint contents were not changed.
- In `.venv-ml312`, real DINOv2 leaf-filter and disease-classifier loading/output-contract tests passed; the classifier emitted the expected 38-class distribution on a synthetic smoke-test input.
- SegFormer real-checkpoint output/mask-shape smoke passed. After artifact hydration, the full CPU pipeline executed SAM 2.1, DINOv2 ViT-S/14, DINOv2 ViT-B/14, and SegFormer on `IMAGE_APP.jpg`; the prior recorded run returned 24 raw proposals, 8 valid/deduplicated masks, and 7 classifier-eligible leaves with no primary-path fallback. The current opt-in real-model test also verifies the complete pipeline returns a completed/partial result with leaves.
- The test image has no verified label/source in this audit. Its seven provisional OOD threshold exceedances led to seven withheld class labels and an `unknown` summary; this observation requires investigation, not a claim about correctness.

### Leaf-filter preference update (2026-10-30)

- Based on the project owner's prior comparison that v1 has lower loss than v2, `v1` is now the configured DINOv2 ViT-S/14 leaf-filter variant; v2 remains registered as an explicit alternative. The historical evaluation report for v1 records 1.0 accuracy, precision, recall, and F1 on 1,250 samples, but its dataset provenance is not independently verified.
- The v1 checkpoint and its matching ONNX INT8 export were hydrated from the verified local Git LFS cache; their SHA-256 values match the LFS object IDs. Original model files remain unchanged.
- The manifest now registers v1 PyTorch, v2 PyTorch, and the v1 ONNX INT8 CPU variant. The DINOv2 leaf-filter adapter supports the ONNX logits contract and the service selects the optimized variant when ONNX Runtime is available, falling back only to original v1 PyTorch. The historical 1,250-image report records 100% accuracy and decision agreement, 0.00018 mean absolute probability difference, and median latency falling from 182.6 ms to 91.7 ms; dataset provenance remains unverified.
- In the Python 3.12.7 CPU runtime with ONNX Runtime 1.31.1, the selected INT8 filter and original v1 PyTorch filter agreed on the `IMAGE_APP.jpg` input (maximum probability difference 0.000029). The full inference pipeline completed with 8 leaves and reported `v1-onnx-int8`, original PyTorch DINOv2 ViT-B/14, and original Transformers SegFormer. A 15-call warmed local microbenchmark measured 22.9 ms median for INT8 versus 63.0 ms for v1 PyTorch on that same crop; this single-image timing is a smoke measurement, not a general performance guarantee.
- The DINOv2 disease INT8 export remains unused because its comparison reports top-1 disagreement and is not production-approved. The classifier's FP32 ONNX export failed direct parity against the current checkpoint and is not selected. SegFormer INT8 is selected on CPU based on high recorded mask agreement; the original Transformers checkpoint remains the fallback.

### Disease classifier and SegFormer ONNX selection (2026-10-30)

- The DINOv2 ViT-B/14 FP32 ONNX export and SegFormer INT8 export were hydrated from the verified local LFS cache. Both files match their manifest SHA-256 values.
- A DINOv2 classifier ONNX adapter was implemented for its declared FP32 input, 38 logits, and 768-dimensional embedding outputs. However, the current ONNX export did not reproduce its recorded parity report against the configured PyTorch checkpoint on `IMAGE_APP.jpg`: maximum logit difference was 0.4643, mean 0.1323, and maximum embedding difference 0.3906 (cosine similarity 0.9974). Although top-1 agreed on this one image, the export is marked rejected and is not selected; the original PyTorch classifier remains active for classification, OOD, and Attention Rollout.
- The SegFormer ONNX adapter validates the normalized 512×512 RGB input and two-class logits, resizes logits with the existing bilinear contract, and returns the same integer class mask. On CPU, `plantseg-b0` selects the validated INT8 ONNX variant when compatible ONNX Runtime is available; original Transformers weights remain the fallback.
- Historical SegFormer comparison reports 99.84% mean mask agreement (99.51% minimum) across 20 images and median latency 229.7 ms INT8 versus 237.2 ms FP32. A direct `IMAGE_APP.jpg` comparison against the current original Transformers checkpoint measured 99.72% mask agreement. That is a modest ~3.2% reported gain; dataset provenance is unverified.
- The latest complete CPU pipeline run selected `v1-onnx-int8` for leaf filtering, the original PyTorch DINOv2 ViT-B/14 classifier (the ONNX export is rejected), and `onnx-int8` for SegFormer. It completed with 8 leaves, OOD results, and disease masks.

## 9. OOD calibration and behavior

- `artifacts/dino_disease/ood.npz` was present and read without loading model checkpoints: 38 class-index entries, means shaped 38×768, inverse covariance shaped 768×768, finite values, and a positive threshold near 2474.644.
- Paired metadata identifies class-conditional Mahalanobis scoring, 768 features, class indices 0–37, and the in-distribution 99th percentile. The score is the quadratic distance from the predicted class mean using the stored inverse covariance; the decision uses strict `distance > threshold`.
- Calibration loads once into a validated cache. Missing, corrupt, incompatible, non-finite, or unscorable calibration/features fail closed. A threshold exceedance retains the classifier's raw class candidate with an OOD warning, while excluding it from accepted plant-level diagnosis metrics; the plant summary remains unknown when no unflagged classified leaves remain.
- The threshold remains explicitly **unvalidated for OOD detection**. The interface labels the result provisional; a threshold exceedance is not represented as a validated OOD diagnosis.
- Controlled tests cover scores below, at, and above the threshold; missing/corrupt calibration; invalid dimensions and NaNs; OOD scoring exceptions; retained class candidates and OOD flags. No genuine supported, unseen-disease, non-leaf, or unrelated natural images were evaluated.
- One local end-to-end image run exercised the true OOD scoring path; its unverified image provenance prevents using it as an OOD evaluation.

## 10. Test-image manifest and provenance

No new test images or labels were fabricated or added. The repository's calibration metadata references a PlantVillage validation source, but this audit did not establish access to a held-out test split or independently inspect image hashes/duplicates. No reproducible source/license-attributed image manifest was available, so the requested `supported_in_distribution`, `healthy_supported`, `unseen_disease_or_plant`, `non_leaf_objects`, and `corrupt_or_invalid` dataset suite remains **not created / not verified**. Synthetic images used by unit tests are limited to deterministic contract tests and are not accuracy evidence.

## 11. Commands and observed results

- `.venv-ml312\Scripts\python.exe -m pytest -q` — **247 passed, 8 skipped**, 8 third-party/dependency warnings. The skipped tests require explicit real-model opt-in.
- `$env:PLANTGUARD_RUN_REAL_MODEL_TESTS='1'; .venv-ml312\Scripts\python.exe -m pytest -q backend\app\tests\test_real_model_inference.py` — **2 passed** on CPU against hydrated configured artifacts; candidate generation covered SAM 2.1 and MobileSAM, and the full pipeline produced a valid result with leaves.
- `Set-Location backend; ..\.venv-ml312\Scripts\python.exe -m pytest -q app\tests\test_device_variants.py app\tests\test_readiness.py app\tests\test_inference_service.py app\tests\test_api.py app\tests\test_services.py` — **68 passed** before candidate-count coverage was added; the final full-suite result below includes the additional tests.
- `Set-Location frontend; npm.cmd run typecheck` — **passed**.
- `Set-Location frontend; npm.cmd test` — **5 files, 24 tests passed**, including tests for OOD rejection (including contradictory flag/score handling), candidate labeling, mask consistency, and visualization availability.
- `Set-Location frontend; npm.cmd run build` — **client and server production builds passed**.
- Real DINOv2 leaf-filter/classifier and SegFormer checkpoint contract tests were previously recorded as **3 passed**; the post-change full CPU inference run additionally exercised all four selected model stages.
- Artifact-backed CPU inference on `IMAGE_APP.jpg` using temporary SHA-verified LFS object copies — **completed** before hydration. SAM 2.1 primary path: 24 proposals, 8 valid/deduplicated, 7 leaf-filter accepted/classified, seven provisional OOD abstentions, all seven SegFormer masks produced. A separately forced MobileSAM fallback run completed with one OOD-abstained leaf; diagnostics identified MobileSAM rather than SAM 2.1. After hydrating configured originals, the opt-in real-model test reran SAM/MobileSAM candidate generation and the end-to-end pipeline successfully against the configured artifact paths.
- `Set-Location backend; ..\.venv-ml312\Scripts\python.exe -m alembic -c alembic.ini heads` — **`0006_plants (head)`**.
- Read-only configured dependency probe under `.venv-ml312` — database `SELECT 1` **passed**; live revision `0006_plants` and `analyses.user_id` checked; Supabase bucket readiness **passed**. No secrets or endpoint values were emitted.
- `/api/ready` previously returned **200 ready** before the full pointer-detection/hydration sequence; this audit does not claim a fresh readiness response after hydration.
- Manifest SHA-256 values match the hydrated original objects for all required model paths. `git lfs ls-files` reports the required artifact paths hydrated; unused variants remain pointers.
- `git diff --check` — **passed**.

## 12. Verification status

**Passed:** Latest Python 3.12 backend suite (247 passed, 8 skipped); opt-in real CPU model tests (2 passed) with configured hydrated artifacts; focused variant/readiness/inference/API regressions; MobileSAM safe-loader tests; complete primary/fallback pipelines on `IMAGE_APP.jpg`; authenticated API upload/inference/persistence/retrieval using temporary SQLite and local storage, including database-engine dispose/recreate; valid/missing SAM config regressions; results UI TypeScript checks, 24 frontend tests, and production build; FastAPI import; prior read-only database connectivity/migration-head and storage readiness probes; local storage round-trip and owner-scoped lifecycle tests.

**Failed:** none in the latest automated backend suite. The original PyTorch error was reproducible against pointer-text files, not against the actual checkpoint objects.

**Blocked:** CUDA/GPU inference; live remote storage object round trip; browser-based frontend-to-real-model journey; a backend-process restart persistence check; external OOD evaluation; source-attributed held-out test-image evaluation. No separate remote test namespace or external evaluation set was verified.

**Not run:** migrations, database writes in the configured live database, uploads to configured live storage, signed-download retrieval from the live provider, backend restart/history against the live database, and destructive or cleanup operations against external infrastructure.

## Acceptance criteria status

- **PASS:** Canonical Python 3.12 CPU runtime; safe loading of integrity-verified original checkpoints hydrated from local Git LFS; actual integrated CPU inference on one unlabelled image; fail-closed OOD abstention; SAM missing-config behavior; severity shown as provisional mask coverage only; actual results page uses structured persisted API results; diagnostics are collapsed and repeated narrative is removed; backend/frontend test and build checks listed above.
- **PARTIAL:** Class/plant interpretation, segmentation semantics, uncertainty, and severity. Unit contracts and real checkpoint execution are verified, but no independently labeled held-out dataset establishes accuracy, calibration, or generalization. The lone end-to-end image is unlabelled and is not an evaluation result.
- **PARTIAL:** Authenticated API-to-real-inference-to-local-persistence journey, including completed-result and asset retrieval after recreating the SQLite engine, is verified with temporary local resources. Browser-based frontend coverage, an actual backend-process restart, live remote upload/readback in a dedicated test bucket, and source-attributed in-distribution/OOD image evaluation remain blocked.
- **PASS (this checkout):** Required inference artifacts are hydrated and checksum-verified; real CPU tests pass. A fresh clone with smudging disabled or missing LFS objects will still correctly fail closed until those objects are hydrated.
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

Real-model contract tests require `PLANTGUARD_RUN_REAL_MODEL_TESTS=1`; setting that flag alone does not establish that the environment is suitable. The required local checkpoint objects are hydrated in this checkout and hash-verified. The recorded full-pipeline runs did not write to configured remote infrastructure.
