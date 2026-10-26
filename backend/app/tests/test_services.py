"""The application service exposes typed inference without eager model loading."""

from app.ml.service import PlantAnalysisService as ModelInferenceService
from app.services.plant_analysis_service import (
    ApplicationPlantAnalysisService,
    create_plant_analysis_service,
)


def test_analysis_service_is_created_lazily():
    service = create_plant_analysis_service(device="cpu")
    assert isinstance(service, ApplicationPlantAnalysisService)
    assert isinstance(service.inference, ModelInferenceService)
    assert service.get_service_name() == "PlantGuardModelInference"
    assert not service.inference.sam.is_ready()
    assert not service.inference.leaf_filter.is_ready()
