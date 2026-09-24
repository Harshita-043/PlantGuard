"""
LLM Service Factory and Manager
"""
import logging
from typing import Optional
from .interface import LLMService
from ..core.config import settings

logger = logging.getLogger(__name__)

# Try to import optional providers, gracefully handling missing dependencies
try:
    from .providers.openai import OpenAILLMProvider
except ImportError:
    OpenAILLMProvider = None

try:
    from .providers.anthropic import AnthropicLLMProvider
except ImportError:
    AnthropicLLMProvider = None

try:
    from .providers.groq import GroqLLMProvider
except ImportError:
    GroqLLMProvider = None

try:
    from .providers.local import LocalLLMProvider
except ImportError:
    LocalLLMProvider = None


class LLMServiceManager:
    """
    Manager for LLM services.
    Provides a singleton instance of the LLM service based on configuration.
    """
    _instance: Optional[LLMService] = None
    _provider: Optional[str] = None

    @classmethod
    def get_llm_service(cls) -> LLMService:
        """Get the LLM service instance based on configuration."""
        if cls._instance is None or cls._provider != settings.LLM_PROVIDER:
            cls._instance = cls._create_llm_service(settings.LLM_PROVIDER)
            cls._provider = settings.LLM_PROVIDER
            logger.info(f"Initialized LLM service: {settings.LLM_PROVIDER}")
        return cls._instance

    @classmethod
    def _create_llm_service(cls, provider: str) -> LLMService:
        """Create an LLM service instance based on the provider name."""
        provider = provider.lower()
        
        if provider == "openai":
            if OpenAILLMProvider is None:
                raise ImportError("OpenAI provider is not available. Install openai package to use this provider.")
            return OpenAILLMProvider(
                api_key=settings.LLM_API_KEY,
                model=settings.LLM_MODEL or "gpt-4"
            )
        elif provider == "anthropic":
            if AnthropicLLMProvider is None:
                raise ImportError("Anthropic provider is not available. Install anthropic package to use this provider.")
            return AnthropicLLMProvider(
                api_key=settings.LLM_API_KEY,
                model=settings.LLM_MODEL or "claude-3-opus-20240229"
            )
        elif provider == "groq":
            if GroqLLMProvider is None:
                raise ImportError("Groq provider is not available. Install groq package to use this provider.")
            return GroqLLMProvider(
                api_key=settings.LLM_API_KEY,
                model=settings.LLM_MODEL or "llama3-8b-8192"
            )
        elif provider == "local":
            if LocalLLMProvider is None:
                raise ImportError("Local provider is not available. Install httpx package to use this provider.")
            return LocalLLMProvider(
                api_key=settings.LLM_API_KEY or "ollama",
                model=settings.LLM_MODEL or "llama2",
                base_url=settings.LLM_BASE_URL or "http://localhost:11434"
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")


def get_llm_service() -> LLMService:
    """Get the LLM service instance."""
    return LLMServiceManager.get_llm_service()
