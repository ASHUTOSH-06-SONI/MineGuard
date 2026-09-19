from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_worker_endpoint():
    response = client.get("/api/workers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    assert data[0]["name"]


def test_alerts_and_history_endpoints():
    alerts = client.get("/api/alerts/active")
    topology = client.get("/api/mine/topology")
    history = client.get("/api/history")

    assert alerts.status_code == 200
    assert topology.status_code == 200
    assert history.status_code == 200
    assert len(alerts.json()) >= 1
    assert len(topology.json()["tunnels"]) >= 1
    assert len(history.json()) >= 1


def test_websocket_stream():
    with client.websocket_connect("/ws/dashboard") as websocket:
        message = websocket.receive_json()
        assert message["type"] == "telemetry"
        assert "workers" in message
        assert len(message["workers"]) == 5
