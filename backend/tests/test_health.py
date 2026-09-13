import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check_status():
    """
    Test GET /api/v1/health returns 200 OK with expected JSON structure.
    Expected response:
    {
      "status": "ok",
      "service": "ULPF",
      "version": "1.0.0"
    }
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ULPF"
    assert data["version"] == "1.0.0"


def test_root_endpoint():
    """
    Test GET / returns framework metadata and health endpoint path.
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Universal Log Pre-processing Framework" in data["framework"]
    assert data["health_endpoint"] == "/api/v1/health"
