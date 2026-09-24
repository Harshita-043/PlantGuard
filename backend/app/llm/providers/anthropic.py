"""
Anthropic LLM Provider
"""
import anthropic
from typing import Any, Dict, List, Optional
from .base import BaseLLMProvider
from ..interface import LLMService


class AnthropicLLMProvider(BaseLLMProvider):
    """
    Anthropic LLM provider implementation.
    """

    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Generate text using Anthropic API."""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or 1024,
                temperature=temperature,
                stop_sequences=stop,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            return response.content[0].text
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")

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
        """Generate structured output using Anthropic API."""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or 1024,
                temperature=temperature,
                stop_sequences=stop,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                **kwargs
            )
            import json
            json_data = json.loads(response.content[0].text)
            return schema(**json_data)
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")

    async def health_check(self) -> bool:
        """Check if Anthropic API is available."""
        try:
            # Anthropic doesn't have a direct health check endpoint,
            # so we'll try a minimal request
            await self.client.messages.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception:
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get Anthropic model information."""
        info = super().get_model_info()
        info.update({
            "provider": "anthropic",
            "model": self.model
        })
        return info
