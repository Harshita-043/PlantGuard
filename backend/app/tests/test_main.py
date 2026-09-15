"""
Basic tests for the backend API
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ping():
    """Test the ping endpoint"""
    response = client.get("/api/ping")
    assert response.status_code == 200
    assert response.json()["message"] == "pong"


def test_demo():
    """Test the demo endpoint"""
    response = client.get("/api/demo")
    assert response.status_code == 200
    assert response.json()["message"] == "Hello from PlantGuard AI Backend"


def test_root():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data