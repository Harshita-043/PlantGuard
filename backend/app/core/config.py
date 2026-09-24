"""
Application Configuration
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # Optional provider abstraction settings. Agentic requests are disabled.
    LLM_PROVIDER: str = ""  # openai, anthropic, groq, or local
    LLM_MODEL: str = ""  # Provider-specific model identifier
    LLM_API_KEY: Optional[str] = None  # API key for the provider
    LLM_BASE_URL: str = "http://localhost:11434"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:8080"]
    DATABASE_URL: Optional[str] = None

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")


# Create settings instance
settings = Settings()
