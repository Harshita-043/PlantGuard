# PlantGuard AI Model Registry

## Overview
This document tracks all machine learning models used in the PlantGuard AI system, including their metadata, versions, performance metrics, and deployment status.

## Current Models

### PlantGuard EfficientNetV2-B0 Classifier
- **Model ID**: plantguard-efficientnetv2b0-v1
- **Name**: PlantGuard EfficientNetV2-B0
- **Version**: v1.0.0
- **Architecture**: EfficientNetV2-B0 with custom classification head
- **Task**: Multi-class plant disease classification (38 classes)
- **Framework**: TensorFlow/Keras
- **File Format**: Keras (.keras)
- **Storage Location**: `ml/models/classification/`

## Model Artifacts

### Primary Model Files
1. **plantguard_classifier.keras**
   - Final trained model after fine-tuning
   - Size: ~20-40 MB (typical for EfficientNetV2-B0)
   - Purpose: Production inference

2. **plantguard_classifier_best.keras**
   - Best checkpoint from training (based on validation accuracy)
   - Size: Similar to primary model
   - Purpose: Backup/rollback option

### Metadata Files
3. **model_metadata.json**
   ```json
   {
     "model_name": "PlantGuard EfficientNetV2-B0",
     "architecture": "EfficientNetV2B0",
     "task": "Plant disease classification",
     "dataset": "PlantVillage",
     "input_size": [224, 224],
     "num_classes": 38,
     "classes": [/* 38 class names */],
     "test_accuracy": 0.9593533277511597,
     "test_loss": 0.11987954378128052,
     "seed": 42,
     "framework": "TensorFlow/Keras",
     "pretrained": "ImageNet",
     "preprocessing": "EfficientNetV2 built-in preprocessing",
     "fine_tuning": true
   }
   ```

4. **class_names.json**
   - Ordered array of 38 class names matching model output indices
   - Used for converting model predictions to human-readable labels

5. **training_history.json**
   - Detailed metrics per epoch for both head training and fine-tuning phases
   - Includes accuracy, loss, validation accuracy, validation loss, learning rate

6. **confusion_matrix.png**
   - Visual representation of model performance per class
   - Shows true positives, false positives, false negatives per class

7. **classification_report.txt**
   - Precision, recall, f1-score, and support for each class
   - Macro and weighted averages

## Model Lineage

### Training Process
1. **Base Model**: EfficientNetV2-B0 pretrained on ImageNet
2. **Phase 1 - Head Training**: 
   - Frozen base layers
   - Trained custom top layers (global avg pooling, dropout, dense, dropout, output)
   - Learning rate: 0.001
   - Duration: 10 epochs
3. **Phase 2 - Fine Tuning**:
   - Unfroze some base model layers
   - Continued training with lower learning rate
   - Learning rate: 0.00001
   - Duration: 10 epochs

### Version History
- **v1.0.0**: Initial release (current)
  - Based on EfficientNetV2-B0 architecture
  - Trained on PlantVillage dataset
  - Test accuracy: 95.94%
  - Classes: 38 plant disease/health states

## Deployment Status
- **Status**: Not deployed for inference
- **Location**: Stored in `ml/models/classification/` directory
- **Format**: Keras SavedModel format (.keras files)
- **Missing**: Model serving infrastructure (TensorFlow Serving, TorchServe, or custom API wrapper)

## Model Card Details

### Intended Use
- **Primary Use Case**: Plant disease identification from leaf images
- **Target Users**: Farmers, gardeners, agricultural extension workers
- **Environment**: Mobile/web application with image upload capability
- **Geographic Scope**: Global (though training data may have geographic biases)

### Factors Affecting Performance
- **Image Quality**: Blurry, low-light, or obscured images reduce accuracy
- **Plant Species**: Only works on the 38 specific plant/disease combinations trained
- **Disease Stage**: Early or late-stage diseases may not match training images
- **Environmental Factors**: Unusual lighting, backgrounds, or leaf orientations
- **Image Resolution**: Model expects 224x224 input; other sizes require resizing

### Ethical Considerations
- **Bias**: May perform poorly on underrepresented diseases or regions
- **Accessibility**: Requires smartphone/camera and internet connectivity
- **Economic Impact**: Incorrect predictions could lead to improper treatment
- **Mitigation**: Should be used as decision support, not definitive diagnosis

### Caveats and Recommendations
- **Not a Substitute for Expertise**: Model predictions should be verified by agricultural experts when possible
- **Continuous Learning**: Model should be updated with new data from field usage
- **Uncertainty Quantification**: Consider adding confidence scores or uncertainty estimates
- **Human-in-the-Low**: For critical applications, include expert review step

## Model Maintenance

### Retraining Schedule
- **Frequency**: To be determined based on data drift and performance monitoring
- **Trigger**: Performance degradation below threshold (e.g., 90% accuracy)
- **Data Source**: Combination of original PlantVillage + new field data

### Versioning Strategy
- **Semantic Versioning**: MAJOR.MINOR.PATCH
  - MAJOR: Architecture changes or different base model
  - MINOR: Significant retraining with new data
  - PATCH: Minor improvements, same training data

### Storage and Backup
- **Primary**: Git LFS or dedicated model storage (not currently in git)
- **Backup**: Should be stored in multiple locations
- **Registry**: Consider using MLflow, Weights & Biases, or custom model registry

## Integration Requirements

### For Deployment
1. **Model Loading Service**: Code to load .keras model and perform inference
2. **Preprocessing Pipeline**: Image resizing, normalization matching training
3. **Postprocessing**: Convert model outputs to class names + confidence scores
4. **API Wrapper**: REST/gRPC endpoint for frontend communication
5. **Scaling**: Consider GPU acceleration for production inference

### Current Gaps
- No model serving code in repository
- No Dockerfile for model service
- No inference API endpoints in backend
- No model validation/testing scripts
- No performance monitoring hooks

## Related Documents
- [ARCHITECTURE.md](01_ARCHITECTURE.md) - System architecture
- [ML_GRAPH.md](02_ML_GRAPH.md) - Detailed ML pipeline
- [DATASETS.md](03_DATASETS.md) - Training dataset information
- [API_CONTRACTS.md](05_API_CONTRACTS.md) - Planned API endpoints