"""
Scan-related API endpoints
"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List
import uuid
import numpy as np
from PIL import Image
import io

from app.ml.pipeline import PlantHealthPipeline
from app.ml.mocks import (
    MockLeafSegmentationModel,
    MockDiseaseClassificationModel,
    MockDiseaseSegmentationModel,
    MockSeverityCalculator,
    MockExplainabilityModel,
    MockLeafTracker,
    MockPlantAggregator
)
from app.schemas import (
    ScanResponse,
    ScanSummary,
    ScanDetail,
    HealthReportResponse
)

router = APIRouter()

# Initialize pipeline with mock models (for development)
# In production, these would be replaced with real model implementations
pipeline = PlantHealthPipeline(
    leaf_segmentation_model=MockLeafSegmentationModel(),
    disease_classification_model=MockDiseaseClassificationModel(),
    disease_segmentation_model=MockDiseaseSegmentationModel(),
    severity_calculator=MockSeverityCalculator(),
    explainability_model=MockExplainabilityModel(),
    leaf_tracker=MockLeafTracker(),
    plant_aggregator=MockPlantAggregator()
)


@router.post("/scan", response_model=ScanResponse)
async def create_scan(
    file: UploadFile = File(...)
):
    """
    Upload a plant image and initiate the health analysis pipeline
    """
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        # Read and process the image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))

        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Convert to numpy array for ML processing
        image_array = np.array(image)

        # Process the image through the ML pipeline
        scan_id = str(uuid.uuid4())
        result = pipeline.process_image(
            image_array=image_array,
            scan_id=scan_id
        )

        # Return scan response
        return ScanResponse(
            scan_id=scan_id,
            message="Scan processed successfully",
            status="completed"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing scan: {str(e)}")


@router.get("/scans", response_model=List[ScanSummary])
async def get_scans(skip: int = 0, limit: int = 10):
    """
    Get paginated list of user's scans
    """
    # TODO: Implement actual database query
    # For now, return mock data
    mock_scans = [
        ScanSummary(
            id="scan_1",
            plant_name="Monstera deliciosa",
            date="2024-06-12T10:30:00Z",
            status="completed",
            overall_health_score=85.5
        ),
        ScanSummary(
            id="scan_2",
            plant_name="Fiddle leaf fig",
            date="2024-06-11T14:22:00Z",
            status="completed",
            overall_health_score=92.0
        )
    ]
    return mock_scans[skip:skip+limit]


@router.get("/scans/{scan_id}", response_model=ScanDetail)
async def get_scan(scan_id: str):
    """
    Get detailed results for a specific scan
    """
    # TODO: Implement actual database query
    # For now, return mock data
    if scan_id not in ["scan_1", "scan_2"]:
        raise HTTPException(status_code=404, detail="Scan not found")

    return ScanDetail(
        id=scan_id,
        plant_name="Monstera deliciosa",
        date="2024-06-12T10:30:00Z",
        status="completed",
        image_url="/uploads/scans/scan_1.jpg",
        leaf_results=[
            {
                "leaf_index": 0,
                "bounding_box": [0.2, 0.3, 0.4, 0.5],
                "disease_class": "healthy",
                "confidence": 0.92,
                "severity_score": 0.1
            },
            {
                "leaf_index": 1,
                "bounding_box": [0.5, 0.2, 0.3, 0.4],
                "disease_class": "leaf_spot",
                "confidence": 0.78,
                "severity_score": 0.6
            }
        ],
        health_report={
            "overall_health_score": 85.5,
            "recommendations": [
                "Monitor leaf spot on lower leaves",
                "Consider reducing watering frequency",
                "Ensure proper air circulation around plant"
            ]
        }
    )


@router.get("/scans/{scan_id}/report", response_model=HealthReportResponse)
async def get_scan_report(scan_id: str):
    """
    Get formatted health report for a specific scan
    """
    # TODO: Implement actual database query
    # For now, return mock data
    if scan_id not in ["scan_1", "scan_2"]:
        raise HTTPException(status_code=404, detail="Scan not found")

    return HealthReportResponse(
        scan_id=scan_id,
        overall_health_score=85.5,
        health_status="good",
        recommendations=[
            "Monitor leaf spot on lower leaves",
            "Consider reducing watering frequency",
            "Ensure proper air circulation around plant",
            "Apply neem oil treatment if spots spread",
            "Check soil moisture levels weekly"
        ]
    )