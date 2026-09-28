from fastapi.testclient import TestClient

from astraforge.main import app


def test_control_center_is_available():
    client = TestClient(app)
    response = client.get("/projects/control")
    assert response.status_code == 200
    assert "AstraForge" in response.text


def test_project_events_websocket():
    client = TestClient(app)
    with client.websocket_connect("/projects/test-project/events"):
        pass
