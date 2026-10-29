"""Supabase Storage adapter tests using Botocore's request stubs."""

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
from app.storage.supabase import SupabaseStorageAdapter


_ENDPOINT = "https://project-ref.storage.supabase.co/storage/v1/s3"
_REGION = "ap-south-1"
_BUCKET = "plantguard-private"
_ACCESS_KEY = "test-supabase-access-key"
_SECRET_KEY = "test-supabase-secret-key"
_PREFIX = "plantguard/"


def _clear_storage_environment(monkeypatch):
    for name in (
        "OBJECT_STORAGE_PROVIDER",
        "SUPABASE_STORAGE_ENDPOINT",
        "SUPABASE_STORAGE_REGION",
        "SUPABASE_STORAGE_BUCKET",
        "SUPABASE_STORAGE_ACCESS_KEY_ID",
        "SUPABASE_STORAGE_SECRET_ACCESS_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def _adapter():
    client = boto3.client(
        "s3",
        endpoint_url=_ENDPOINT,
        region_name=_REGION,
        aws_access_key_id=_ACCESS_KEY,
        aws_secret_access_key=_SECRET_KEY,
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 0}),
    )
    adapter = SupabaseStorageAdapter(
        endpoint_url=_ENDPOINT,
        region=_REGION,
        bucket_name=_BUCKET,
        access_key_id=_ACCESS_KEY,
        secret_access_key=_SECRET_KEY,
        s3_client=client,
    )
    return adapter, client


def _configuration(**overrides):
    values = {
        "_env_file": None,
        "OBJECT_STORAGE_PROVIDER": "supabase",
        "SUPABASE_STORAGE_ENDPOINT": _ENDPOINT,
        "SUPABASE_STORAGE_REGION": _REGION,
        "SUPABASE_STORAGE_BUCKET": _BUCKET,
        "SUPABASE_STORAGE_ACCESS_KEY_ID": SecretStr(_ACCESS_KEY),
        "SUPABASE_STORAGE_SECRET_ACCESS_KEY": SecretStr(_SECRET_KEY),
    }
    values.update(overrides)
    return Settings(**values)


def test_supabase_adapter_validates_endpoint_region_bucket_and_credentials():
    base = {
        "region": _REGION,
        "bucket_name": _BUCKET,
        "access_key_id": _ACCESS_KEY,
        "secret_access_key": _SECRET_KEY,
    }
    for invalid_endpoint in (
        "http://project-ref.storage.supabase.co/storage/v1/s3",
        "https://attacker.example/storage/v1/s3",
        "https://user:pass@project-ref.storage.supabase.co/storage/v1/s3",
        "https://project-ref.storage.supabase.co/other",
    ):
        with pytest.raises(StorageConfigurationError):
            SupabaseStorageAdapter(endpoint_url=invalid_endpoint, **base)

    with pytest.raises(StorageConfigurationError, match="region"):
        SupabaseStorageAdapter(endpoint_url=_ENDPOINT, **{**base, "region": " "})


def test_factory_requires_explicit_provider_and_does_not_fall_back(tmp_path, monkeypatch):
    _clear_storage_environment(monkeypatch)
    with pytest.raises(StorageConfigurationError, match="No object storage provider"):
        create_object_storage(Settings(_env_file=None))
    with pytest.raises(StorageConfigurationError, match="Supabase storage configuration is incomplete"):
        create_object_storage(Settings(_env_file=None, OBJECT_STORAGE_PROVIDER="supabase"))

    local = create_object_storage(
        Settings(_env_file=None, OBJECT_STORAGE_PROVIDER="local", LOCAL_STORAGE_ROOT=tmp_path / "local")
    )
    assert isinstance(local, LocalFileObjectStorage)


def test_factory_selects_supabase_with_complete_configuration():
    storage = create_object_storage(_configuration())
    assert isinstance(storage, SupabaseStorageAdapter)


def test_supabase_client_uses_sigv4_path_style_and_presigned_get(monkeypatch):
    signed_adapter, _ = _adapter()
    captured = {}

    def fake_client(service, **kwargs):
        captured["service"] = service
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("app.storage.supabase.boto3.client", fake_client)
    adapter = SupabaseStorageAdapter(
        endpoint_url=_ENDPOINT,
        region=_REGION,
        bucket_name=_BUCKET,
        access_key_id=_ACCESS_KEY,
        secret_access_key=_SECRET_KEY,
    )

    assert adapter is not None
    assert captured["service"] == "s3"
    assert captured["config"].signature_version == "s3v4"
    assert captured["config"].s3["addressing_style"] == "path"
    assert captured["region_name"] == _REGION

    signed_url = signed_adapter.create_download_url("plants/leaf.png")
    assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in signed_url
    assert "X-Amz-Expires=300" in signed_url
    assert "plantguard/plants/leaf.png" in signed_url


def test_supabase_credentials_are_redacted_from_settings_representation():
    settings = _configuration()
    assert _ACCESS_KEY not in repr(settings)
    assert _SECRET_KEY not in repr(settings)


def test_upload_preserves_binary_content_type_metadata_and_namespaces_key():
    adapter, client = _adapter()
    data = b"\x00\xffplant-image"
    with Stubber(client) as stubber:
        stubber.add_response(
            "put_object",
            {"ETag": '"etag"'},
            {
                "Bucket": _BUCKET,
                "Key": _PREFIX + "plants/plant-1/image",
                "Body": data,
                "ContentType": "image/webp",
                "Metadata": {"source": "upload"},
            },
        )
        key = adapter.put(
            data,
            object_key="plants/plant-1/image",
            content_type="image/webp",
            metadata={"source": "upload"},
        )
    assert key == "plants/plant-1/image"


def test_upload_generates_safe_key_when_omitted(monkeypatch):
    import app.storage.supabase as supabase_storage

    adapter, client = _adapter()
    monkeypatch.setattr(supabase_storage, "generate_object_key", lambda: "generated-key")
    with Stubber(client) as stubber:
        stubber.add_response(
            "put_object",
            {"ETag": '"etag"'},
            {"Bucket": _BUCKET, "Key": _PREFIX + "generated-key", "Body": b"image"},
        )
        assert adapter.put(b"image") == "generated-key"


def test_read_preserves_binary_content_type_and_metadata():
    adapter, client = _adapter()
    content = bytes(range(256)) * 2
    with Stubber(client) as stubber:
        stubber.add_response(
            "get_object",
            {
                "Body": StreamingBody(io.BytesIO(content), len(content)),
                "ContentType": "image/png",
                "Metadata": {"source": "camera"},
            },
            {"Bucket": _BUCKET, "Key": _PREFIX + "plants/leaf"},
        )
        stored = adapter.get("plants/leaf")
    assert stored.object_key == "plants/leaf"
    assert stored.content == content
    assert stored.content_type == "image/png"
    assert stored.metadata == {"source": "camera"}


def test_exists_and_missing_object():
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
            {"Bucket": _BUCKET, "Key": _PREFIX + "exists"},
        )
        stubber.add_client_error(
            "head_object",
            service_error_code="404",
            http_status_code=404,
            expected_params={"Bucket": _BUCKET, "Key": _PREFIX + "missing"},
        )
        assert adapter.exists("exists")
        assert not adapter.exists("missing")


def test_delete_and_missing_object_are_successful():
    adapter, client = _adapter()
    with Stubber(client) as stubber:
        stubber.add_response("delete_object", {}, {"Bucket": _BUCKET, "Key": _PREFIX + "nested/object"})
        stubber.add_client_error(
            "delete_object",
            service_error_code="NoSuchKey",
            http_status_code=404,
            expected_params={"Bucket": _BUCKET, "Key": _PREFIX + "missing"},
        )
        adapter.delete("nested/object")
        adapter.delete("missing")


def test_missing_read_raises_object_not_found():
    adapter, client = _adapter()
    with Stubber(client) as stubber:
        stubber.add_client_error(
            "get_object",
            service_error_code="NoSuchKey",
            http_status_code=404,
            expected_params={"Bucket": _BUCKET, "Key": _PREFIX + "missing"},
        )
        with pytest.raises(ObjectNotFound):
            adapter.get("missing")


@pytest.mark.parametrize(
    ("method", "operation", "key", "params"),
    [
        ("put", "put_object", "write-failure", {"Bucket": _BUCKET, "Key": _PREFIX + "write-failure", "Body": b"x"}),
        ("get", "get_object", "read-failure", {"Bucket": _BUCKET, "Key": _PREFIX + "read-failure"}),
        ("delete", "delete_object", "delete-failure", {"Bucket": _BUCKET, "Key": _PREFIX + "delete-failure"}),
    ],
)
def test_provider_failures_are_sanitized(method, operation, key, params):
    adapter, client = _adapter()
    with Stubber(client) as stubber:
        stubber.add_client_error(
            operation,
            service_error_code="AccessDenied",
            service_message=_SECRET_KEY,
            http_status_code=403,
            expected_params=params,
        )
        with pytest.raises(StorageError) as raised:
            getattr(adapter, method)(b"x", object_key=key) if method == "put" else getattr(adapter, method)(key)
    assert _SECRET_KEY not in str(raised.value)


def test_missing_bucket_and_network_failures_become_storage_errors():
    adapter, client = _adapter()
    with Stubber(client) as stubber:
        stubber.add_client_error(
            "put_object",
            service_error_code="NoSuchBucket",
            http_status_code=404,
            expected_params={"Bucket": _BUCKET, "Key": _PREFIX + "missing-bucket", "Body": b"x"},
        )
        with pytest.raises(StorageError, match="bucket is missing"):
            adapter.put(b"x", object_key="missing-bucket")

    def fail_request(**_kwargs):
        raise EndpointConnectionError(endpoint_url=_ENDPOINT)

    client.put_object = fail_request
    with pytest.raises(StorageError, match="provider unavailable"):
        adapter.put(b"x", object_key="network-failure")


@pytest.mark.parametrize("key", ["../outside", "/absolute", "nested/../../escape", "nested\\escape"])
def test_unsafe_object_keys_are_rejected_before_provider_call(key):
    adapter, _client = _adapter()
    with pytest.raises(InvalidObjectKey):
        adapter.put(b"x", object_key=key)
    with pytest.raises(InvalidObjectKey):
        adapter.get(key)


def test_secret_configuration_is_required_without_cloud_fallback(monkeypatch):
    _clear_storage_environment(monkeypatch)
    config = Settings(_env_file=None, OBJECT_STORAGE_PROVIDER="supabase")
    with pytest.raises(StorageConfigurationError, match="SUPABASE_STORAGE_ENDPOINT"):
        create_object_storage(config)
