"""Cloudflare R2 adapter tests using Botocore's real SDK request stubs."""

import io
from datetime import datetime, timezone

import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import EndpointConnectionError
from botocore.response import StreamingBody
from botocore.stub import Stubber
from pydantic import SecretStr

from app.core.config import Settings
from app.storage import (
    InvalidObjectKey,
    LocalFileObjectStorage,
    ObjectNotFound,
    StorageConfigurationError,
    StorageError,
    create_object_storage,
)
from app.storage.r2 import CloudflareR2ObjectStorage


_ENDPOINT = "https://test-account.r2.cloudflarestorage.com"
_BUCKET = "plantguard-test"
_ACCESS_KEY = "test-access-key"
_SECRET_KEY = "test-secret-key-value"
_STORAGE_ENVIRONMENT_VARIABLES = (
    "OBJECT_STORAGE_PROVIDER",
    "R2_BUCKET_NAME",
    "R2_ENDPOINT_URL",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
)


def _clear_storage_environment(monkeypatch):
    for name in _STORAGE_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def _adapter():
    client = boto3.client(
        "s3",
        endpoint_url=_ENDPOINT,
        region_name="auto",
        aws_access_key_id=_ACCESS_KEY,
        aws_secret_access_key=_SECRET_KEY,
        config=Config(retries={"max_attempts": 0}),
    )
    adapter = CloudflareR2ObjectStorage(
        endpoint_url=_ENDPOINT,
        bucket_name=_BUCKET,
        access_key_id=_ACCESS_KEY,
        secret_access_key=_SECRET_KEY,
        s3_client=client,
    )
    return adapter, client


def test_r2_provider_configuration_is_validated_before_client_use():
    with pytest.raises(StorageConfigurationError, match="HTTPS"):
        CloudflareR2ObjectStorage(
            endpoint_url="http://test-account.r2.cloudflarestorage.com",
            bucket_name=_BUCKET,
            access_key_id=_ACCESS_KEY,
            secret_access_key=_SECRET_KEY,
        )

    with pytest.raises(StorageConfigurationError, match="hostname"):
        CloudflareR2ObjectStorage(
            endpoint_url="https://attacker.example",
            bucket_name=_BUCKET,
            access_key_id=_ACCESS_KEY,
            secret_access_key=_SECRET_KEY,
        )


def test_factory_requires_an_explicit_provider_and_never_falls_back(tmp_path, monkeypatch):
    _clear_storage_environment(monkeypatch)
    missing_selection = Settings(_env_file=None, OBJECT_STORAGE_PROVIDER=None)
    with pytest.raises(StorageConfigurationError, match="No object storage provider"):
        create_object_storage(missing_selection)

    incomplete_r2 = Settings(_env_file=None, OBJECT_STORAGE_PROVIDER="r2")
    with pytest.raises(StorageConfigurationError, match="R2 storage configuration is incomplete"):
        create_object_storage(incomplete_r2)

    local = Settings(
        _env_file=None,
        OBJECT_STORAGE_PROVIDER="local",
        LOCAL_STORAGE_ROOT=tmp_path / "local-objects",
    )
    adapter = create_object_storage(local)
    assert isinstance(adapter, LocalFileObjectStorage)


def test_factory_selects_r2_with_explicit_configuration():
    configuration = Settings(
        _env_file=None,
        OBJECT_STORAGE_PROVIDER="r2",
        R2_ENDPOINT_URL=_ENDPOINT,
        R2_BUCKET_NAME=_BUCKET,
        R2_ACCESS_KEY_ID=SecretStr(_ACCESS_KEY),
        R2_SECRET_ACCESS_KEY=SecretStr(_SECRET_KEY),
    )

    adapter = create_object_storage(configuration)

    assert isinstance(adapter, CloudflareR2ObjectStorage)


def test_r2_client_uses_sigv4_and_preserves_presigned_get_compatibility(monkeypatch):
    signed_adapter, _ = _adapter()
    captured = {}

    def fake_client(service, **kwargs):
        captured["service"] = service
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("app.storage.r2.boto3.client", fake_client)
    adapter = CloudflareR2ObjectStorage(
        endpoint_url=_ENDPOINT,
        bucket_name=_BUCKET,
        access_key_id=_ACCESS_KEY,
        secret_access_key=_SECRET_KEY,
    )

    assert adapter is not None
    assert captured["service"] == "s3"
    assert captured["config"].signature_version == "s3v4"
    assert captured["region_name"] == "auto"
    assert captured["endpoint_url"] == _ENDPOINT

    signed_url = signed_adapter.create_download_url("plants/leaf.png")
    assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in signed_url
    assert "X-Amz-Expires=300" in signed_url
    assert "plantguard/plants/leaf.png" in signed_url


def test_secret_configuration_is_redacted_in_settings_representation():
    configuration = Settings(
        _env_file=None,
        OBJECT_STORAGE_PROVIDER="r2",
        R2_ACCESS_KEY_ID=SecretStr(_ACCESS_KEY),
        R2_SECRET_ACCESS_KEY=SecretStr(_SECRET_KEY),
    )

    assert _ACCESS_KEY not in repr(configuration)
    assert _SECRET_KEY not in repr(configuration)


def test_upload_uses_private_namespace_and_preserves_type_metadata():
    adapter, client = _adapter()
    key = "images/plant-123/input"
    request = {
        "Bucket": _BUCKET,
        "Key": f"plantguard/{key}",
        "Body": b"\x00\xffplant-image",
        "ContentType": "image/webp",
        "Metadata": {"source": "upload"},
    }
    with Stubber(client) as stubber:
        stubber.add_response("put_object", {"ETag": '"etag"'}, request)

        returned_key = adapter.put(
            request["Body"],
            object_key=key,
            content_type="image/webp",
            metadata={"source": "upload"},
        )

    assert returned_key == key


def test_upload_generates_a_safe_namespaced_key(monkeypatch):
    import app.storage.r2 as r2_storage

    adapter, client = _adapter()
    monkeypatch.setattr(r2_storage, "generate_object_key", lambda: "generated-key")

    with Stubber(client) as stubber:
        stubber.add_response(
            "put_object",
            {"ETag": '"etag"'},
            {"Bucket": _BUCKET, "Key": "plantguard/generated-key", "Body": b"image"},
        )
        key = adapter.put(b"image")
        stubber.assert_no_pending_responses()

    assert key == "generated-key"


def test_read_returns_exact_binary_content_and_object_metadata():
    adapter, client = _adapter()
    key = "plants/leaf-1"
    content = bytes(range(256)) * 3
    response = {
        "Body": StreamingBody(io.BytesIO(content), len(content)),
        "ContentType": "image/png",
        "Metadata": {"source": "capture"},
    }
    with Stubber(client) as stubber:
        stubber.add_response(
            "get_object",
            response,
            {"Bucket": _BUCKET, "Key": f"plantguard/{key}"},
        )

        stored = adapter.get(key)

    assert stored.object_key == key
    assert stored.content == content
    assert stored.content_type == "image/png"
    assert stored.metadata == {"source": "capture"}


def test_exists_uses_head_object():
    adapter, client = _adapter()
    with Stubber(client) as stubber:
        stubber.add_response(
            "head_object",
            {
                "ContentLength": 1,
                "ETag": '"etag"',
                "LastModified": datetime.now(timezone.utc),
                "ContentType": "image/png",
                "Metadata": {},
            },
            {"Bucket": _BUCKET, "Key": "plantguard/existing"},
        )

        assert adapter.exists("existing")


def test_delete_uses_delete_object():
    adapter, client = _adapter()
    with Stubber(client) as stubber:
        stubber.add_response(
            "delete_object",
            {},
            {"Bucket": _BUCKET, "Key": "plantguard/nested/object"},
        )

        adapter.delete("nested/object")


def test_delete_of_missing_object_is_idempotent():
    adapter, client = _adapter()
    with Stubber(client) as stubber:
        stubber.add_client_error(
            "delete_object",
            service_error_code="NoSuchKey",
            http_status_code=404,
            expected_params={"Bucket": _BUCKET, "Key": "plantguard/missing"},
        )

        adapter.delete("missing")


def test_missing_get_is_translated_to_object_not_found():
    adapter, client = _adapter()
    with Stubber(client) as stubber:
        stubber.add_client_error(
            "get_object",
            service_error_code="NoSuchKey",
            http_status_code=404,
            expected_params={"Bucket": _BUCKET, "Key": "plantguard/missing"},
        )

        with pytest.raises(ObjectNotFound):
            adapter.get("missing")


def test_missing_exists_returns_false():
    adapter, client = _adapter()
    with Stubber(client) as stubber:
        stubber.add_client_error(
            "head_object",
            service_error_code="404",
            http_status_code=404,
            expected_params={"Bucket": _BUCKET, "Key": "plantguard/missing"},
        )

        assert not adapter.exists("missing")


def test_missing_bucket_is_a_clear_storage_failure():
    adapter, client = _adapter()
    with Stubber(client) as stubber:
        stubber.add_client_error(
            "put_object",
            service_error_code="NoSuchBucket",
            http_status_code=404,
            expected_params={"Bucket": _BUCKET, "Key": "plantguard/object", "Body": b"image"},
        )

        with pytest.raises(StorageError, match="bucket is missing or unavailable"):
            adapter.put(b"image", object_key="object")


@pytest.mark.parametrize(
    ("method", "operation", "params"),
    [
        ("put", "put_object", {"Bucket": _BUCKET, "Key": "plantguard/upload-fail", "Body": b"x"}),
        ("get", "get_object", {"Bucket": _BUCKET, "Key": "plantguard/read-fail"}),
        ("delete", "delete_object", {"Bucket": _BUCKET, "Key": "plantguard/delete-fail"}),
    ],
)
def test_provider_failures_are_translated_without_leaking_secrets(method, operation, params):
    adapter, client = _adapter()
    with Stubber(client) as stubber:
        stubber.add_client_error(
            operation,
            service_error_code="AccessDenied",
            service_message=_SECRET_KEY,
            http_status_code=403,
            expected_params=params,
        )

        with pytest.raises(StorageError) as error:
            if method == "put":
                adapter.put(b"x", object_key="upload-fail")
            elif method == "get":
                adapter.get("read-fail")
            else:
                adapter.delete("delete-fail")

    assert _SECRET_KEY not in str(error.value)
    assert "credentials" not in repr(adapter).lower()


def test_provider_network_failure_is_translated():
    adapter, client = _adapter()

    def fail_request(**_kwargs):
        raise EndpointConnectionError(endpoint_url=_ENDPOINT)

    client.put_object = fail_request
    with pytest.raises(StorageError, match="provider unavailable"):
        adapter.put(b"image", object_key="network-failure")


def test_r2_rejects_traversal_and_does_not_use_filename_as_provider_path():
    adapter, client = _adapter()
    with Stubber(client) as stubber:
        stubber.add_response(
            "put_object",
            {"ETag": '"etag"'},
            {"Bucket": _BUCKET, "Key": "plantguard/plant-123/scan-456/image.jpg", "Body": b"image"},
        )
        adapter.put(b"image", object_key="plant-123/scan-456/image.jpg")

        with pytest.raises(InvalidObjectKey):
            adapter.put(b"image", object_key="../../outside")

        stubber.assert_no_pending_responses()


def test_incomplete_production_provider_configuration_fails_clearly(monkeypatch):
    _clear_storage_environment(monkeypatch)
    configuration = Settings(_env_file=None, OBJECT_STORAGE_PROVIDER="r2", R2_BUCKET_NAME=_BUCKET)

    with pytest.raises(StorageConfigurationError) as error:
        create_object_storage(configuration)

    assert "R2_ENDPOINT_URL" in str(error.value)
    assert "R2_ACCESS_KEY_ID" in str(error.value)
    assert _SECRET_KEY not in str(error.value)
