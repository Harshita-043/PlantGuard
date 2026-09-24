# Model Artifact Inventory

The repository contains the following classification artifacts under `ml/models/classification/`:

- `plantguard_classifier.keras`
- `plantguard_classifier_best.keras`
- `model_metadata.json`
- `class_names.json`
- training/report/visualization files

The metadata file describes an EfficientNetV2B0 classifier, a 224×224 input, 38 labels, and reports test metrics. These are metadata claims only; this application audit did not load the model, verify preprocessing, reproduce metrics, or establish compatibility with backend inference. The artifacts are not referenced by current application code and were not modified.

**Application integration status: NOT YET INTEGRATED.** Do not describe these files as a production model service.
