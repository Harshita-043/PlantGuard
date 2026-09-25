"""Private local-filesystem object storage for development."""

import hashlib
import json
import os
import struct
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.storage.errors import ObjectNotFound, StorageError
from app.storage.interface import StoredObject
from app.storage.keys import generate_object_key, validate_object_key


_MAGIC = b"PLANTGUARD-OBJECT\x01"
_HEADER_LENGTH = struct.Struct(">I")
_MAX_HEADER_BYTES = 1024 * 1024


class LocalFileObjectStorage:
    """Store objects privately below an explicitly selected local root.

    Object keys are validated and hashed to opaque filenames. Each object is one
    atomically replaced file containing its metadata and exact binary payload.
    """

    def __init__(self, root: str | os.PathLike[str]):
        try:
            configured_root = Path(root).expanduser()
            configured_root.mkdir(parents=True, exist_ok=True)
            self._root = configured_root.resolve(strict=True)
            if not self._root.is_dir():
                raise NotADirectoryError("Storage root is not a directory")
        except OSError as exc:
            raise StorageError("Could not initialize the local storage root") from exc

    def put(
        self,
        content: bytes,
        *,
        object_key: str | None = None,
        content_type: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> str:
        key = validate_object_key(object_key if object_key is not None else generate_object_key())
        if not isinstance(content, (bytes, bytearray, memoryview)):
            raise TypeError("Object content must be bytes-like")
        if content_type is not None and (not isinstance(content_type, str) or not content_type):
            raise ValueError("Content type must be a non-empty string or None")
        if metadata is not None and not isinstance(metadata, Mapping):
            raise TypeError("Object metadata must be a string-to-string mapping")
        stored_metadata = dict(metadata or {})
        if any(not isinstance(name, str) or not isinstance(value, str) for name, value in stored_metadata.items()):
            raise TypeError("Object metadata must be a string-to-string mapping")

        header = {
            "object_key": key,
            "content_type": content_type,
            "metadata": stored_metadata,
        }
        try:
            encoded_header = json.dumps(header, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
            if len(encoded_header) > _MAX_HEADER_BYTES:
                raise ValueError("Object metadata is too large")
        except (TypeError, ValueError) as exc:
            raise StorageError("Object metadata could not be encoded") from exc

        target = self._object_path(key)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".plantguard-", suffix=".tmp", dir=self._root, delete=False
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(_MAGIC)
                temporary_file.write(_HEADER_LENGTH.pack(len(encoded_header)))
                temporary_file.write(encoded_header)
                temporary_file.write(bytes(content))
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            self._assert_confined(target)
            os.replace(temporary_path, target)
            temporary_path = None
            return key
        except OSError as exc:
            raise StorageError("Could not write the local object") from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def get(self, object_key: str) -> StoredObject:
        key = validate_object_key(object_key)
        path = self._object_path(key)
        self._assert_confined(path)
        try:
            with path.open("rb") as stored_file:
                magic = stored_file.read(len(_MAGIC))
                header_length_bytes = stored_file.read(_HEADER_LENGTH.size)
                if magic != _MAGIC or len(header_length_bytes) != _HEADER_LENGTH.size:
                    raise StorageError("Stored object has an invalid format")
                header_length = _HEADER_LENGTH.unpack(header_length_bytes)[0]
                if header_length > _MAX_HEADER_BYTES:
                    raise StorageError("Stored object metadata exceeds the supported size")
                encoded_header = stored_file.read(header_length)
                if len(encoded_header) != header_length:
                    raise StorageError("Stored object metadata is incomplete")
                header: Any = json.loads(encoded_header.decode("utf-8"))
                content = stored_file.read()
        except FileNotFoundError as exc:
            raise ObjectNotFound(f"Object {key!r} does not exist") from exc
        except StorageError:
            raise
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, struct.error) as exc:
            raise StorageError("Could not read the local object") from exc

        if (
            not isinstance(header, dict)
            or header.get("object_key") != key
            or (header.get("content_type") is not None and not isinstance(header.get("content_type"), str))
            or not isinstance(header.get("metadata"), dict)
            or any(not isinstance(name, str) or not isinstance(value, str) for name, value in header["metadata"].items())
        ):
            raise StorageError("Stored object metadata is invalid")
        return StoredObject(
            object_key=key,
            content=content,
            content_type=header["content_type"],
            metadata=dict(header["metadata"]),
        )

    def exists(self, object_key: str) -> bool:
        key = validate_object_key(object_key)
        path = self._object_path(key)
        self._assert_confined(path)
        if path.is_symlink():
            raise StorageError("Stored object path cannot be a symbolic link")
        try:
            if path.exists() and not path.is_file():
                raise StorageError("Stored object path is not a regular file")
            return path.is_file()
        except OSError as exc:
            raise StorageError("Could not inspect the local object") from exc

    def delete(self, object_key: str) -> None:
        key = validate_object_key(object_key)
        path = self._object_path(key)
        self._assert_confined(path)
        if path.is_symlink():
            raise StorageError("Stored object path cannot be a symbolic link")
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise StorageError("Could not delete the local object") from exc

    def _object_path(self, object_key: str) -> Path:
        digest = hashlib.sha256(object_key.encode("ascii")).hexdigest()
        return self._root / f"{digest}.object"

    def _assert_confined(self, path: Path) -> None:
        try:
            if not path.resolve(strict=False).is_relative_to(self._root):
                raise StorageError("Resolved object path escapes the configured storage root")
        except OSError as exc:
            raise StorageError("Could not resolve the local object path") from exc
