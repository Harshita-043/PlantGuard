"""Explicit construction of configured storage providers."""

from app.core.config import Settings, settings
from app.storage.errors import StorageConfigurationError
from app.storage.interface import ObjectStorage
from app.storage.local import LocalFileObjectStorage


def create_object_storage(configuration: Settings | None = None) -> ObjectStorage:
    """Build the selected adapter; never fall back between providers."""
    config = configuration or settings
    provider = config.OBJECT_STORAGE_PROVIDER

    if provider == "local":
        return LocalFileObjectStorage(config.LOCAL_STORAGE_ROOT)
    if provider == "r2":
        required = {
            "R2_BUCKET_NAME": config.R2_BUCKET_NAME,
            "R2_ENDPOINT_URL": config.R2_ENDPOINT_URL,
            "R2_ACCESS_KEY_ID": config.R2_ACCESS_KEY_ID,
            "R2_SECRET_ACCESS_KEY": config.R2_SECRET_ACCESS_KEY,
        }
        missing = [name for name, value in required.items() if value is None or not _configured_value(value)]
        if missing:
            raise StorageConfigurationError(
                "R2 storage configuration is incomplete; set: " + ", ".join(missing)
            )

        from app.storage.r2 import CloudflareR2ObjectStorage

        return CloudflareR2ObjectStorage(
            endpoint_url=config.R2_ENDPOINT_URL,
            bucket_name=config.R2_BUCKET_NAME,
            access_key_id=config.R2_ACCESS_KEY_ID.get_secret_value(),
            secret_access_key=config.R2_SECRET_ACCESS_KEY.get_secret_value(),
        )
    if provider == "supabase":
        required = {
            "SUPABASE_STORAGE_ENDPOINT": config.SUPABASE_STORAGE_ENDPOINT,
            "SUPABASE_STORAGE_REGION": config.SUPABASE_STORAGE_REGION,
            "SUPABASE_STORAGE_BUCKET": config.SUPABASE_STORAGE_BUCKET,
            "SUPABASE_STORAGE_ACCESS_KEY_ID": config.SUPABASE_STORAGE_ACCESS_KEY_ID,
            "SUPABASE_STORAGE_SECRET_ACCESS_KEY": config.SUPABASE_STORAGE_SECRET_ACCESS_KEY,
        }
        missing = [name for name, value in required.items() if value is None or not _configured_value(value)]
        if missing:
            raise StorageConfigurationError(
                "Supabase storage configuration is incomplete; set: " + ", ".join(missing)
            )

        from app.storage.supabase import SupabaseStorageAdapter

        return SupabaseStorageAdapter(
            endpoint_url=config.SUPABASE_STORAGE_ENDPOINT,
            region=config.SUPABASE_STORAGE_REGION,
            bucket_name=config.SUPABASE_STORAGE_BUCKET,
            access_key_id=config.SUPABASE_STORAGE_ACCESS_KEY_ID.get_secret_value(),
            secret_access_key=config.SUPABASE_STORAGE_SECRET_ACCESS_KEY.get_secret_value(),
        )
    raise StorageConfigurationError(
        "No object storage provider is selected; set OBJECT_STORAGE_PROVIDER to 'local', 'r2', or 'supabase'"
    )


def _configured_value(value: object) -> bool:
    if hasattr(value, "get_secret_value"):
        value = value.get_secret_value()
    return isinstance(value, str) and bool(value.strip())
