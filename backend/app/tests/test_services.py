"""
Test the ML services
"""
import numpy as np
from PIL import Image
import io

from app.services.plant_analysis_service import create_plant_analysis_service


def test_mock_services_creation():
    """Test that mock services are created correctly"""
    service = create_plant_analysis_service()
    assert service is not None
    assert service.get_service_name() == "MockPlantAnalysisService"
    assert service.is_ready() == True


def test_image_analysis():
    """Test analyzing a mock image"""
    service = create_plant_analysis_service()

    # Create a mock RGB image (100x100 pixels)
    mock_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

    # Analyze the image
    result = service.analyze_image(mock_image, "test-analysis-1")

    # Verify response structure
    assert result.analysis_id == "test-analysis-1"
    assert result.status == "completed"
    assert len(result.leaf_results) > 0  # Should detect some leaves
    assert result.plant_health_summary is not None
    assert result.ml_mode == "mock"
    assert result.processing_time_ms is not None

    # Verify leaf results have expected fields
    for leaf in result.leaf_results:
        assert leaf.leaf_index >= 0
        assert len(leaf.bounding_box) == 4
        assert 0 <= leaf.classification_confidence <= 1
        assert leaf.disease_class is not None
        assert leaf.severity_score >= 0 and leaf.severity_score <= 1

    # Verify plant health summary
    summary = result.plant_health_summary
    assert 0 <= summary.overall_health_score <= 100
    assert summary.healthy_leaf_count >= 0
    assert summary.total_leaf_count == len(result.leaf_results)
    assert len(summary.recommendations) > 0


def test_service_readiness():
    """Test that all services report ready"""
    service = create_plant_analysis_service()
    assert service.is_ready() == True

    # Check that individual services are ready too (this would require accessing internals)
    # For now, we trust that the initialization worked


if __name__ == "__main__":
    test_mock_services_creation()
    test_image_analysis()
    test_service_readiness()
    print("All tests passed!")