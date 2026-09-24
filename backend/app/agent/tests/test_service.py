"""Agent service must not manufacture analysis without an ML implementation."""

import numpy as np
import pytest

from app.agent.service import AgentService
from app.services.plant_analysis_service import MLCapabilityUnavailable


def test_agent_service_initializes_without_claiming_analysis_is_available():
    service = AgentService()
    service.initialize()

    assert service.is_ready()
    assert service.get_service_name() == "AgentService"
    with pytest.raises(MLCapabilityUnavailable, match="no ML implementation is integrated"):
        import asyncio

        asyncio.run(service.analyze_image(np.zeros((8, 8, 3), dtype=np.uint8)))
