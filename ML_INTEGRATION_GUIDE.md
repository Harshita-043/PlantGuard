# Adding Trained ML Models to PlantGuard AI

This guide explains how to replace the mock ML implementations with your trained models.

## Overview

The PlantGuard AI backend is designed with clean separation between the application logic and ML models. All ML components implement specific interfaces, making it easy to swap mock implementations for real trained models without changing any other code.

## ML Pipeline Stages

The system consists of 7 ML stages that match your requested pipeline:

1. **Leaf Segmentation** - Segments individual leaves from whole plant images
2. **Disease Classification** - Classifies disease type for each leaf
3. **Disease Segmentation** - Segments diseased regions within each leaf
4. **Severity Calculation** - Calculates disease severity metrics
5. **Explainability** - Generates Grad-CAM visualizations for model predictions
6. **Leaf Tracking** - Tracks leaves across video frames (for video analysis)
7. **Plant Aggregation** - Combines leaf-level results into plant-level health assessment

## Interface Locations

All ML interfaces are located in:
`backend/app/ml/interfaces/`

Each stage has its own interface file:
- `leaf_segmentation.py`
- `disease_classification.py`
- `disease_segmentation.py`
- `severity_calculator.py`
- `explainability.py`
- `leaf_tracker.py`
- `plant_aggregator.py`

## Mock Implementations

Mock implementations for development/testing are located in:
`backend/app/ml/mocks/`

## How to Add Your Trained Models

### Step 1: Organize Your Model Artifacts

Place your trained models in the `ml-models/` directory (create if it doesn't exist):

```
ml-models/
├── leaf_segmentation/
│   ├── model.pth
│   └── config.yaml
├── disease_classification/
│   ├── model.pth
│   └── class_names.txt
├── disease_segmentation/
│   ├── model.pth
│   └── config.yaml
├── ... (other stages)
```

### Step 2: Create Real Model Implementations

Create a new directory for real model implementations:
`backend/app/ml/real_models/`

For each ML stage, create a class that implements the corresponding interface.

#### Example: Real Leaf Segmentation Model

```python
# backend/app/ml/real_models/leaf_segmentation.py
import torch
import numpy as np
from app.ml.interfaces.leaf_segmentation import LeafSegmentationModel
import logging

logger = logging.getLogger(__name__)

class TensorFlowLeafSegmentationModel(LeafSegmentationModel):
    def __init__(self, model_path: str):
        """
        Initialize the leaf segmentation model.
        
        Args:
            model_path: Path to the saved model directory or file
        """
        logger.info(f"Loading Leaf Segmentation model from {model_path}")
        # Load your TensorFlow/Keras model
        # self.model = tf.keras.models.load_model(model_path)
        # Or for PyTorch:
        # self.model = torch.load(model_path)
        self.model_path = model_path
        logger.info("Leaf Segmentation model loaded successfully")
    
    def segment_leaves(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Segment leaves from the input plant image using your trained model.
        
        Args:
            image: Input RGB image as numpy array (H, W, 3)
            
        Returns:
            List of leaf detections with bounding boxes, masks, and confidence scores
        """
        # Preprocess image for your model
        # processed_image = preprocess_for_model(image)
        
        # Run inference
        # predictions = self.model.predict(processed_image)
        
        # Post-process predictions to get leaf detections
        # leaf_detections = postprocess_predictions(predictions, image.shape)
        
        # For now, returning mock data - replace with actual model inference
        logger.info("Running REAL Leaf Segmentation model")
        h, w = image.shape[:2]
        return [
            {
                "bbox": [0.2, 0.3, 0.4, 0.5],
                "mask": None,  # Your model should return actual mask data
                "confidence": 0.95
            }
            # ... actual detections from your model
        ]
```

### Step 3: Update Pipeline Configuration

Modify the pipeline initialization in `backend/app/main.py` to use your real models instead of mocks:

```python
# Instead of:
# pipeline = PlantHealthPipeline(
#     leaf_segmentation_model=MockLeafSegmentationModel(),
#     disease_classification_model=MockDiseaseClassificationModel(),
#     # ... etc
# )

# Use:
from app.ml.real_models.leaf_segmentation import TensorFlowLeafSegmentationModel
from app.ml.real_models.disease_classification import PyTorchDiseaseClassificationModel
# ... import other real models

pipeline = PlantHealthPipeline(
    leaf_segmentation_model=TensorFlowLeafSegmentationModel(
        model_path="./ml-models/leaf_segmentation/"
    ),
    disease_classification_model=PyTorchDiseaseClassificationModel(
        model_path="./ml-models/disease_classification/"
    ),
    # ... initialize other real models
)
```

### Step 4: Configure Model Usage

Add a configuration option to easily switch between mock and real models:

In `backend/app/core/config.py`:
```python
# Add to Settings class:
USE_MOCK_MODELS: bool = True  # Set to False to use real models
ML_MODEL_PATH: str = "./ml-models"
```

Then in `main.py`:
```python
from app.core.config import settings

# Initialize models based on setting
if settings.USE_MOCK_MODELS:
    # Use mock models (current behavior)
    leaf_segmentation_model = MockLeafSegmentationModel()
else:
    # Use real models
    leaf_segmentation_model = TensorFlowLeafSegmentationModel(
        model_path=f"{settings.ML_MODEL_PATH}/leaf_segmentation/"
    )
```

## Important Considerations

### Input/Output Contracts
Each interface defines specific input/output formats that your implementations must follow:

1. **Leaf Segmentation**: 
   - Input: RGB numpy array (H, W, 3)
   - Output: List of dicts with `bbox` [x,y,w,h] (normalized 0-1), optional `mask`, `confidence`

2. **Disease Classification**:
   - Input: RGB leaf image numpy array (H, W, 3)
   - Output: Dict with `disease_class` (string), `confidence` (0-1), optional `all_probabilities`

3. **Disease Segmentation**:
   - Input: RGB leaf image numpy array (H, W, 3)
   - Output: Dict with `mask` (boolean numpy array H, W), `diseased_area_ratio` (0-1), optional `bounding_box`

4. **And so on for other interfaces...**

### Performance Tips
- Batch processing: Consider processing multiple leaves at once if your model supports it
- GPU utilization: Ensure your models are configured to use GPU when available
- Memory management: Properly dispose of intermediate tensors to avoid memory leaks
- Preprocessing: Match the preprocessing used during model training exactly

### Testing Your Implementation
1. Start with a single model type (e.g., just leaf segmentation)
2. Keep other stages as mocks to isolate issues
3. Verify the output format matches expectations
4. Test with sample images to ensure reasonable results
5. Gradually replace more stages with real models

## Verification

When your models are correctly integrated:
1. The API endpoints will work exactly as before
2. Frontend will display results from your real models
3. All mock log messages will be replaced with real model logging
4. No changes needed to frontend, database, or API contracts

## Troubleshooting

- **Shape errors**: Verify your model's expected input/output shapes
- **Normalization issues**: Ensure preprocessing matches training exactly
- **Interface mismatches**: Double-check that your implementation returns exactly what the interface specifies
- **Performance bottlenecks**: Profile each stage to identify slow components

## Contact

If you encounter issues integrating your specific model architecture, refer to the interface definitions or consult with the ML team.