"""Focused tests for temporary image upload validation and cleanup."""
import asyncio
import io
import tempfile

import pytest
from fastapi import HTTPException
from fastapi.datastructures import UploadFile
from PIL import Image

from app.api.v1 import analyze


def _png_bytes() -> bytes:
    image = Image.new("RGB", (2, 2), color=(10, 20, 30))
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def _upload(data: bytes, *, content_type: str = "image/png", filename: str = "leaf.png") -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(data), headers={"content-type": content_type})


def _use_temp_root(monkeypatch, tmp_path):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))


class _SuccessfulService:
    def analyze_image(self, **kwargs):
        return {"accepted": True}


def test_valid_image_is_processed_and_temporary_files_are_removed(monkeypatch, tmp_path):
    _use_temp_root(monkeypatch, tmp_path)
    monkeypatch.setattr(analyze, "create_plant_analysis_service", lambda: _SuccessfulService())

    result = asyncio.run(analyze.analyze_image(_upload(_png_bytes())))

    assert result == {"accepted": True}
    assert list(tmp_path.iterdir()) == []


def test_unsupported_declared_mime_is_rejected_without_temp_files(monkeypatch, tmp_path):
    _use_temp_root(monkeypatch, tmp_path)

    with pytest.raises(HTTPException) as error:
        asyncio.run(analyze.analyze_image(_upload(_png_bytes(), content_type="image/gif")))

    assert error.value.status_code == 415
    assert list(tmp_path.iterdir()) == []


def test_malformed_image_is_rejected_and_cleaned_up(monkeypatch, tmp_path):
    _use_temp_root(monkeypatch, tmp_path)

    with pytest.raises(HTTPException) as error:
        asyncio.run(analyze.analyze_image(_upload(b"not an image")))

    assert error.value.status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_oversized_image_is_rejected_and_cleaned_up(monkeypatch, tmp_path):
    _use_temp_root(monkeypatch, tmp_path)

    with pytest.raises(HTTPException) as error:
        asyncio.run(analyze.analyze_image(_upload(b"x" * (analyze.MAX_IMAGE_BYTES + 1))))

    assert error.value.status_code == 413
    assert list(tmp_path.iterdir()) == []


def test_unsafe_client_filename_is_ignored(monkeypatch, tmp_path):
    _use_temp_root(monkeypatch, tmp_path)
    monkeypatch.setattr(analyze, "create_plant_analysis_service", lambda: _SuccessfulService())

    result = asyncio.run(analyze.analyze_image(_upload(_png_bytes(), filename="../../outside.png")))

    assert result == {"accepted": True}
    assert list(tmp_path.iterdir()) == []


def test_missing_upload_is_rejected():
    with pytest.raises(HTTPException) as error:
        asyncio.run(analyze.analyze_image(None))

    assert error.value.status_code == 400


def test_analysis_unavailable_still_cleans_temporary_upload(monkeypatch, tmp_path):
    _use_temp_root(monkeypatch, tmp_path)

    with pytest.raises(HTTPException) as error:
        asyncio.run(analyze.analyze_image(_upload(_png_bytes())))

    assert error.value.status_code == 503
    assert list(tmp_path.iterdir()) == []


def test_analysis_failure_cleans_temporary_upload(monkeypatch, tmp_path):
    _use_temp_root(monkeypatch, tmp_path)

    class FailingService:
        def analyze_image(self, **kwargs):
            raise RuntimeError("processing failed")

    monkeypatch.setattr(analyze, "create_plant_analysis_service", lambda: FailingService())
    with pytest.raises(HTTPException) as error:
        asyncio.run(analyze.analyze_image(_upload(_png_bytes())))

    assert error.value.status_code == 500
    assert list(tmp_path.iterdir()) == []


def test_unexpected_service_initialization_error_cleans_temporary_upload(monkeypatch, tmp_path):
    _use_temp_root(monkeypatch, tmp_path)

    def fail_initialization():
        raise RuntimeError("unexpected initialization error")

    monkeypatch.setattr(analyze, "create_plant_analysis_service", fail_initialization)
    with pytest.raises(HTTPException) as error:
        asyncio.run(analyze.analyze_image(_upload(_png_bytes())))

    assert error.value.status_code == 500
    assert list(tmp_path.iterdir()) == []


def test_declared_type_must_match_image_content_and_file_is_cleaned(monkeypatch, tmp_path):
    _use_temp_root(monkeypatch, tmp_path)

    with pytest.raises(HTTPException) as error:
        asyncio.run(analyze.analyze_image(_upload(_png_bytes(), content_type="image/jpeg")))

    assert error.value.status_code == 415
    assert list(tmp_path.iterdir()) == []
