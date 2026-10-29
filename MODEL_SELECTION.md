# Model Selection & Quantization Parity Analysis

This document records the empirical evaluation of FP32 versus quantized variants across all pipeline stages, establishing the model choices, precision, CPU latencies, sizes, and fallback policies according to strict parity rules.

---

## 1. Summary Selection Matrix

| Stage | Profile | Chosen File | Precision | Accuracy / IoU | Latency (CPU) | Size | Fallback | Status |
|---|---|---|---|---|---|---|---|---|
| **1. Leaf Instance Segmentation** | CPU / CUDA | `artifacts/sam2/sam2.1_hiera_base_plus.pt` | FP32 | Not validated on held-out mask set | ~2000-4000 ms (CPU) | 308.6 MB | MobileSAM (`mobile_sam.pt`, 38.8 MB) | Validated loading & weights |
| **1b. Fallback Segmentation** | CPU (low-resource) | `artifacts/mobilesam/mobile_sam.pt` | FP32 | Mask heuristic | ~250-400 ms (CPU) | 38.8 MB | None | Validated fallback |
| **2. Leaf Filter** | CPU Default | `artifacts/dino_leaf_filter/dino_leaf_filter.pt` (v1) | FP32 | 100% agreement on test sets | 81.18 ms | 84.2 MB | `dino_leaf_filter_v2.pt` / ONNX FP32 | Verified & configurable |
| **2b. Leaf Filter (Fast CPU)** | CPU Optimized | `artifacts/optimized/dino_leaf_filter/onnx_int8/dino_leaf_filter_dynamic_int8.onnx` | Dynamic INT8 | 1.0 acc (1250 images), 100% agreement on mixed | 22.80 ms | 23.8 MB | ONNX FP32 / PyTorch v1 | Verified |
| **3. Disease Classifier** | CPU / CUDA | `artifacts/optimized/dino_disease/onnx/dino_disease_fp32_224.onnx` | FP32 | 94.91% top-1 (1140 imgs), 100% agreement with PyTorch | 151.51 ms | 330.5 MB | PyTorch FP32 (`dino_disease_classifier.pt`, 195.10 ms) | Verified |
| **4. Lesion Segmentation** | CPU | `artifacts/optimized/segformer/onnx_int8/segformer_dynamic_int8.onnx` | Dynamic INT8 | IoU: 0.9744–0.9839 (>0.95), severity diff < 0.36 pt (<2.0 pt) | 109.45 ms | 7.5 MB | ONNX FP32 (14.3 MB, 123.05 ms) / PyTorch safetensors | Verified |

*Note: Any metric without held-out ground truth annotations is explicitly marked "Not validated on held-out set".*

---

## 2. Stage-by-Stage Evaluation Evidence

### A. Disease Classifier (DINOv2 ViT-B/14, 38 Classes)
- **Candidate Variants Tested:**
  1. PyTorch FP32 (`artifacts/dino_disease/dino_disease_classifier.pt`)
  2. ONNX FP32 (`artifacts/optimized/dino_disease/onnx/dino_disease_fp32_224.onnx`)
  3. ONNX Dynamic INT8 (`artifacts/optimized/dino_disease/onnx_int8/dino_disease_dynamic_int8.onnx`)
  4. ONNX Selective INT8 (`artifacts/optimized/dino_disease/onnx_selective_int8/dino_disease_mlp_int8.onnx`)

- **Reported Benchmark (`reports/device_validation/dino_disease/`):**
  - Dataset: `data/raw/plantvillage_hf/data.zip` (1140 images across all 38 classes, 30 per class).
  - FP32 ONNX Top-1 Accuracy: **94.91%**.
  - Dynamic INT8 ONNX Top-1 Accuracy: **6.93%** (Prediction agreement with FP32: **6.93%**).
  - Selective INT8 ONNX Top-1 Accuracy: **8.16%** (Prediction agreement with FP32: **8.25%**).

- **Fresh Session Verification on Real Images:**
  - **PyTorch FP32 vs ONNX FP32:**
    - Prediction Agreement: **100.0%**
    - Max Absolute Probability Drift: **0.0093** (< 1 percentage point)
    - Mean Absolute Error: **0.0007**
    - Median Latency on CPU: 195.10 ms (PyTorch) vs **151.51 ms (ONNX FP32)**
  - **ONNX Dynamic INT8:**
    - Prediction Agreement with FP32: **0.0%**
    - Max Absolute Probability Drift: **0.5968**
    - Predictions collapsed to `Apple___Black_rot` regardless of input with diffuse probabilities (~0.2–0.39).
  - **ONNX Selective INT8 (MLP INT8):**
    - Prediction Agreement with FP32: **25.0%**
    - Max Absolute Probability Drift: **0.5769**
  - **Root Cause Analysis:** Post-training naive dynamic quantization (`QInt8` / MatMul) on DINOv2 Base ViT causes accumulative distortion of attention embeddings across 12 self-attention and LayerNorm blocks (mean embedding error > 1.68, logits drift > 11.7), severely corrupting class boundaries.
  - **Decision:** In accordance with the decision rule (variant must be within 0.5% top-1 and >=99.5% agreement), **ONNX FP32 is selected**. Dynamic INT8 and Selective INT8 are **REJECTED** for production classification.

---

### B. Leaf Filter (DINOv2 ViT-S/14 Binary Classifier)
- **Candidate Variants Tested:**
  1. PyTorch v1 (`dino_leaf_filter.pt`)
  2. PyTorch v2 (`dino_leaf_filter_v2.pt`)
  3. ONNX FP32 (`dino_leaf_filter_fp32_224.onnx`)
  4. ONNX Dynamic INT8 (`dino_leaf_filter_dynamic_int8.onnx`)

- **Reported Benchmark (`reports/device_validation/dino_leaf_filter/int8_full_validation.json`):**
  - Tested on 1250 images (500 negative, 750 positive).
  - FP32 Accuracy: 1.0, INT8 Accuracy: 1.0, Prediction Agreement: 1.0.
  - Median CPU latency: 0.183s (FP32) vs 0.092s (INT8).

- **Fresh Session Verification on Mixed Set:**
  - Real Leaf Images: All models predicted `LEAF` with prob > 0.999.
  - Synthetic Non-Leaf (random noise, black, white): All models predicted `NON-LEAF` (probs 0.001 to 0.198).
  - Decision agreement between FP32 and INT8: **100%**.
  - Median CPU latency: PyTorch v1 = 81.18 ms, PyTorch v2 = 73.30 ms, ONNX FP32 = 47.57 ms, ONNX INT8 = 22.80 ms.
  - **Decision:** As specified by repository instructions, default to **PyTorch v1 (`dino_leaf_filter.pt`)** via `PLANTGUARD_LEAF_FILTER_VERSION="v1"`, while supporting v2 and ONNX INT8 via configuration.

---

### C. SegFormer Lesion Segmenter (SegFormer-B0 PlantSeg)
- **Candidate Variants Tested:**
  1. PyTorch Reference (`outputs/segformer_plantseg/best_model/model.safetensors`)
  2. ONNX FP32 (`artifacts/optimized/segformer/onnx/segformer_fp32_512.onnx`)
  3. ONNX Dynamic INT8 (`artifacts/optimized/segformer/onnx_int8/segformer_dynamic_int8.onnx`)

- **Fresh Session Verification:**
  - Evaluated on real diseased leaf images at 512x512:
    - Apple Scab: PyTorch lesion % = 10.17%, ONNX FP32 = 10.03%, ONNX INT8 = 9.82%. Mask IoU (INT8 vs FP32) = **0.9744**.
    - Test Leaf: PyTorch lesion % = 12.08%, ONNX FP32 = 11.93%, ONNX INT8 = 12.04%. Mask IoU (INT8 vs FP32) = **0.9839**.
  - Severity error between INT8 and FP32: **0.11% to 0.21%** (well within the <= 2.0% threshold).
  - Mean Mask IoU: **0.979** (well above the >= 0.95 threshold).
  - Median CPU Latency: PyTorch = 232.68 ms, ONNX FP32 = 123.05 ms, ONNX INT8 = **109.45 ms**.
  - File Size: INT8 is **7.5 MB** vs FP32 **14.3 MB** (48% reduction).
  - **Decision:** ONNX Dynamic INT8 meets all parity criteria (IoU >= 0.95, severity delta <= 2%) and is selected as the default CPU lesion segmentation model.
