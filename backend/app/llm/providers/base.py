"""
Base LLM Provider
Base class for all LLM provider implementations.
"""
from typing import Any, Dict, List, Optional
from ..interface import LLMService


class BaseLLMProvider(LLMService):
    """
    Base class for LLM providers.
    """

    def __init__(self, api_key: str, model: str, **kwargs):
        self.api_key = api_key
        self.model = model
        self.additional_params = kwargs

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the LLM model."""
        return {
            "provider": self.__class__.__name__.lower().replace("provider", ""),
            "model": self.model,
        }
