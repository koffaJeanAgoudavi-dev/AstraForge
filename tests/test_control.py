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


def test_build_is_persisted_as_queued_work(monkeypatch):
    from astraforge.api import job_manager, state_store

    monkeypatch.setattr(job_manager, "start", lambda: None)
    monkeypatch.setattr(job_manager, "stop", lambda: _noop())
    client = TestClient(app)
    response = client.post(
        "/projects/build",
        json={
            "id": "queued-test-project",
            "name": "Queued test",
            "description": "test",
            "requirements": [],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["run_id"] == state_store.get_latest_run("queued-test-project")["id"]
    assert state_store.get_run(payload["run_id"])["status"] == "queued"


async def _noop():
    return None
