"""Provider readiness checks use read-only access probes."""

from types import SimpleNamespace

from app.storage.local import LocalFileObjectStorage
from app.storage.r2 import CloudflareR2ObjectStorage
from app.storage.supabase import SupabaseStorageAdapter


ENDPOINT_SUPABASE = "https://project-ref.storage.supabase.co/storage/v1/s3"
ENDPOINT_R2 = "https://account.r2.cloudflarestorage.com"


def test_local_storage_readiness_requires_accessible_root(tmp_path):
    storage = LocalFileObjectStorage(tmp_path / "objects")
    assert storage.check_ready()


def test_supabase_readiness_uses_head_bucket_only():
    calls = []
    client = SimpleNamespace(head_bucket=lambda **params: calls.append(params) or {})
    storage = SupabaseStorageAdapter(
        endpoint_url=ENDPOINT_SUPABASE,
        region="ap-south-1",
        bucket_name="plantguard-private",
        access_key_id="test-access-key",
        secret_access_key="test-secret-key",
        s3_client=client,
    )

    assert storage.check_ready()
    assert calls == [{"Bucket": "plantguard-private"}]


def test_r2_readiness_uses_head_bucket_only():
    calls = []
    client = SimpleNamespace(head_bucket=lambda **params: calls.append(params) or {})
    storage = CloudflareR2ObjectStorage(
        endpoint_url=ENDPOINT_R2,
        bucket_name="plantguard-private",
        access_key_id="test-access-key",
        secret_access_key="test-secret-key",
        s3_client=client,
    )

    assert storage.check_ready()
    assert calls == [{"Bucket": "plantguard-private"}]

def test_supabase_download_url_is_short_lived_and_namespaced():
    calls = []
    client = SimpleNamespace(generate_presigned_url=lambda *args, **kwargs: calls.append((args, kwargs)) or
                             "https://project-ref.storage.supabase.co/signed/object")
    storage = SupabaseStorageAdapter(
        endpoint_url=ENDPOINT_SUPABASE,
        region="ap-south-1",
        bucket_name="plantguard-private",
        access_key_id="test-access-key",
        secret_access_key="test-secret-key",
        s3_client=client,
    )

    result = storage.create_download_url("analyses/scan-1/masks/cam.png", expires_in=300)

    assert result.startswith("https://")
    assert calls == [(('get_object',), {
        "Params": {"Bucket": "plantguard-private", "Key": "plantguard/analyses/scan-1/masks/cam.png"},
        "ExpiresIn": 300,
        "HttpMethod": "GET",
    })]


def test_s3_download_url_expiry_is_bounded():
    import pytest
    from app.storage import StorageError

    storage = SupabaseStorageAdapter(
        endpoint_url=ENDPOINT_SUPABASE,
        region="ap-south-1",
        bucket_name="plantguard-private",
        access_key_id="test-access-key",
        secret_access_key="test-secret-key",
        s3_client=SimpleNamespace(generate_presigned_url=lambda *_args, **_kwargs: "https://example.test"),
    )
    for expiry in (0, 30, 901, True):
        with pytest.raises(ValueError):
            storage.create_download_url("analyses/scan-1/masks/cam.png", expires_in=expiry)


def test_local_storage_requires_authenticated_api_proxy(tmp_path):
    storage = LocalFileObjectStorage(tmp_path / "private")
    assert storage.create_download_url("analyses/scan-1/masks/cam.png") is None