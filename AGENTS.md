# PlantGuard AI repository instructions

- This is an existing full-stack project. Preserve working features and inspect current code before replacing implementations.
- Preserve all model checkpoints. Never retrain, rewrite, overwrite, or delete them without a separate explicit request.
- Keep the configured model order: SAM 2.1 Hiera Base Plus candidate masks, DINOv2 ViT-S/14 leaf filtering, DINOv2 ViT-B/14 classification, SegFormer-B0 PlantSeg lesion segmentation, then reliability/severity/explainability/result assembly.
- A heuristic or placeholder must never be described as SAM inference or as a model prediction. Fail with a typed capability error when a required model cannot execute.
- Use `backend/requirements.txt` for the API runtime and `backend/requirements-ml.txt` for the optional inference runtime. Do not load checkpoints in ordinary CPU-safe tests.
- Keep model inference behind `backend/app/ml/service.py`; validate image, tensor, mask, class and mapping contracts at the boundary.
- Do not add frontend features until the inference result contract is stable. Do not expose environment values or secrets in docs/logs.
- Keep original checkpoints immutable. A variant may be selected only after manifest SHA-256 verification; optimized variants additionally require recorded validation and runtime compatibility. Remote image transfer requires the explicit remote profile, HTTPS credentials, and `PLANTGUARD_REMOTE_IMAGE_UPLOAD_AUTHORIZED=true`.
- Runtime diagnostics must not return secret values, absolute model paths, or remote endpoint URLs. Never treat integrated graphics as CUDA or claim GPU validation from CPU tests.
- Run focused tests only when requested. Report exact commands and outcomes; mark real-model checks BLOCKED when dependencies, hardware, or verified config are unavailable.
