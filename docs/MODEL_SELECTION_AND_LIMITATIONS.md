# PlantGuard AI — Model Selection and Limitations

This document provides the architectural evaluation, technical rationale, checkpoint specifications, runtime requirements, evaluation evidence, and known limitations for every model in the PlantGuard AI computer vision pipeline.

---

## Pipeline Overview

The PlantGuard AI disease diagnostic pipeline enforces a strict, hierarchical, sequential execution flow:

```
Input Image (RGB)
      │
      ▼
[Stage 1] SAM 2.1 Hiera Base Plus (Candidate Leaf Mask Generation)
          └── Fallback: MobileSAM (ViT-T)
      │
      ▼
[Stage 2] DINOv2 ViT-S/14 (Leaf Candidate Filtering: Positive / Negative)
      │
      ▼
[Stage 3] DINOv2 ViT-B/14 (Disease Classification: 38 PlantVillage Classes + 768-D Embedding)
      │
      ▼
[Stage 4] OOD Reliability Scoring (Class-Conditional Mahalanobis Distance vs In-Distribution Threshold)
      │
      ▼
[Stage 5] SegFormer-B0 PlantSeg (Lesion Semantic Segmentation)
      │
      ▼
[Stage 6] Geometric Mask-Based Severity Estimation & DINOv2 Attention Rollout Explainability
      │
      ▼
Result Assembly & Fail-Closed Validation
```

---

## 1. Stage 1: Leaf Proposal & Segmentation

### A. Primary: SAM 2.1 Hiera Base Plus
- **Model Key:** `sam2_instance_segmentation`
- **Architecture:** Meta SAM 2.1 Hiera Base Plus (`sam2.1_hiera_b+`)
- **Checkpoint:** `artifacts/sam2/sam2.1_hiera_base_plus.pt` (323,606,802 bytes, SHA-256: `a2345aede8715ab1d5d31b4a509fb160c5a4af1970f199d9054ccfb746c004c5`)
- **Configuration:** `configs/sam2.1/sam2.1_hiera_b+.yaml`
- **Responsibility:** Automatically segment individual plant leaf instances across the uploaded image without requiring bounding box prompts.
- **Why Suitable:** SAM 2.1 demonstrates superior boundary adherence, hierarchical feature representation (Hiera backbone), and robust zero-shot instance segmentation on complex foliage compared to generic box detectors.
- **Alternatives Considered:**
  - *YOLOv8-Seg:* Faster, but struggles with unseen leaf shapes, overlapping leaves, and complex backgrounds.
  - *Mask R-CNN:* Heavily biased toward specific trained classes and requires rigid bounding box proposals.
- **Evaluation Evidence:** Tested on `IMAGE_APP.jpg`; generated 24 raw proposals pruned down to 8 non-overlapping valid leaf candidate masks.
- **Runtime Requirements:**
  - CPU: Supported with memory-bounded chunking (~30–50s per image).
  - GPU: Recommended (CUDA with float16/bfloat16) for real-time ~300ms inference.
- **Known Limitations:**
  - High CPU memory and compute overhead when generating large point grids.
  - Can segment non-leaf objects (stems, pots, background cloth) which must be filtered downstream.

### B. Fallback: MobileSAM
- **Model Key:** `mobile_sam_instance_segmentation`
- **Architecture:** Lightweight Vision Transformer (ViT-T encoder + lightweight mask decoder)
- **Checkpoint:** `artifacts/mobilesam/mobile_sam.pt` (40,728,226 bytes, SHA-256: `6dbb90523a35330fedd7f1d3dfc66f995213d81b29a5ca8108dbcdd4e37d6c2f`)
- **Responsibility:** Standby candidate generator if SAM 2.1 is uninstalled or lacks native acceleration.
- **Why Suitable:** Extremely compact (~40 MB) and fast on CPU using an 8x8 point grid.
- **Known Limitations:** Lower boundary fidelity on complex leaves compared to SAM 2.1; occasionally produces fragmented masks.

---

## 2. Stage 2: Leaf Candidate Filtering

- **Model Key:** `dinov2_vits14`
- **Architecture:** DINOv2 ViT-S/14 (small Vision Transformer, 384 embedding dimension, patch size 14) + Binary Classification Head
- **Checkpoint Variants:**
  - Preferred INT8 ONNX: `artifacts/optimized/dino_leaf_filter/onnx_int8/dino_leaf_filter_dynamic_int8.onnx` (24,951,130 bytes, SHA-256: `60814f923bca327916ef4242699298e16db73eb5547dd5698b6aa55490bf9961`)
  - Original PyTorch FP32: `artifacts/dino_leaf_filter/dino_leaf_filter.pt` (v1, 88,300,314 bytes, SHA-256: `fa2207b53a067c26aa3346e9dfbc7fbf86d38e21a4f3cefd3980c98f986641ae`)
  - Alternative v2 PyTorch: `artifacts/dino_leaf_filter/dino_leaf_filter_v2.pt` (v2, 88,300,869 bytes, SHA-256: `8c3ec0bc4c730ad3d1421e42a9b311fc61217ec56c71f30141b71216dd54eb0c`)
- **Responsibility:** Distinguish genuine leaf masks from background artifacts, stems, hands, soil, or background geometry.
- **Contract:** Input (1, 3, 224, 224) RGB normalized by ImageNet mean/std; Output (1, 2) logits/probabilities for `[0: negative, 1: positive]`. Positive threshold: $\ge 0.50$.
- **Why Suitable:** DINOv2 foundation features possess high semantic visual representation for object classification; the small (ViT-S) variant executes in under 25ms on CPU with INT8 quantization.
- **Evaluation Evidence:** 100% agreement between INT8 ONNX and FP32 PyTorch on test crops (max probability delta: $0.000029$). Historical 1,250-sample validation recorded 1.0 precision, recall, and F1.
- **Known Limitations:** Trained on cropped leaves; extreme closeups of leaf textures or leaves with severe necrosis may rarely receive lower confidence.

---

## 3. Stage 3: Disease Classification

- **Model Key:** `dinov2_vitb14`
- **Architecture:** DINOv2 ViT-B/14 (base Vision Transformer, 768 embedding dimension, 12 attention heads, patch size 14) + 38-Class Classification Head
- **Checkpoint:** `artifacts/dino_disease/dino_disease_classifier.pt` (344,016,841 bytes, SHA-256: `446ee9cf1da3d6118bfa934372a912bb0fb1a7efec1781fe563ef31d0442e3f6`)
- **Mapping:** `artifacts/dino_disease/classes.json` (38 PlantVillage classes across Apple, Blueberry, Cherry, Corn, Grape, Orange, Peach, Pepper, Potato, Raspberry, Soybean, Squash, Strawberry, Tomato)
- **Responsibility:** Predict crop type, disease identity, and extract the 768-dimensional CLS feature vector for downstream OOD scoring.
- **Why Suitable:** ViT-B/14 provides rich visual semantics that capture both subtle leaf discolorations (rusts, blights) and global leaf morphology.
- **Rejected Variants:**
  - *DINOv2 ViT-B FP32 ONNX Export:* Rejected due to parity divergence against the PyTorch checkpoint on embedding outputs (max logit diff 0.46, max embedding diff 0.39). PyTorch FP32 checkpoint is strictly enforced.
- **Evaluation Evidence:** Verified 38-class distribution, finite probabilities summing to 1.0, and exact CLS token feature extraction across multiple test runs.
- **Known Limitations:**
  - Bounding box crops pass rectangular image patches to the classifier; background pixels outside the mask are not masked out to avoid introducing synthetic edge artifacts.

---

## 4. Stage 4: Out-of-Distribution (OOD) Scoring

- **Artifacts:**
  - Calibration matrix: `artifacts/dino_disease/ood.npz` (2,177,452 bytes, SHA-256: `a940f5d96ca44fbf8d135beea9e801cf3d8650df6866ec532ae1046168536f61`)
  - Calibration metadata: `artifacts/dino_disease/ood.json` (1,108 bytes, SHA-256: `89f5bc335f6f45ff5804efbb2fa9856f6ba50aa0ce6294d35eb7b372fbf6ec25`)
- **Method:** Class-Conditional Mahalanobis Distance using class-specific means $\mu_c$ (38 x 768) and inverse covariance $\Sigma^{-1}$ (768 x 768):
  $$D_M(x, c) = (x - \mu_c)^T \Sigma^{-1} (x - \mu_c)$$
- **Decision Boundary:** In-distribution 99th percentile threshold ($\approx 2474.644$). If $D_M > \text{threshold}$, the leaf is flagged as OOD.
- **Fail-Closed Behavior:** When a leaf exceeds the threshold, the predicted disease label is withheld from the accepted plant-level diagnosis summary metrics. The plant health status reports `UNKNOWN` if all detected leaves are flagged as OOD.
- **Evaluation Evidence:** Validated covariance positive-definiteness, dimensional alignment, and fail-closed behavior on `IMAGE_APP.jpg` (score 11,306 > 2,474.64, correctly triggering OOD abstention).
- **Known Limitations:**
  - Calibrated strictly on the in-distribution validation split of the training set. Real-world field images with natural lighting variations can trigger false rejections. A multi-source field evaluation dataset is required to establish calibrated open-set boundaries.

---

## 5. Stage 5: Lesion Semantic Segmentation

- **Model Key:** `segformer_b0_plantseg`
- **Architecture:** SegFormer-B0 (nvidia/mit-b0 hierarchical transformer backbone + lightweight MLP decoder)
- **Checkpoint Variants:**
  - Preferred INT8 ONNX: `artifacts/optimized/segformer/onnx_int8/segformer_dynamic_int8.onnx` (7,907,030 bytes, SHA-256: `0dc2323e198642a8b945cae7c51480c598000be05c040d6c48325a7a92265f24`)
  - Original Transformers: `outputs/segformer_plantseg/best_model/model.safetensors` (14,884,776 bytes, SHA-256: `be1cf5b4260d2d326f59ee9fc928f64560ea511c59c5d011f05cefcab2a2c5a1`)
- **Configuration:** `outputs/segformer_plantseg/best_model/config.json` & `preprocessing.json`
- **Responsibility:** Pixel-level binary segmentation distinguishing diseased lesions (`class 1`) from healthy leaf tissue (`class 0`).
- **Contract:** Input (1, 3, 512, 512) normalized; bilinear upsampling of logits to match the original leaf crop resolution.
- **Evaluation Evidence:** Direct comparison between INT8 ONNX and original Transformers checkpoint measured 99.72% mask agreement on test crops.
- **Known Limitations:**
  - SegFormer outputs binary lesion maps; it does not assign disease names to individual lesions (classification is handled by Stage 3).

---

## 6. Stage 6: Severity Estimation & Explainability

### A. Severity Estimation
- **Method:** Geometric pixel intersection:
  $$\text{Severity Ratio} = \frac{|\text{Lesion Mask} \cap \text{Valid Leaf Mask}|}{|\text{Valid Leaf Mask}|}$$
- **Responsibility:** Measure exact percentage of leaf tissue affected by pathological lesions.
- **Why Suitable:** Grounded strictly in validated segmentation masks, preventing hallucinatory severity claims.
- **Known Limitations:** Pixel ratio is an objective computer vision metric; it is not agronomically calibrated to yield impact or harvest loss.

### B. Architecture-Appropriate Explainability
- **Method:** DINOv2 Attention Rollout across ViT transformer blocks (CLS token attention to spatial patch tokens).
- **Why Suitable:** Standard CNN Grad-CAM is architecturally invalid for Vision Transformers lacking spatial convolutions. Attention rollout accurately reveals which visual tokens guided the transformer encoder.
- **Known Limitations:** Attention rollout reflects visual feature correlation, not causal counterfactual proof.

---

## 7. Model Selection Verdict

| Model / Subsystem | Current Evidence Status | Selection Decision | Next Verification Gate |
|---|---|---|---|
| **SAM 2.1 Hiera Base+** | Verified on CPU & GPU architectures | **KEEP / PRODUCTION PRIMARY** | Benchmark sub-second latency on RTX GPU host |
| **MobileSAM** | Verified safe CPU fallback | **KEEP / STANDBY FALLBACK** | Maintain for low-resource environments |
| **DINOv2 ViT-S/14 v1** | Verified 100% agreement INT8 / FP32 | **KEEP / PREFERRED FILTER** | Test on non-foliage edge-case images |
| **DINOv2 ViT-B/14** | Verified FP32 PyTorch checkpoint | **KEEP / PREFERRED CLASSIFIER** | Re-evaluate ONNX export once parity is solved |
| **OOD Mahalanobis** | Verified fail-closed implementation | **KEEP / PROVISIONAL THRESHOLD** | Calibrate on multi-crop field evaluation set |
| **SegFormer-B0 PlantSeg** | Verified 99.7% agreement INT8 / FP32 | **KEEP / PREFERRED SEGMENTER** | Multi-class lesion segmentation in future work |

