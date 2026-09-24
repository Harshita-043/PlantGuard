"""
Local/Ollama LLM Provider
"""
import httpx
from typing import Any, Dict, List, Optional
from .base import BaseLLMProvider
from ..interface import LLMService


class LocalLLMProvider(BaseLLMProvider):
    """
    Local/Ollama LLM provider implementation.
    """

    def __init__(self, api_key: str = "ollama", model: str = "llama2", base_url: str = "http://localhost:11434", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(base_url=self.base_url)

    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Generate text using Ollama API."""
        try:
            response = await self.client.post(
                "/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stop": stop or [],
                    "stream": False
                },
                **kwargs
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            raise Exception(f"Ollama API error: {str(e)}")

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
        """Generate structured output using Ollama API."""
        try:
            response = await self.client.post(
                "/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"You are a helpful assistant that outputs valid JSON. {prompt}",
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stop": stop or [],
                    "stream": False,
                    "format": "json"
                },
                **kwargs
            )
            response.raise_for_status()
            import json
            json_data = json.loads(response.json()["response"])
            return schema(**json_data)
        except Exception as e:
            raise Exception(f"Ollama API error: {str(e)}")

    async def health_check(self) -> bool:
        """Check if Ollama API is available."""
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            return True
        except Exception:
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get Ollama model information."""
        info = super().get_model_info()
        info.update({
            "provider": "local",
            "model": self.model
        })
        return info
