"""Validation and generation for provider-independent object keys."""

import re
from uuid import uuid4

from app.storage.errors import InvalidObjectKey


_KEY_SEGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def validate_object_key(object_key: str) -> str:
    """Accept safe slash-delimited logical keys, rejecting filesystem traversal."""
    if not isinstance(object_key, str) or not object_key or len(object_key) > 512:
        raise InvalidObjectKey("Object key must be a non-empty string of at most 512 characters")
    if "\\" in object_key or "\x00" in object_key:
        raise InvalidObjectKey("Object key contains an unsafe path character")

    for segment in object_key.split("/"):
        if segment in {"", ".", ".."} or not _KEY_SEGMENT.fullmatch(segment) or segment.endswith("."):
            raise InvalidObjectKey("Object key contains an unsafe path segment")
        if segment.split(".", 1)[0].upper() in _WINDOWS_RESERVED_NAMES:
            raise InvalidObjectKey("Object key contains a reserved path segment")
    return object_key


def generate_object_key() -> str:
    """Return an unguessable, filename-independent object identifier."""
    return uuid4().hex
