from fastapi import FastAPI
from fastapi.testclient import TestClient

from astraforge import api
from astraforge.projects.schemas import ProjectSpec
from astraforge.state.store import StateStore
from astraforge.workspace.manager import WorkspaceManager


def make_app(state_store):
    app = FastAPI()
    app.include_router(api.router)
    api.state_store = state_store
    return app


def test_project_lifecycle_and_file_endpoints(tmp_path, monkeypatch):
    store = StateStore(tmp_path / "state.db")
    workspace_root = tmp_path / "workspaces"

    class TempWorkspaceManager(WorkspaceManager):
        def __init__(self, root=workspace_root):
            super().__init__(root)

    monkeypatch.setattr(api, "WorkspaceManager", TempWorkspaceManager)
    app = make_app(store)

    project = {"name": "Demo", "description": "Build a demo", "requirements": ["FastAPI"]}
    with TestClient(app) as client:
        created = client.post("/projects", json=project)
        assert created.status_code == 200
        project_id = created.json()["project"]["id"]

        queued = client.post(f"/projects/{project_id}/build")
        assert queued.status_code == 200
        run_id = queued.json()["run_id"]

        workspace = TempWorkspaceManager().create_project_workspace(project_id)
        TempWorkspaceManager().write_file(workspace, "src/app.py", "print('ok')")

        files = client.get(f"/projects/{project_id}/files")
        assert files.status_code == 200
        assert files.json()["files"] == ["src/app.py"]

        source = client.get(f"/projects/{project_id}/files", params={"path": "src/app.py"})
        assert source.status_code == 200
        assert source.json()["content"] == "print('ok')"

        store.update_run(
            run_id,
            stage="testing",
            status="running",
            context={"test_results": [{"passed": True, "attempts": 0}], "tester_findings": []},
        )
        tests = client.get(f"/projects/{project_id}/tests")
        assert tests.status_code == 200
        assert tests.json()["tests"][0]["passed"] is True

        status = client.get(f"/projects/{project_id}")
        assert status.status_code == 200
        assert status.json()["latest_run"]["id"] == run_id
        assert "worker_id" not in status.json()["latest_run"]
        assert "context" not in status.json()["latest_run"]


def test_build_rejects_deployment_without_publish(tmp_path):
    store = StateStore(tmp_path / "state.db")
    app = make_app(store)
    project = ProjectSpec(name="Demo", description="Build a demo")
    store.save_project(project)

    with TestClient(app) as client:
        response = client.post(f"/projects/{project.id}/build?deploy=true")
        assert response.status_code == 400
        assert response.json()["detail"] == "Deployment requires publish=true"
