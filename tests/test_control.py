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


def test_build_returns_immediately_with_run_id(monkeypatch):
    from astraforge.api import state_store

    async def fake_background(project, run_id, publish, deploy):
        return None

    monkeypatch.setattr("astraforge.api._run_pipeline_in_background", fake_background)
    client = TestClient(app)
    response = client.post(
        "/projects/build",
        json={
            "id": "async-test-project",
            "name": "Async test",
            "description": "test",
            "requirements": [],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "started"
    assert payload["run_id"] == state_store.get_latest_run("async-test-project")["id"]
