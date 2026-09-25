"""
Application Configuration
"""
from pathlib import Path
from typing import List, Literal, Optional
from pydantic import Field, SecretStr
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
    OBJECT_STORAGE_PROVIDER: Optional[Literal["local", "r2", "supabase"]] = None
    LOCAL_STORAGE_ROOT: Path = Path(".local-storage")
    R2_BUCKET_NAME: Optional[str] = None
    R2_ENDPOINT_URL: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[SecretStr] = None
    R2_SECRET_ACCESS_KEY: Optional[SecretStr] = None
    SUPABASE_STORAGE_ENDPOINT: Optional[str] = None
    SUPABASE_STORAGE_REGION: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: Optional[str] = None
    SUPABASE_STORAGE_ACCESS_KEY_ID: Optional[SecretStr] = None
    SUPABASE_STORAGE_SECRET_ACCESS_KEY: Optional[SecretStr] = None
    JWT_SECRET_KEY: Optional[SecretStr] = None
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0, le=1440)

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")


# Create settings instance
settings = Settings()
