"""The application must fail closed when real inference is not integrated."""

import pytest

from app.services.plant_analysis_service import (
    MLCapabilityUnavailable,
    create_plant_analysis_service,
)


def test_analysis_service_is_unavailable_without_real_ml():
    with pytest.raises(MLCapabilityUnavailable, match="no ML implementation is integrated"):
        create_plant_analysis_service()
