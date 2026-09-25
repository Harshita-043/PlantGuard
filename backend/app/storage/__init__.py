"""Provider-independent object storage contracts and adapters."""

from app.storage.errors import InvalidObjectKey, ObjectNotFound, StorageConfigurationError, StorageError
from app.storage.factory import create_object_storage
from app.storage.interface import ObjectStorage, StoredObject
from app.storage.local import LocalFileObjectStorage
from app.storage.supabase import SupabaseStorageAdapter

__all__ = [
    "InvalidObjectKey",
    "LocalFileObjectStorage",
    "ObjectNotFound",
    "ObjectStorage",
    "StorageConfigurationError",
    "StorageError",
    "SupabaseStorageAdapter",
    "StoredObject",
    "create_object_storage",
]
