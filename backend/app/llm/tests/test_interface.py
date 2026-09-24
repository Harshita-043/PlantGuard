"""
Tests for the LLM interface.
"""
import pytest
from app.llm.interface import LLMService


def test_llm_service_is_abstract():
    """Test that LLMService cannot be instantiated directly."""
    with pytest.raises(TypeError):
        LLMService()