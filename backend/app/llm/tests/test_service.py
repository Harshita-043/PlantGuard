"""Provider selection must reject unconfigured and non-production providers."""

import pytest

from app.llm.service import LLMServiceManager


def test_unconfigured_provider_is_rejected():
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        LLMServiceManager._create_llm_service("")


def test_mock_provider_is_not_registered_for_application_use():
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        LLMServiceManager._create_llm_service("mock")
