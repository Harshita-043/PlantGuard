"""The application service exposes typed inference without eager model loading."""

from types import SimpleNamespace

import numpy as np
import pytest

from app.ml.errors import InferenceError, InferenceErrorCode
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


def test_legacy_adapter_rejects_ood_result_it_cannot_represent():
    result = SimpleNamespace(
        leaves=[SimpleNamespace(ood=SimpleNamespace(is_ood=True))],
    )
    inference = SimpleNamespace(analyze=lambda *_args, **_kwargs: result)
    service = ApplicationPlantAnalysisService(inference=inference)

    with pytest.raises(InferenceError) as exc:
        service.analyze_image(np.zeros((1, 1, 3), dtype=np.uint8))

    assert exc.value.code == InferenceErrorCode.OUT_OF_DISTRIBUTION
    assert exc.value.stage == "ood_detection"
