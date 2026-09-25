"""Errors shared by storage implementations."""


class StorageError(RuntimeError):
    """A storage operation failed."""


class StorageConfigurationError(StorageError):
    """Storage provider selection or configuration is invalid."""


class ObjectNotFound(StorageError):
    """The requested object does not exist."""


class InvalidObjectKey(StorageError):
    """An object key is not safe for use by the storage abstraction."""
