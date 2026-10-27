"""Provider-independent object storage contract."""

from dataclasses import dataclass
from typing import Mapping, Protocol


@dataclass(frozen=True)
class StoredObject:
    """Object bytes and the metadata needed to interpret them."""

    object_key: str
    content: bytes
    content_type: str | None
    metadata: Mapping[str, str]


class ObjectStorage(Protocol):
    """Private storage operations required by the API lifecycle."""

    def check_ready(self) -> bool:
        """Probe provider access without reading or writing user objects."""
        ...

    def create_download_url(self, object_key: str, *, expires_in: int = 300) -> str | None:
        """Create a short-lived provider URL, or None when an authenticated API proxy is needed."""
        ...

    def put(
        self,
        content: bytes,
        *,
        object_key: str | None = None,
        content_type: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> str:
        """Write bytes and return their safe object key; generate a key if omitted."""
        ...

    def get(self, object_key: str) -> StoredObject:
        """Read an object or raise ObjectNotFound."""
        ...

    def exists(self, object_key: str) -> bool:
        """Return whether an object is stored under this key."""
        ...

    def delete(self, object_key: str) -> None:
        """Delete an object; deleting a missing key is a no-op."""
        ...
