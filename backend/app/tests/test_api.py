"""
Test the API endpoints
"""
from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.api.v1 import analyze
from app.main import app

client = TestClient(app)


def test_ping_endpoint():
    """Test the legacy ping endpoint"""
    response = client.get("/api/ping")
    assert response.status_code == 200
    assert response.json()["message"] == "pong"


def test_demo_endpoint():
    """Test the legacy demo endpoint"""
    response = client.get("/api/demo")
    assert response.status_code == 200
    assert response.json()["message"] == "Hello from PlantGuard AI Backend"


def test_analysis_health_endpoint():
    """Analysis health does not claim model readiness when prerequisites are absent."""
    response = client.get("/api/v1/analyze/health")
    assert response.status_code == 503
    data = response.json()
    assert data["detail"] == {
        "status": "unavailable",
        "inference_available": False,
        "code": "model_prerequisites_unavailable",
        "message": "Configured model artifacts or runtime are unavailable",
    }


def test_analysis_health_never_equates_prerequisites_with_verified_inference(monkeypatch):
    monkeypatch.setattr(analyze, "create_plant_analysis_service",
                        lambda: SimpleNamespace(is_ready=lambda: True))
    response = client.get("/api/v1/analyze/health")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "status": "unverified",
        "inference_available": False,
        "code": "model_validation_required",
        "message": "Model prerequisites are present, but checkpoint integrity and real inference have not been verified",
    }


def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data


if __name__ == "__main__":
    test_ping_endpoint()
    test_demo_endpoint()
    test_analysis_health_endpoint()
    test_root_endpoint()
    print("All API tests passed!")
