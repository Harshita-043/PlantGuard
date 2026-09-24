"""
Test the API endpoints
"""
from fastapi.testclient import TestClient
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
    """Analysis cannot claim healthy when no inference service is integrated."""
    response = client.get("/api/v1/analyze/health")
    assert response.status_code == 503
    data = response.json()
    assert "no ML implementation is integrated" in data["detail"]


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
