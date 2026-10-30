"""
Application Configuration
"""
from pathlib import Path
from typing import List, Literal, Optional
from pydantic import Field, SecretStr, field_validator
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
    PLANTGUARD_DEVICE: Literal["auto", "cpu", "cuda", "cuda:0", "mps"] = "auto"
    PLANTGUARD_INFERENCE_PROFILE: Literal["auto", "cpu", "cuda", "remote"] = "auto"
    PLANTGUARD_OOD_CALIBRATION_PATH: Optional[Path] = None
    PLANTGUARD_CPU_MEMORY_LIMIT_GB: Optional[float] = Field(default=None, gt=0)
    PLANTGUARD_CUDA_MEMORY_LIMIT_GB: Optional[float] = Field(default=None, gt=0)
    PLANTGUARD_MAX_CONCURRENCY: int = Field(default=1, ge=1, le=8)
    PLANTGUARD_REMOTE_INFERENCE_URL: Optional[str] = None
    PLANTGUARD_REMOTE_INFERENCE_TOKEN: Optional[SecretStr] = None
    PLANTGUARD_REMOTE_IMAGE_UPLOAD_AUTHORIZED: bool = False
    PLANTGUARD_REMOTE_MAX_IMAGE_BYTES: int = Field(default=10 * 1024 * 1024, gt=0, le=50 * 1024 * 1024)
    PLANTGUARD_REMOTE_TIMEOUT_SECONDS: float = Field(default=60, gt=0, le=300)
    PLANTGUARD_REMOTE_MAX_CONCURRENCY: int = Field(default=1, ge=1, le=8)
    PLANTGUARD_DIAGNOSTICS_TOKEN: Optional[SecretStr] = None
    PLANTGUARD_LEAF_FILTER_VERSION: str = "v1"
    PLANTGUARD_DISEASE_CLASSIFIER_VARIANT: str = "fp32"
    PLANTGUARD_SEGFORMER_VARIANT: str = "plantseg-b0"

    @field_validator("PLANTGUARD_OOD_CALIBRATION_PATH", mode="before")
    @classmethod
    def empty_ood_calibration_path_is_unset(cls, value: object) -> object:
        return None if value == "" else value

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=(
            ".env",
            "backend/.env",
            str(Path(__file__).resolve().parent.parent.parent / ".env"),
            str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
        ),
        extra="ignore",
    )


# Create settings instance
settings = Settings()
