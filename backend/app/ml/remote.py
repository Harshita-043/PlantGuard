"""Opt-in authenticated HTTPS client for a remote PlantGuard inference service."""

from __future__ import annotations

import io
import json
import logging
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

import numpy as np
from PIL import Image

from app.core.config import settings
from app.ml.errors import InferenceErrorCode, InferenceTimeoutError, InvalidImageError, ModelCapabilityError
from app.schemas.inference import FullScanResult

logger = logging.getLogger(__name__)
MAX_REMOTE_RESPONSE_BYTES = 2 * 1024 * 1024


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_HTTPS_OPENER = build_opener(_NoRedirectHandler())


def _open_https(request: Request, timeout: float):
    return _HTTPS_OPENER.open(request, timeout=timeout)


def validate_remote_base_url(value: str) -> str:
    parsed = urlparse(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
        raise ValueError("Remote inference URL must be an HTTPS origin without credentials, path, query, or fragment")
    return value.rstrip("/")


class RemoteInferenceClient:
    """Send image data only when explicitly configured and invoked by the caller."""

    def __init__(self, *, base_url: str, token: str, max_image_bytes: int = 10 * 1024 * 1024,
                 timeout_seconds: float = 60, max_concurrency: int = 1,
                 deployment_authorized: bool = False):
        self.base_url = validate_remote_base_url(base_url)
        if not token:
            raise ModelCapabilityError(InferenceErrorCode.UNSUPPORTED_RUNTIME,
                                       "Remote inference requires an explicit bearer token", stage="remote")
        if not deployment_authorized:
            raise ModelCapabilityError(InferenceErrorCode.UNSUPPORTED_RUNTIME,
                                       "Remote image processing requires explicit deployment authorization", stage="remote")
        self._token = token
        self.max_image_bytes = max_image_bytes
        self.timeout_seconds = timeout_seconds
        self._slots = threading.BoundedSemaphore(max_concurrency)

    @classmethod
    def from_settings(cls) -> "RemoteInferenceClient":
        url = settings.PLANTGUARD_REMOTE_INFERENCE_URL
        token = settings.PLANTGUARD_REMOTE_INFERENCE_TOKEN
        if not url or token is None:
            raise ModelCapabilityError(InferenceErrorCode.UNSUPPORTED_RUNTIME,
                                       "Remote inference profile requires a configured HTTPS URL and token", stage="remote")
        try:
            return cls(base_url=url, token=token.get_secret_value(),
                       max_image_bytes=settings.PLANTGUARD_REMOTE_MAX_IMAGE_BYTES,
                       timeout_seconds=settings.PLANTGUARD_REMOTE_TIMEOUT_SECONDS,
                       max_concurrency=settings.PLANTGUARD_REMOTE_MAX_CONCURRENCY,
                       deployment_authorized=settings.PLANTGUARD_REMOTE_IMAGE_UPLOAD_AUTHORIZED)
        except ValueError as exc:
            raise ModelCapabilityError(InferenceErrorCode.UNSUPPORTED_RUNTIME,
                                       "Remote inference configuration is invalid", stage="remote") from exc

    def analyze(self, image: np.ndarray, *, analysis_id: str | None = None) -> FullScanResult:
        if (not isinstance(image, np.ndarray) or image.ndim != 3 or image.shape[2] != 3
                or image.dtype != np.uint8 or image.size == 0
                or image.shape[0] > 8192 or image.shape[1] > 8192 or image.shape[0] * image.shape[1] > 32_000_000):
            raise InvalidImageError("Remote inference expects a non-empty RGB uint8 image")
        encoded = io.BytesIO()
        Image.fromarray(image, mode="RGB").save(encoded, format="PNG", optimize=True)
        payload = encoded.getvalue()
        if len(payload) > self.max_image_bytes:
            raise InvalidImageError("Encoded image exceeds the configured remote request size limit")
        request = Request(
            f"{self.base_url}/v1/inference",
            data=payload,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "image/png",
                "Accept": "application/json",
                "Content-Length": str(len(payload)),
                **({"X-Analysis-ID": analysis_id} if analysis_id else {}),
            },
            method="POST",
        )
        if not self._slots.acquire(timeout=self.timeout_seconds):
            raise InferenceTimeoutError("Remote inference concurrency slot timed out")
        try:
            with _open_https(request, timeout=self.timeout_seconds) as response:
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_REMOTE_RESPONSE_BYTES:
                    raise ModelCapabilityError(InferenceErrorCode.REMOTE_FAILURE,
                                               "Remote inference response exceeded size limit", stage="remote")
                body = response.read(MAX_REMOTE_RESPONSE_BYTES + 1)
                if len(body) > MAX_REMOTE_RESPONSE_BYTES:
                    raise ModelCapabilityError(InferenceErrorCode.REMOTE_FAILURE,
                                               "Remote inference response exceeded size limit", stage="remote")
            result = FullScanResult.model_validate_json(body)
            logger.info("remote_inference_complete runtime=remote model=%s status=%s",
                        result.model_versions, result.status)
            return result
        except HTTPError as exc:
            if exc.code in (408, 504):
                raise InferenceTimeoutError("Remote inference endpoint timed out") from exc
            raise ModelCapabilityError(InferenceErrorCode.REMOTE_FAILURE,
                                       f"Remote inference endpoint returned HTTP {exc.code}", stage="remote") from exc
        except (TimeoutError, URLError) as exc:
            if isinstance(exc, TimeoutError) or isinstance(getattr(exc, "reason", None), TimeoutError):
                raise InferenceTimeoutError("Remote inference request timed out") from exc
            raise ModelCapabilityError(InferenceErrorCode.REMOTE_FAILURE,
                                       "Remote inference endpoint is unavailable", stage="remote") from exc
        except (ValueError, json.JSONDecodeError) as exc:
            raise ModelCapabilityError(InferenceErrorCode.REMOTE_FAILURE,
                                       "Remote inference response did not match the result contract", stage="remote") from exc
        finally:
            self._slots.release()

    def analyze_bytes(self, image_bytes: bytes, *, analysis_id: str | None = None) -> FullScanResult:
        """Decode validated upload bytes then send through the explicitly enabled remote profile."""
        try:
            with Image.open(io.BytesIO(image_bytes)) as source:
                image = np.asarray(source.convert("RGB"), dtype=np.uint8)
        except (OSError, ValueError) as exc:
            raise InvalidImageError("Remote inference could not decode the uploaded image") from exc
        return self.analyze(image, analysis_id=analysis_id)


def probe_remote_health(base_url: str, token: str, timeout_seconds: float = 2.0) -> str:
    """Authenticated bounded GET to the configured service's /health endpoint."""
    try:
        base = validate_remote_base_url(base_url)
        request = Request(f"{base}/health", headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        with _open_https(request, timeout=min(max(timeout_seconds, 0.2), 3.0)) as response:
            response.read(4096)
        return "available" if 200 <= response.status < 300 else "unavailable"
    except HTTPError as exc:
        return "unauthorized" if exc.code in (401, 403) else "unavailable"
    except (OSError, ValueError, TimeoutError, URLError):
        return "unavailable"
