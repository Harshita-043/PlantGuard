# Model Artifact Inventory

The repository contains the following classification artifacts under `ml/models/classification/`:

- `plantguard_classifier.keras`
- `plantguard_classifier_best.keras`
- `model_metadata.json`
- `class_names.json`
- training/report/visualization files

The metadata file describes an EfficientNetV2B0 classifier, a 224×224 input, 38 labels, and reports test metrics. These are metadata claims only; this application audit did not load the model, verify preprocessing, reproduce metrics, or establish compatibility with backend inference. The artifacts are not referenced by current application code and were not modified.

**Application integration status: NOT YET INTEGRATED.** Do not describe these files as a production model service.

## Phase 9 runtime status

- The SAM2/CLIP bundle has an isolated runtime manifest at `ml/models/leaf segmentation/PlantGuard/PlantGuard/requirements-runtime.txt`, targeting Python 3.12.10. It is separate from `backend/requirements.txt`.
- SAM2 configuration now resolves the existing `models/sam2/sam2.1_hiera_small.pt` and `configs/sam2.1_hiera_s.yaml` relative to the bundle. Missing generator settings use the documented `SAM2AutomaticMaskGenerator` API defaults except `points_per_side=32`, which was already configured by this project.
- A load-only smoke command exists at `app.smoke_test`. The repository Windows environment had only Python 3.14, no WSL, PyTorch, SAM2, or CUDA tooling; therefore model construction/checkpoint load have not been verified.
- CLIP uses the existing `ViT-B-32` code architecture and now has an explicit strict local safetensors load path. The bundled file's provenance and architecture compatibility remain unverified until it is loaded successfully. Registry pretrained weights are not used as a fallback.
- No EfficientNet checkpoint is selected or loaded. U-Net architecture remains unknown; severity and Grad-CAM remain missing. No weights were modified.
