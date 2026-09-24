"""
OpenAI LLM Provider
"""
import openai
from typing import Any, Dict, List, Optional
from .base import BaseLLMProvider
from ..interface import LLMService


class OpenAILLMProvider(BaseLLMProvider):
    """
    OpenAI LLM provider implementation.
    """

    def __init__(self, api_key: str, model: str = "gpt-4", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Generate text using OpenAI API."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

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
        """Generate structured output using OpenAI API."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
                response_format={"type": "json_object"},
                **kwargs
            )
            import json
            json_data = json.loads(response.choices[0].message.content)
            return schema(**json_data)
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    async def health_check(self) -> bool:
        """Check if OpenAI API is available."""
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get OpenAI model information."""
        info = super().get_model_info()
        info.update({
            "provider": "openai",
            "model": self.model
        })
        return info
