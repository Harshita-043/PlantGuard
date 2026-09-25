"""Focused tests for the provider-independent local object storage adapter."""

import re

import pytest

from app.storage import (
    InvalidObjectKey,
    LocalFileObjectStorage,
    ObjectNotFound,
    StorageError,
)


def test_put_generates_safe_object_key_and_writes_object(tmp_path):
    storage = LocalFileObjectStorage(tmp_path / "private")

    key = storage.put(b"plant bytes", content_type="image/png")

    assert re.fullmatch(r"[0-9a-f]{32}", key)
    assert storage.exists(key)


def test_put_and_read_nested_object_key(tmp_path):
    storage = LocalFileObjectStorage(tmp_path / "private")
    key = "plants/plant-123/scans/scan-456/source-image"

    returned_key = storage.put(b"image", object_key=key)

    assert returned_key == key
    assert storage.get(key).content == b"image"


def test_read_existing_object_preserves_binary_content_and_metadata(tmp_path):
    storage = LocalFileObjectStorage(tmp_path / "private")
    content = bytes(range(256)) * 4
    metadata = {"source": "upload", "purpose": "plant-image"}
    key = storage.put(content, object_key="images/binary.bin", content_type="image/png", metadata=metadata)

    stored = storage.get(key)

    assert stored.object_key == key
    assert stored.content == content
    assert stored.content_type == "image/png"
    assert stored.metadata == metadata


def test_missing_object_raises_object_not_found(tmp_path):
    storage = LocalFileObjectStorage(tmp_path / "private")

    with pytest.raises(ObjectNotFound):
        storage.get("missing/object")


def test_exists_reports_present_and_missing_objects(tmp_path):
    storage = LocalFileObjectStorage(tmp_path / "private")
    key = storage.put(b"data")

    assert storage.exists(key)
    assert not storage.exists("missing")


def test_delete_removes_existing_object(tmp_path):
    storage = LocalFileObjectStorage(tmp_path / "private")
    key = storage.put(b"data")

    storage.delete(key)

    assert not storage.exists(key)
    with pytest.raises(ObjectNotFound):
        storage.get(key)


def test_delete_missing_object_is_idempotent(tmp_path):
    storage = LocalFileObjectStorage(tmp_path / "private")

    storage.delete("missing/object")


@pytest.mark.parametrize(
    "unsafe_key",
    [
        "../outside",
        "images/../../outside",
        r"..\outside",
        r"images\..\outside",
        "/absolute/path",
        r"C:\outside\file",
        "images//empty-segment",
        "images/./dot-segment",
        "images/NUL.txt",
        "images/trailing.",
    ],
)
def test_unsafe_object_keys_are_rejected(tmp_path, unsafe_key):
    storage = LocalFileObjectStorage(tmp_path / "private")

    with pytest.raises(InvalidObjectKey):
        storage.put(b"data", object_key=unsafe_key)


def test_traversal_attempt_cannot_read_or_modify_outside_root(tmp_path):
    storage_root = tmp_path / "private"
    outside_file = tmp_path / "outside"
    outside_file.write_bytes(b"keep")
    storage = LocalFileObjectStorage(storage_root)

    with pytest.raises(InvalidObjectKey):
        storage.delete("../outside")

    assert outside_file.read_bytes() == b"keep"
    assert list(storage_root.iterdir()) == []


def test_local_files_do_not_use_the_supplied_key_as_a_filesystem_path(tmp_path):
    storage_root = tmp_path / "private"
    storage = LocalFileObjectStorage(storage_root)
    key = storage.put(b"data", object_key="user-filename.jpg")

    stored_paths = list(storage_root.iterdir())
    assert len(stored_paths) == 1
    assert stored_paths[0].name != key
    assert re.fullmatch(r"[0-9a-f]{64}\.object", stored_paths[0].name)


def test_failed_atomic_write_raises_storage_error_and_cleans_temporary_file(tmp_path, monkeypatch):
    import app.storage.local as local_storage

    storage_root = tmp_path / "private"
    storage = LocalFileObjectStorage(storage_root)

    def fail_replace(_source, _target):
        raise PermissionError("write denied")

    monkeypatch.setattr(local_storage.os, "replace", fail_replace)

    with pytest.raises(StorageError):
        storage.put(b"data", object_key="failing-write")

    assert list(storage_root.iterdir()) == []
    assert not storage.exists("failing-write")


def test_non_directory_storage_root_raises_storage_error(tmp_path):
    root_file = tmp_path / "root-file"
    root_file.write_bytes(b"not a directory")

    with pytest.raises(StorageError):
        LocalFileObjectStorage(root_file)


def test_invalid_metadata_is_rejected_before_writing(tmp_path):
    storage_root = tmp_path / "private"
    storage = LocalFileObjectStorage(storage_root)

    with pytest.raises(TypeError):
        storage.put(b"data", metadata={"size": 12})

    assert list(storage_root.iterdir()) == []
