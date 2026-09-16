# PlantGuard AI Machine Learning Graph

## Overview
The ML component of PlantGuard AI uses a service-oriented architecture with clearly defined interfaces for each stage of the plant health analysis pipeline. This design allows for independent development and seamless integration of ML models developed separately.

## ML Service Architecture
PlantGuard AI implements a pipeline of isolated ML services, each responsible for a specific stage of plant health analysis:

1. **Leaf Segmentation Service** - Segments individual leaves from whole plant images
2. **Disease Classification Service** - Classifies disease type for each leaf
3. **Disease Segmentation Service** - Segments diseased regions within each leaf
4. **Severity Service** - Calculates disease severity metrics
5. **Explainability Service** - Generates Grad-CAM visualizations for model predictions
6. **Video Tracking Service** - Tracks leaves across video frames (for video analysis)
7. **Plant Aggregator Service** - Aggregates leaf-level results into plant-level assessment
8. **Plant Analysis Service** - Orchestrates the complete ML pipeline

## Pipeline Flow
```
Whole Plant Image / Video
        ↓
Leaf Segmentation Service
        ↓
Multiple Leaf Objects (N leaves, dynamic count)
        ↓
For each leaf [0..N-1]:
        ↓
Disease Classification Service
        ↓
Disease Segmentation Service
        ↓
Severity Service
        ↓
Explainability Service
        ↓
Per-Leaf Result
        ↓
Plant Aggregator Service
        ↓
Plant-Level Aggregation
        ↓
Plant Health Report
        ↓
Care Recommendations
```

## Service Interfaces (Contracts)
Each service implements a clearly defined interface with specific input/output contracts:

### LeafSegmentationService
- **Input**: RGB numpy array (H, W, 3)
- **Output**: List of detections with:
  - `bbox`: [x_min, y_min, width, height] (normalized 0-1)
  - `mask`: Optional segmentation mask (boolean numpy array H, W)
  - `confidence`: Detection confidence score (0-1)

### DiseaseClassificationService
- **Input**: RGB leaf image numpy array (H, W, 3)
- **Output**: Dict with:
  - `disease_class`: String identifier (e.g., "healthy", "leaf_spot")
  - `confidence`: Confidence score (0-1)
  - `all_probabilities`: Optional dict of all class probabilities

### DiseaseSegmentationService
- **Input**: RGB leaf image numpy array (H, W, 3)
- **Output**: Dict with:
  - `mask`: Segmentation mask (boolean numpy array H, W)
  - `diseased_area_ratio`: Ratio of diseased pixels (0-1)
  - `bounding_box`: Optional [x_min, y_min, width, height] (normalized)

### SeverityService
- **Input**: Leaf RGB numpy array (H, W, 3), disease mask (boolean numpy array H, W)
- **Output**: Dict with:
  - `severity_score`: Overall severity (0-1)
  - `affected_percentage`: Percentage affected (0-100)
  - `severity_level`: Categorical level (low, medium, high)
  - `metrics`: Additional severity metrics (optional)

### ExplainabilityService
- **Input**: Leaf RGB numpy array (H, W, 3), disease class (string)
- **Output**: Dict with:
  - `heatmap`: Normalized heatmap (0-1)
  - `overlay`: Optional RGB overlay visualization
  - `activation_map`: Optional raw activation values

### VideoTrackingService
- **Input**: Previous leaf detections, current video frame (H, W, 3)
- **Output**: List of tracked leaf detections with updated bboxes, masks, confidences, leaf_ids

### PlantAggregatorService
- **Input**: List of LeafResult objects
- **Output**: PlantHealthSummary with:
  - `overall_health_score`: Overall plant health (0-100)
  - `health_status`: Overall status (excellent, good, fair, poor, critical)
  - `healthy_leaf_count`: Number of healthy leaves
  - `total_leaf_count`: Total leaves analyzed
  - `disease_summary`: Disease distribution counts
  - `risk_assessment`: Overall risk level (low, medium, high)
  - `recommendations`: List of care recommendations

### PlantAnalysisService
- **Input**: RGB image/frame (H, W, 3), optional analysis ID
- **Output**: PlantAnalysisResponse with complete analysis results

## Implementation Details
- **Service Location**: `backend/app/services/`
- **Interfaces**: `backend/app/services/interfaces/` (abstract base classes)
- **Mock Implementations**: `backend/app/services/mock/` (for development/testing)
- **Service Factory**: `backend/app/services/plant_analysis_service.py` (creates appropriate services based on ML_MODE)
- **Configuration**: `backend/app/core/config.py` (ML_MODE=mock/real, ML_MODEL_PATH)

## Current Limitations (Development Stage)
1. **Mock Implementations**: Currently using mock services for development/testing
2. **Real Service Implementations**: To be created when ML models are available
3. **Model Artifacts**: To be placed in `ml-models/` directory structure
4. **Production Deployment**: Infrastructure setup pending

## Dependencies
- NumPy (for array operations in service interfaces)
- Pydantic (for data validation and contracts)
- Optional ML framework dependencies (to be implemented in real services)

## Integration Points
- **Backend API**: `POST /api/v1/analyze/image` and `POST /api/v1/analyze/video`
- **Service Orchestration**: Handled by PlantAnalysisService
- **Data Transfer**: Standardized contracts between services
- **Model Storage**: `ml-models/{service_type}/` directory structure

## Future Improvements
1. **Real Service Implementations**: Replace mock services with actual ML model implementations
2. **Model Optimization**: GPU acceleration, batch processing, model quantization
3. **Continuous Learning**: Pipeline for retraining with new field data
4. **Advanced Explainability**: Enhanced Grad-CAM or alternative techniques
5. **Uncertainty Estimation**: Bayesian approaches or ensemble methods for confidence scores
6. **Model Monitoring**: Performance tracking, drift detection, A/B testing
7. **Ensemble Methods**: Combine multiple models for improved robustness
8. **Edge Deployment**: TensorFlow Lite, TensorFlow.js, or ONNX conversion for deployment flexibility

## Model Artifacts Storage
When ML models are available, they should be stored in:
```
ml-models/
├── leaf_segmentation/
│   ├── model.pth or .h5 or .pb
│   └── config.yaml
├── disease_classification/
│   ├── model.pth or .h5 or .pb
│   └── class_names.txt
├── disease_segmentation/
│   ├── model.pth or .h5 or .pb
│   └── config.yaml
├── severity/
│   └── model.pth or .h5 or .pb
├── explainability/
│   └── model.pth or .h5 or .pb
├── video_tracking/
│   └── model.pth or .h5 or .pb
└── plant_aggregator/
    └── model.pth or .h5 or .pb
```

## Integration Readiness
The architecture is designed for seamless integration of independently-developed ML models:
- **Zero Frontend Changes**: Frontend consumes only standardized API responses
- **Zero Backend Contract Changes**: API endpoints remain stable regardless of ML model source
- **True Separation of Concerns**: ML logic isolated in `backend/app/services/`
- **Environment-Based Configuration**: Simple toggle via `ML_MODE=mock` or `ML_MODE=real`
- **Well-Defined Contracts**: Clear input/output specifications for all ML services
- **Dynamic Leaf Handling**: Supports arbitrary number of detected leaves (no hard-coded limits)
- **Framework Agnostic**: Compatible with TensorFlow, PyTorch, JAX, or any other ML framework