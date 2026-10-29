# Project status

- [x] **Step 0**: Inventory – done
- [x] **Step 1**: Fix the environment (venv recreation, install deps) – completed (imports verified)
- [x] **Step 2**: Re‑verify inventory (load ONNX models, inspect quantisation) – completed
- [x] **Step 3**: Decide leaf filter version (v1 vs v2) – completed (v1 default configured in registry & config)
- [x] **Step 4**: Parity & quality comparison (FP32 vs INT8) – completed; evaluated DINOv2 disease (ONNX FP32 chosen, INT8 rejected due to 0% agreement), leaf filter (v1 default, INT8 parity verified), and SegFormer (INT8 chosen with IoU > 0.97 and <0.36 pt severity diff). Recorded in MODEL_SELECTION.md.
- [x] **Step 5**: Implement CAM (attention rollout) – completed; implemented AttentionRolloutExplainer in app/ml/cam.py (1 CLS, 0 register tokens, 16x16 grid), overlay & original mapping verified on real image, outputs saved to outputs/explainability/.
- [ ] **Step 6**: Build full pipeline (segmentation fallback, startup checks, backend routes) – pending
- [ ] **Step 7**: DB & Supabase integration – pending
- [ ] **Step 8**: Frontend integration – pending
- [x] **Step 9**: Tests, Docker, CI – completed (regression test passed)
- [x] **Step 10**: Model distribution script – completed
- [x] **Step 11**: Run guide (RUN_GUIDE.md) – completed
- [x] **Step 12**: Final report (FINAL_REPORT.md) – completed

- [x] **Pre‑check baseline tests** – PASS
