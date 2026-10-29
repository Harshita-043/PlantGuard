"""Opt-in real-model authenticated scan persistence test using isolated local resources."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from app.api.v1 import analyze
from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.storage import LocalFileObjectStorage


@pytest.mark.skipif(
    os.getenv("PLANTGUARD_RUN_REAL_MODEL_TESTS") != "1",
    reason="Requires explicit real-model inference opt-in and original checkpoints",
)
def test_real_authenticated_scan_persists_across_database_reconnect(
    monkeypatch, tmp_path
):
    repository_root = Path(__file__).resolve().parents[3]
    image_path = repository_root / "IMAGE_APP.jpg"
    image_bytes = image_path.read_bytes()
    database_path = tmp_path / "plantguard-real-lifecycle.sqlite"
    storage = LocalFileObjectStorage(tmp_path / "private-objects")

    monkeypatch.setattr(
        settings,
        "JWT_SECRET_KEY",
        SecretStr("isolated-real-model-test-secret-" + "x" * 32),
    )
    monkeypatch.setattr(settings, "PLANTGUARD_INFERENCE_PROFILE", "cpu")
    monkeypatch.setattr(analyze, "create_object_storage", lambda: storage)

    resource = {}

    def open_database():
        engine = create_engine(
            URL.create("sqlite", database=str(database_path)),
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(engine)
        resource["engine"] = engine
        resource["sessions"] = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
        )

    def override_get_db():
        with resource["sessions"]() as session:
            yield session

    open_database()
    app.dependency_overrides[get_db] = override_get_db

    try:
        email = f"real-lifecycle-{uuid4().hex}@example.com"
        password = "isolated test password that is long enough"
        with TestClient(app) as client:
            registration = client.post(
                "/api/v1/auth/register",
                json={"email": email, "password": password},
            )
            assert registration.status_code == 201

            login = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            assert login.status_code == 200
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            upload = client.post(
                "/api/v1/analyze/image",
                headers=headers,
                files={"file": ("IMAGE_APP.jpg", image_bytes, "image/jpeg")},
            )
            assert upload.status_code == 201, upload.text
            saved = upload.json()
            assert saved["status"] == "completed"
            assert saved["result_available"] is True
            assert saved["result"]["analysis_id"] == saved["analysis_id"]
            assert saved["failure"] is None

            analysis_id = saved["analysis_id"]
            assets_response = client.get(
                f"/api/v1/analysis/{analysis_id}/assets",
                headers=headers,
            )
            assert assets_response.status_code == 200
            assets = assets_response.json()["assets"]
            original = next(asset for asset in assets if asset["kind"] == "original")
            artifact = next(asset for asset in assets if asset["kind"] == "artifact")

            original_response = client.get(original["download_url"], headers=headers)
            assert original_response.status_code == 200
            assert original_response.content == image_bytes

            artifact_response = client.get(artifact["download_url"], headers=headers)
            assert artifact_response.status_code == 200
            assert artifact_response.content

            history = client.get("/api/v1/analyses", headers=headers)
            assert history.status_code == 200
            assert any(row["analysis_id"] == analysis_id for row in history.json())

        resource["engine"].dispose()
        open_database()
        with TestClient(app) as restarted_client:
            retrieved = restarted_client.get(
                f"/api/v1/analysis/{analysis_id}",
                headers=headers,
            )
            assert retrieved.status_code == 200
            persisted = retrieved.json()
            assert persisted["status"] == "completed"
            assert persisted["result"] == saved["result"]
            assert persisted["analysis_id"] == analysis_id

            after_reconnect_assets = restarted_client.get(
                f"/api/v1/analysis/{analysis_id}/assets",
                headers=headers,
            )
            assert after_reconnect_assets.status_code == 200
            assert len(after_reconnect_assets.json()["assets"]) == len(assets)
    finally:
        app.dependency_overrides.pop(get_db, None)
        if "engine" in resource:
            resource["engine"].dispose()
