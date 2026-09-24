"""
LLM Service Interface
Defines the contract for LLM services in PlantGuard AI.
"""
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from pydantic import BaseModel


class LLMService(ABC):
    """
    Interface for LLM services.
    Responsible for providing language model capabilities to the agentic system.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: The input prompt
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            stop: List of stop sequences
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text string
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> BaseModel:
        """
        Generate structured output conforming to a Pydantic schema.

        Args:
            prompt: The input prompt
            schema: Pydantic model class for output validation
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            stop: List of stop sequences
            **kwargs: Additional provider-specific parameters

        Returns:
            Pydantic model instance with validated output
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the LLM service is available and healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        pass

    @abstractmethod
    def get_service_name(self) -> str:
        """
        Get the name of the LLM service.

        Returns:
            str: Service name (e.g., "openai-gpt4", "anthropic-claude-3")
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the LLM model.

        Returns:
            Dictionary with model information (name, version, provider, etc.)
        """
        pass