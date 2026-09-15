# PlantGuard AI Datasets

## Overview
PlantGuard AI uses the PlantVillage dataset for training and evaluating its plant disease classification model.

## PlantVillage Dataset

### Description
The PlantVillage dataset is a publicly available dataset of plant leaf images labeled with diseases and healthy conditions. It contains images of various crops with multiple disease types per crop.

### Source
- **Origin**: PlantVillage Project (Penn State University)
- **Access**: Publicly available via Kaggle and other repositories
- **Version**: Likely the standard version used in plant pathology research

### Dataset Characteristics
- **Total Classes**: 38 plant disease/health combinations
- **Image Type**: RGB leaf photographs
- **Variability**: 
  - Different lighting conditions
  - Various backgrounds (some with context, some isolated leaves)
  - Different resolutions and qualities
  - Real-world field conditions

### Class Distribution
Based on `class_names.json` and typical PlantVillage distribution:
- **Apple**: 4 classes (scab, black rot, cedar rust, healthy)
- **Blueberry**: 1 class (healthy)
- **Cherry**: 2 classes (powdery mildew, healthy)
- **Corn**: 4 classes (Cercospora/Gray leaf spot, common rust, northern leaf blight, healthy)
- **Grape**: 4 classes (black rot, esca, leaf blight, healthy)
- **Orange**: 1 class (huanglongbing/citrus greening)
- **Pepper**: 2 classes (bacterial spot, healthy)
- **Potato**: 3 classes (early blight, late blight, healthy)
- **Raspberry**: 1 class (healthy)
- **Soybean**: 1 class (healthy)
- **Squash**: 1 class (powdery mildew)
- **Strawberry**: 2 classes (leaf scorch, healthy)
- **Tomato**: 10 classes (bacterial spot, early blight, late blight, leaf mold, septoria leaf spot, spider mites, target spot, tomato yellow leaf curl virus, tomato mosaic virus, healthy)

### Preprocessing Applied
For training the EfficientNetV2-B0 model:
1. **Resizing**: All images resized to 224x224 pixels
2. **Normalization**: EfficientNetV2-specific preprocessing (based on ImageNet statistics)
3. **Data Augmentation** (likely applied during training):
   - Rotation
   - Width/height shift
   - Shear
   - Zoom
   - Horizontal flip
   - Brightness adjustment

### Train/Validation/Test Split
From training history observations:
- **Training**: Approximately 70% of data
- **Validation**: Approximately 20% of data (used for early stopping and hyperparameter tuning)
- **Test**: Approximately 10% of data (final evaluation)

### Data Quality
- **Label Accuracy**: High-quality expert labeling
- **Image Quality**: Varied; includes both lab-quality and field images
- **Class Balance**: Likely imbalanced (some diseases more common than others); model may have been trained with class weighting or balanced sampling

### Limitations
1. **Geographic Bias**: Primarily represents diseases visible in certain regions/climates
2. **Seasonal Variability**: May not capture all disease stages
3. **Image Consistency**: Varied backgrounds and lighting may affect generalization
4. **Limited Species**: Only includes specific crops listed in class names
5. **No Temporal Data**: Single time-point images, no progression data

### Usage in PlantGuard AI
- **Training**: Used to train the EfficientNetV2-B0 classification model
- **Validation**: Used for hyperparameter tuning and early stopping
- **Testing**: Final evaluation showing 95.94% test accuracy
- **Deployment**: Model expects similar preprocessing as applied to PlantVillage images

### Alternative/Supplemental Datasets Considered
- **PlantDoc**: Another plant disease dataset with different imaging conditions
- **Custom Field Images**: Real-world images from target deployment environments
- **Augmented Synthetic Data**: GAN-generated or augmented images for rare classes

### Data Governance
- **Licensing**: PlantVillage dataset is typically free for research and educational use; commercial use should verify license
- **Privacy**: No personal data in plant leaf images
- **Bias Mitigation**: Should evaluate model performance across different disease severities and image qualities

### Future Data Needs
1. **Local Field Data**: Images from target deployment regions to improve geographic generalization
2. **Severity Scaling**: Images representing different disease progression stages
3. **Multi-angle Views**: Top, side, close-up images for better robustness
4. **Underserved Crops**: Expansion to other economically important plants
5. **Continuous Learning Pipeline**: Mechanism to collect and label new images from users

### References
- Hughes, D. P., et al. (2015). "Using Deep Learning for Image-Based Plant Disease Detection." Frontiers in Plant Science, 6, 1425.
- PlantVillage Dataset Repository: https://www.kaggle.com/datasets/emmarex/plantdisease (example)