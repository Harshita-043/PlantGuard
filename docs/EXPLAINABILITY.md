# Explainability behavior and limits

## Implemented visualization

The disease classifier is the repository's native DINOv2 ViT-B/14 transformer (`backend/app/ml/architectures/dinov2.py`) with a LayerNorm/linear 38-class head. It returns the final block's multi-head self-attention tensor. The adapter now computes a class-specific gradient-weighted CLS-to-patch map: for the selected logit it differentiates the logit with respect to the final attention tensor, multiplies gradients by attention, averages heads, keeps positive values, reshapes the 16x16 ViT-B/14 patch grid, and bilinearly resizes it to 224x224. `backend/app/ml/service.py` validates that shape and finiteness, then resizes the visualization to the exact selected crop dimensions for storage.

This is architecture-compatible transformer attribution visualization; it is not ordinary CNN Grad-CAM, a causal explanation, proof that highlighted pixels caused the classification, or a validated explanation method. Quality, faithfulness, stability, and human usefulness have **not** been evaluated on PlantVillage, PlantSeg, or deployment images. The result description makes this limitation explicit.

## Failure behavior

The output uses `ExplainabilityResult.status` (`available` or `unavailable`), a method identifier, and an optional heatmap asset. A shape/gradient/persistence failure is logged as an explainability-stage warning and does not discard the classification or segmentation result. If the adapter cannot provide the map, or no storage backend can persist the visualization for the caller, the typed status is unavailable. A storage-backed asset is required for status `available`.

## Evaluation required

The gradient path and end-to-end output shape must be smoke-tested with the actual classifier checkpoint in the ML environment. Explanation evaluation additionally needs perturbation/faithfulness and stability analysis, crop alignment review, and domain-expert assessment. None has been completed here. A successful shape contract test is not evidence of explanation quality.
