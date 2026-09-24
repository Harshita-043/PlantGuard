"""
LLM Providers Package
"""
from .base import BaseLLMProvider

# Try to import optional providers, gracefully handling missing dependencies
try:
    from .openai import OpenAILLMProvider
except ImportError:
    OpenAILLMProvider = None

try:
    from .anthropic import AnthropicLLMProvider
except ImportError:
    AnthropicLLMProvider = None

try:
    from .groq import GroqLLMProvider
except ImportError:
    GroqLLMProvider = None

try:
    from .local import LocalLLMProvider
except ImportError:
    LocalLLMProvider = None

__all__ = [
    "BaseLLMProvider",
]

if OpenAILLMProvider is not None:
    __all__.append("OpenAILLMProvider")

if AnthropicLLMProvider is not None:
    __all__.append("AnthropicLLMProvider")

if GroqLLMProvider is not None:
    __all__.append("GroqLLMProvider")

if LocalLLMProvider is not None:
    __all__.append("LocalLLMProvider")
