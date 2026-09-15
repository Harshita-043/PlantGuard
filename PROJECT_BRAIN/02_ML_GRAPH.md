# PlantGuard AI Machine Learning Graph

## Overview
The ML component of PlantGuard AI uses a TensorFlow/Keras EfficientNetV2-B0 model for plant disease classification. The model was trained on the PlantVillage dataset to classify 38 different plant disease states across multiple crop types.

## Model Architecture

### Base Model
- **Architecture**: EfficientNetV2-B0
- **Input Shape**: (224, 224, 3) RGB images
- **Pretrained Weights**: ImageNet
- **Feature Extraction**: Transfer learning approach

### Custom Layers
1. **Base Model**: EfficientNetV2-B0 (include_top=False, weights='imagenet')
2. **Global Average Pooling**: Reduces spatial dimensions
3. **Dropout**: 0.2 rate for regularization
4. **Dense Layer**: 128 units with ReLU activation
5. **Dropout**: 0.2 rate for regularization
6. **Output Layer**: 38 units with softmax activation (one per class)

## Training Process

### Dataset
- **Source**: PlantVillage dataset
- **Classes**: 38 plant disease/health combinations
- **Split**: 
  - Training: ~70%
  - Validation: ~20% 
  - Test: ~10%
- **Preprocessing**: 
  - Resize to 224x224
  - EfficientNetV2 built-in preprocessing (rescaling)
  - Data augmentation (likely applied during training)

### Training Phases
1. **Head Training**: Train only the custom top layers while freezing base model
   - Initial learning rate: 0.001
   - Duration: 10 epochs
   - Results: Good convergence, validation accuracy ~94.3%

2. **Fine Tuning**: Unfreeze some base model layers and train with lower learning rate
   - Learning rate: 0.00001 (1/100th of initial)
   - Duration: 10 epochs
   - Results: Improved validation accuracy ~96.0%

## Model Performance

### Final Metrics (from model_metadata.json)
- **Test Accuracy**: 95.94%
- **Test Loss**: 0.1199
- **Framework**: TensorFlow/Keras
- **Seed**: 42 (for reproducibility)

### Training History Insights
From training_history.json:
- **Head Training**: 
  - Training accuracy improved from 79.5% to 95.2%
  - Validation accuracy improved from 41.9% to 94.3%
  - Some overfitting observed in later epochs (validation accuracy plateaued)

- **Fine Tuning**:
  - Training accuracy improved from 95.4% to 97.2%
  - Validation accuracy improved from 94.4% to 96.0%
  - Better generalization with lower learning rate

## Model Classes (38 total)
The model classifies the following plant disease states:
- Apple: Apple scab, Black rot, Cedar apple rust, Healthy
- Blueberry: Healthy
- Cherry: Powdery mildew, Healthy
- Corn: Cercospora leaf spot/Gray leaf spot, Common rust, Northern Leaf Blight, Healthy
- Grape: Black rot, Esca (Black Measles), Leaf blight, Healthy
- Orange: Huanglongbing (Citrus greening)
- Pepper: Bacterial spot, Healthy
- Potato: Early blight, Late blight, Healthy
- Raspberry: Healthy
- Soybean: Healthy
- Squash: Powdery mildew
- Strawberry: Leaf scorch, Healthy
- Tomato: Bacterial spot, Early blight, Late blight, Leaf Mold, Septoria leaf spot, Spider mites, Target spot, Tomato Yellow Leaf Curl Virus, Tomato mosaic virus, Healthy

## Model Artifacts
Located in `ml/models/classification/`:
- `plantguard_classifier.keras` - Final trained model
- `plantguard_classifier_best.keras` - Best checkpoint during training
- `model_metadata.json` - Model metadata and metrics
- `class_names.json` - Ordered list of class names
- `training_history.json` - Detailed training metrics per epoch
- `confusion_matrix.png` - Visualization of model performance
- `classification_report.txt` - Precision, recall, F1-score per class

## Preprocessing Pipeline
1. **Input**: Raw image (any format, any size)
2. **Resize**: To 224x224 pixels (maintaining aspect ratio likely with padding/cropping)
3. **Color Space**: RGB (3 channels)
4. **Normalization**: EfficientNetV2 built-in preprocessing (specific to ImageNet pretraining)
5. **Output**: Normalized tensor ready for model input

## Current Limitations
1. **No Serving Infrastructure**: Model stored as Keras files, not deployed for inference
2. **Missing API Endpoint**: No backend route to accept images and return predictions
3. **No Input Validation**: No verification of image format/size before processing
4. **No Batch Processing**: Designed for single-image inference
5. **No Confidence Thresholding**: Returns raw probabilities without uncertainty quantification
6. **No Model Monitoring**: No drift detection or performance tracking in production

## Dependencies
- TensorFlow (version unspecified, but compatible with Keras .keras format)
- NumPy (for array operations)
- PIL/Pillow (likely used for image loading/preprocessing in application code)

## Integration Points Needed
1. **Backend API Endpoint**: `/api/scan` or similar to accept plant images
2. **Image Preprocessing Service**: To prepare images for model input
3. **Model Loading Service**: To load Keras model and perform inference
4. **Result Formatting**: To convert model outputs to user-friendly responses
5. **Error Handling**: For invalid images, model failures, etc.

## Future Improvements
1. **Model Optimization**: Convert to TensorFlow Lite or TensorFlow.js for edge deployment
2. **Ensemble Methods**: Combine with other architectures for improved robustness
3. **Continuous Learning**: Pipeline for retraining with new data
4. **Explainability**: Grad-CAM or similar to show which image regions influenced decisions
5. **Uncertainty Estimation**: Bayesian approaches or Monte Carlo dropout for confidence scores