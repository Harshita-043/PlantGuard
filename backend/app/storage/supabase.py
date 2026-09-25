"""Supabase Storage adapter using the project's S3-compatible endpoint."""

from collections.abc import Mapping
from urllib.parse import urlsplit

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectTimeoutError,
    EndpointConnectionError,
    HTTPClientError,
    ReadTimeoutError,
)

from app.storage.errors import ObjectNotFound, StorageConfigurationError, StorageError
from app.storage.interface import StoredObject
from app.storage.keys import generate_object_key, validate_object_key


_SUPABASE_NAMESPACE = "plantguard/"


class SupabaseStorageAdapter:
    """Store objects in one private Supabase Storage bucket through its S3 API."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        region: str,
        bucket_name: str,
        access_key_id: str,
        secret_access_key: str,
        s3_client: BaseClient | None = None,
    ):
        _validate_configuration(endpoint_url, region, bucket_name, access_key_id, secret_access_key)
        self._bucket_name = bucket_name
        if s3_client is None:
            try:
                s3_client = boto3.client(
                    "s3",
                    endpoint_url=endpoint_url,
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    config=Config(
                        connect_timeout=3,
                        read_timeout=20,
                        retries={"max_attempts": 2, "mode": "standard"},
                        s3={"addressing_style": "path"},
                    ),
                )
            except BotoCoreError:
                raise StorageConfigurationError("Could not initialize the Supabase Storage S3 client") from None
        self._client = s3_client

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
        custom_metadata = dict(metadata or {})
        if any(not isinstance(name, str) or not isinstance(value, str) for name, value in custom_metadata.items()):
            raise TypeError("Object metadata must be a string-to-string mapping")

        request: dict[str, object] = {
            "Bucket": self._bucket_name,
            "Key": self._provider_key(key),
            "Body": bytes(content),
        }
        if content_type is not None:
            request["ContentType"] = content_type
        if custom_metadata:
            request["Metadata"] = custom_metadata
        self._call("upload", "put_object", **request)
        return key

    def get(self, object_key: str) -> StoredObject:
        key = validate_object_key(object_key)
        response = self._call(
            "read",
            "get_object",
            Bucket=self._bucket_name,
            Key=self._provider_key(key),
        )
        body = response.get("Body")
        if body is None or not hasattr(body, "read"):
            raise StorageError("Supabase Storage read returned an invalid object body")
        try:
            content = body.read()
        except Exception:
            raise StorageError("Supabase Storage object read failed") from None
        finally:
            close = getattr(body, "close", None)
            if close is not None:
                try:
                    close()
                except (BotoCoreError, OSError):
                    pass

        content_type = response.get("ContentType")
        stored_metadata = response.get("Metadata", {})
        if content_type is not None and not isinstance(content_type, str):
            raise StorageError("Supabase Storage returned invalid content type metadata")
        if not isinstance(stored_metadata, dict) or any(
            not isinstance(name, str) or not isinstance(value, str) for name, value in stored_metadata.items()
        ):
            raise StorageError("Supabase Storage returned invalid object metadata")
        if not isinstance(content, bytes):
            raise StorageError("Supabase Storage returned an invalid object body")
        return StoredObject(key, content, content_type, dict(stored_metadata))

    def exists(self, object_key: str) -> bool:
        key = validate_object_key(object_key)
        try:
            self._call(
                "check object",
                "head_object",
                Bucket=self._bucket_name,
                Key=self._provider_key(key),
            )
        except ObjectNotFound:
            return False
        return True

    def delete(self, object_key: str) -> None:
        key = validate_object_key(object_key)
        try:
            self._call(
                "delete",
                "delete_object",
                Bucket=self._bucket_name,
                Key=self._provider_key(key),
            )
        except ObjectNotFound:
            return

    def _provider_key(self, object_key: str) -> str:
        return _SUPABASE_NAMESPACE + object_key

    def _call(self, operation: str, method: str, **request: object) -> dict:
        try:
            return getattr(self._client, method)(**request)
        except ClientError as exc:
            error = exc.response.get("Error", {})
            code = str(error.get("Code", ""))
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if code in {"NoSuchBucket", "BucketNotFound"}:
                raise StorageError("Supabase Storage bucket is missing or unavailable") from None
            if code in {"NoSuchKey", "NotFound", "404"} or status_code == 404:
                raise ObjectNotFound("Supabase Storage object does not exist") from None
            if code in {
                "AccessDenied",
                "InvalidAccessKeyId",
                "SignatureDoesNotMatch",
                "InvalidToken",
                "ExpiredToken",
            } or status_code == 403:
                raise StorageError("Supabase Storage denied the request; check the server-side S3 credentials") from None
            raise StorageError(f"Supabase Storage {operation} failed") from None
        except (EndpointConnectionError, ConnectTimeoutError, ReadTimeoutError, HTTPClientError):
            raise StorageError(f"Supabase Storage provider unavailable during {operation}") from None
        except BotoCoreError:
            raise StorageError(f"Supabase Storage {operation} failed due to an SDK or credential error") from None
        except OSError:
            raise StorageError(f"Supabase Storage network or stream failure during {operation}") from None


def _validate_configuration(
    endpoint_url: str,
    region: str,
    bucket_name: str,
    access_key_id: str,
    secret_access_key: str,
) -> None:
    values = (endpoint_url, region, bucket_name, access_key_id, secret_access_key)
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise StorageConfigurationError(
            "Supabase Storage endpoint, region, bucket, and server-side S3 credentials are required"
        )
    endpoint = urlsplit(endpoint_url)
    if endpoint.scheme != "https" or not endpoint.hostname or endpoint.username or endpoint.password:
        raise StorageConfigurationError("Supabase Storage endpoint must be HTTPS without embedded credentials")
    if not endpoint.hostname.lower().endswith(".storage.supabase.co"):
        raise StorageConfigurationError("Supabase Storage endpoint must use the project's storage hostname")
    if endpoint.path.rstrip("/") != "/storage/v1/s3" or endpoint.query or endpoint.fragment:
        raise StorageConfigurationError("Supabase Storage endpoint must end with /storage/v1/s3")
    if not 1 <= len(bucket_name) <= 100 or bucket_name.strip() != bucket_name:
        raise StorageConfigurationError("Supabase Storage bucket name is invalid")
