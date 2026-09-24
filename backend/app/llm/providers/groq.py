"""
Groq LLM Provider
"""
from groq import Groq
from typing import Any, Dict, List, Optional
from .base import BaseLLMProvider
from ..interface import LLMService


class GroqLLMProvider(BaseLLMProvider):
    """
    Groq LLM provider implementation.
    """

    def __init__(self, api_key: str, model: str = "llama3-8b-8192", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.client = Groq(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Generate text using Groq API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Groq API error: {str(e)}")

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
        """Generate structured output using Groq API."""
        try:
            response = self.client.chat.completions.create(
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
            raise Exception(f"Groq API error: {str(e)}")

    async def health_check(self) -> bool:
        """Check if Groq API is available."""
        try:
            self.client.chat.completions.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception:
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get Groq model information."""
        info = super().get_model_info()
        info.update({
            "provider": "groq",
            "model": self.model
        })
        return info
