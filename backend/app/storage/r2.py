"""Cloudflare R2 adapter using its S3-compatible API."""

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


_R2_NAMESPACE = "plantguard/"
_R2_REGION = "auto"


class CloudflareR2ObjectStorage:
    """S3-compatible object operations scoped to one private R2 bucket."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        bucket_name: str,
        access_key_id: str,
        secret_access_key: str,
        s3_client: BaseClient | None = None,
    ):
        _validate_configuration(endpoint_url, bucket_name, access_key_id, secret_access_key)
        self._bucket_name = bucket_name
        if s3_client is None:
            try:
                s3_client = boto3.client(
                    "s3",
                    endpoint_url=endpoint_url,
                    region_name=_R2_REGION,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    config=Config(
                        connect_timeout=3,
                        read_timeout=20,
                        retries={"max_attempts": 2, "mode": "standard"},
                        signature_version="s3v4",
                    ),
                )
            except BotoCoreError:
                raise StorageConfigurationError("Could not initialize the R2 S3 client") from None
        self._client = s3_client

    def check_ready(self) -> bool:
        """Probe bucket access using a read-only S3 HEAD request."""
        self._call("readiness", "head_bucket", Bucket=self._bucket_name)
        return True
    def create_download_url(self, object_key: str, *, expires_in: int = 300) -> str:
        """Generate a short-lived HTTPS GET URL for this private object."""
        if not isinstance(expires_in, int) or isinstance(expires_in, bool) or not 60 <= expires_in <= 900:
            raise ValueError("Signed URL expiration must be between 60 and 900 seconds")
        key = validate_object_key(object_key)
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket_name, "Key": self._provider_key(key)},
                ExpiresIn=expires_in,
                HttpMethod="GET",
            )
        except (BotoCoreError, ValueError):
            raise StorageError("Could not create a temporary object download link") from None
        endpoint = urlsplit(url) if isinstance(url, str) else None
        if endpoint is None or endpoint.scheme != "https" or not endpoint.hostname:
            raise StorageError("Storage provider returned an invalid temporary download link")
        return url
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
            raise StorageError("R2 read returned an invalid object body")
        try:
            content = body.read()
        except Exception:
            raise StorageError("R2 object read failed") from None
        finally:
            close = getattr(body, "close", None)
            if close is not None:
                try:
                    close()
                except (BotoCoreError, OSError):
                    pass

        content_type = response.get("ContentType")
        metadata = response.get("Metadata", {})
        if content_type is not None and not isinstance(content_type, str):
            raise StorageError("R2 returned invalid object content type metadata")
        if not isinstance(metadata, dict) or any(
            not isinstance(name, str) or not isinstance(value, str) for name, value in metadata.items()
        ):
            raise StorageError("R2 returned invalid object metadata")
        if not isinstance(content, bytes):
            raise StorageError("R2 returned an invalid object body")
        return StoredObject(key, content, content_type, dict(metadata))

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
        return _R2_NAMESPACE + object_key

    def _call(self, operation: str, method: str, **request: object) -> dict:
        try:
            return getattr(self._client, method)(**request)
        except ClientError as exc:
            error = exc.response.get("Error", {})
            code = str(error.get("Code", ""))
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if code in {"NoSuchBucket", "BucketNotFound"}:
                raise StorageError("R2 bucket is missing or unavailable") from None
            if code in {"NoSuchKey", "NotFound", "404"} or status_code == 404:
                raise ObjectNotFound("R2 object does not exist") from None
            if code in {
                "AccessDenied",
                "InvalidAccessKeyId",
                "SignatureDoesNotMatch",
                "InvalidToken",
                "ExpiredToken",
            } or status_code == 403:
                raise StorageError("R2 denied the request; check the bucket-scoped credentials and permissions") from None
            raise StorageError(f"R2 {operation} failed") from None
        except (EndpointConnectionError, ConnectTimeoutError, ReadTimeoutError, HTTPClientError):
            raise StorageError(f"R2 provider unavailable during {operation}") from None
        except BotoCoreError:
            raise StorageError(f"R2 {operation} failed due to an SDK or credential error") from None
        except OSError:
            raise StorageError(f"R2 network or stream failure during {operation}") from None


def _validate_configuration(endpoint_url: str, bucket_name: str, access_key_id: str, secret_access_key: str) -> None:
    values = (endpoint_url, bucket_name, access_key_id, secret_access_key)
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise StorageConfigurationError("R2 endpoint, bucket, and backend credentials are required")
    endpoint = urlsplit(endpoint_url)
    if endpoint.scheme != "https" or not endpoint.hostname or endpoint.username or endpoint.password:
        raise StorageConfigurationError("R2 endpoint must be an HTTPS URL without embedded credentials")
    if not endpoint.hostname.lower().endswith(".r2.cloudflarestorage.com"):
        raise StorageConfigurationError("R2 endpoint must use the Cloudflare R2 S3 API hostname")
    if endpoint.path not in {"", "/"} or endpoint.query or endpoint.fragment:
        raise StorageConfigurationError("R2 endpoint must be a base endpoint URL")
    if not 3 <= len(bucket_name) <= 63 or not all(char.islower() or char.isdigit() or char == "-" for char in bucket_name):
        raise StorageConfigurationError("R2 bucket name must use lowercase letters, digits, or hyphens")
    if bucket_name.startswith("-") or bucket_name.endswith("-"):
        raise StorageConfigurationError("R2 bucket name cannot start or end with a hyphen")
