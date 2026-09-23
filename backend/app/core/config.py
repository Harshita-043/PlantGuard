"""
Application Configuration
"""
import os
from typing import Optional
from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # Application
    APP_NAME: str = "PlantGuard AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # API
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "PlantGuard AI"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # Database
    DATABASE_URL: str = "sqlite:///./plantguard.db"  # Default to SQLite for dev
    # For PostgreSQL: "postgresql://user:password@postgres:5432/plantguard"

    # ML Model Settings
    ML_MODEL_PATH: str = "./ml-models"  # Base path for model artifacts
    ML_MODE: str = "mock"  # "mock" or "real" - controls whether to use mock or real ML models

    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    UPLOAD_FOLDER: str = "./uploads"
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/jpg"]

    # Object Storage Settings
    STORAGE_PROVIDER: str = "mock"  # "mock", "s3", "minio", etc.
    STORAGE_BUCKET: str = "plantguard-ai"  # Bucket/container name
    STORAGE_REGION: str = "us-east-1"  # Storage region
    STORAGE_ENDPOINT: str = ""  # Custom endpoint (for MinIO, etc.) - empty for AWS
    STORAGE_ACCESS_KEY: str = ""  # Access key (empty for mock/IAM roles)
    STORAGE_SECRET_KEY: str = ""  # Secret key (empty for mock/IAM roles)
    STORAGE_PRESIGNED_URL_EXPIRY: int = 3600  # Expiry time for signed URLs (seconds)
    MAX_IMAGE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    MAX_VIDEO_SIZE: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]
    ALLOWED_VIDEO_TYPES: List[str] = ["video/mp4", "video/quicktime", "video/x-msvideo"]

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    class Config:
        case_sensitive = True
        env_file = ".env"


# Create settings instance
settings = Settings()