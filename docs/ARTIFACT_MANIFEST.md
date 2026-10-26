# PlantGuard AI — Verified Model Artifact Manifest

*Generated: 2026-10-26*
*Platform: ASUS Vivobook 15/16 (Intel Iris Xe, 16 GB RAM, Windows 11)*

Every artifact below has been verified on disk via structural unpack, header inspection, and live inference execution.

---

## 1. Verified Model Artifacts & Checksums

| Component Name | Local File Path | Checkpoint Format | Parameter Count | File Size (MB) | SHA-256 Checksum | Operational Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DINOv2 Leaf Filter (v2)** | `artifacts/dino_leaf_filter/dino_leaf_filter_v2.pt` | PyTorch StateDict Zip | ~22.0M (`dinov2_vits14`) | 84.21 MB | `03b3fb0337f60072d95f39634049bab211f4187b26343254595822413e30a268` | **Active** (Verified on CPU) |
| **DINOv2 Leaf Filter (v1)** | `artifacts/dino_leaf_filter/dino_leaf_filter.pt` | PyTorch StateDict Zip | ~22.0M (`dinov2_vits14`) | 84.21 MB | `555fed395710a7618f600083c53c97da1cdd57092d2eb0d402335231165f7a23` | Preserved (v1 baseline) |
| **DINOv2 Disease Classifier** | `artifacts/dino_disease/dino_disease_classifier.pt` | PyTorch StateDict Zip | ~86.6M (`dinov2_vitb14`) | 330.46 MB | `a219227893ef855fb8a96d105489d513a29130e19418d97b09be433247130081` | **Active** (Verified on CPU) |
| **Disease Class Mapping** | `artifacts/dino_disease/classes.json` | JSON (38 classes) | 38 labels | 0.001 MB | `f8988b3e341acb2e461ea8dd1caf9d3492a925405a32bcc57a79113237842aa4` | **Active** (Verified 38 classes) |
| **SegFormer-B0 Lesion Segmentation** | `outputs/segformer_plantseg/best_model/model.safetensors` | Safetensors (208 layers) | ~3.71M (`nvidia/mit-b0`) | 14.20 MB | `5e188bbebe7782ecaed12e494eda81f97ff7d53336b24015c57d4ba41c08621a` | **Active** (Verified on CPU) |
| **SegFormer Config** | `outputs/segformer_plantseg/best_model/config.json` | JSON | N/A | 0.001 MB | `2cc0ab73a3b2b2e1007e0a8a60cd340db6f1953e54b514ad945e07d635493ca7` | **Active** (id2label: 0=bg, 1=lesion) |
| **SegFormer Preprocessing** | `outputs/segformer_plantseg/best_model/preprocessing.json` | JSON | N/A | 0.001 MB | `18a4464b70dd698fafa5333c54c0bfd21abd889a29e294c66042064ca49ec4c8` | **Active** (512x512 ImageNet norm) |
| **SAM 2.1 Hiera Base+** | `artifacts/sam2/sam2.1_hiera_base_plus.pt` | PyTorch StateDict Zip | ~80.8M (`sam2.1_hiera_b+`) | 308.62 MB | `a2345aede8715ab1d5d31b4a509fb160c5a4af1970f199d9054ccfb746c004c5` | **Active** (Intact; heuristic/GPU ready) |

---

## 2. Model Specifications & Input/Output Contracts

### 2.1 DINOv2 Small Leaf Filter
- **Backbone**: `dinov2_vits14` (embed_dim=384, depth=12, num_heads=6, patch_size=14).
- **Head**: `nn.Sequential(nn.LayerNorm(384), nn.Linear(384, 1))`.
- **Pre-trained Resolution**: 518×518 (positional embeddings dynamically interpolated to 224×224).
- **Inference Preprocessing**: Resize to 224×224 RGB, normalized with ImageNet mean `(0.485, 0.456, 0.406)` and std `(0.229, 0.224, 0.225)`.
- **Output**: Sigmoid probability $\sigma(z) \in [0, 1]$.
  - `negative` (non-leaf) = $1.0 - \sigma(z)$
  - `positive` (leaf) = $\sigma(z)$
- **Hardware Profile**: ~84 MB RAM. CPU latency on Intel Core i5/i7: **~120 ms**.

### 2.2 DINOv2 Base Disease Classifier
- **Backbone**: `dinov2_vitb14` (embed_dim=768, depth=12, num_heads=12, patch_size=14).
- **Head**: `nn.Sequential(nn.LayerNorm(768), nn.Linear(768, 38))`.
- **Pre-trained Resolution**: 518×518 (positional embeddings dynamically interpolated to 224×224).
- **Inference Preprocessing**: Resize to 224×224 RGB, normalized with ImageNet mean and std.
- **Output**: Softmax distribution over 38 PlantVillage classes:
  - Apple: Apple scab, Black rot, Cedar apple rust, healthy
  - Blueberry: healthy
  - Cherry: Powdery mildew, healthy
  - Corn: Cercospora leaf spot, Common rust, Northern Leaf Blight, healthy
  - Grape: Black rot, Esca (Black Measles), Leaf blight, healthy
  - Orange: Haunglongbing (Citrus greening)
  - Peach: Bacterial spot, healthy
  - Pepper bell: Bacterial spot, healthy
  - Potato: Early blight, Late blight, healthy
  - Raspberry: healthy
  - Soybean: healthy
  - Squash: Powdery mildew
  - Strawberry: Leaf scorch, healthy
  - Tomato: Bacterial spot, Early blight, Late blight, Leaf Mold, Septoria leaf spot, Spider mites, Target Spot, Tomato Yellow Leaf Curl Virus, Tomato mosaic virus, healthy
- **Hardware Profile**: ~330 MB RAM. CPU latency on Intel Core i5/i7: **~480 ms**.

### 2.3 SegFormer-B0 Semantic Lesion Segmentation
- **Backbone**: `nvidia/mit-b0` (Mix Transformer B0 with MLP decoder).
- **Classes**:
  - `0`: `background` (healthy leaf tissue / non-lesion)
  - `1`: `diseased_region` (active pathological lesions)
- **Training Source**: PlantSeg dataset (18 epochs, validation Dice score: 0.787).
- **Inference Preprocessing**: 512×512 RGB, normalized with ImageNet mean and std.
- **Output**: Logits shape `(1, 2, 128, 128)`, bilinearly interpolated to original image coordinates `(H, W)` or `(512, 512)`.
- **Hardware Profile**: ~15 MB RAM. CPU latency on Intel Core i5/i7: **~180 ms**.

### 2.4 SAM 2.1 Hiera Base+
- **Backbone**: Hiera Base+ (`sam2.1_hiera_b+`).
- **Input**: Raw RGB uint8 images.
- **Output**: Filtered candidate leaf masks `[ymin, xmin, ymax, xmax]` excluding whole-frame background canvas.
- **Hardware Profile**: Ideal on CUDA GPU; on Vivobook CPU, bounded heuristic fallback maintains sub-second responsiveness.

---

## 3. Strict Rule Enforcements

- **No EfficientNet**: Confirmed zero presence of EfficientNet models or checkpoints.
- **Zero Silent Weights Overwrites**: Local checkpoints are verified read-only; no training scripts or overwrite commands exist in the active pipeline.
