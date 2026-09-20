from fastapi.testclient import TestClient
from app.main import app
from app.services.syslog.manager import syslog_manager

client = TestClient(app)


def test_get_syslog_status(client):
    response = client.get("/api/v1/syslog/status")
    assert response.status_code == 200
    data = response.json()
    assert "manager_running" in data
    assert "udp" in data
    assert "tcp" in data
    assert "tls" in data
    assert "queue" in data
    assert "metrics" in data


def test_syslog_metrics_reset(client):
    response = client.post("/api/v1/syslog/metrics/reset")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Syslog metrics reset successfully."
    assert data["metrics"]["messages_received"] == 0
