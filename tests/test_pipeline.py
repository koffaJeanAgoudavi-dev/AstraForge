import json

import pytest

from astraforge.orchestration.pipeline import AutonomousPipeline
from astraforge.providers.base import ModelResponse
from astraforge.projects.schemas import ProjectSpec
from astraforge.state.store import StateStore
from astraforge.workspace.manager import WorkspaceManager
from astraforge.workspace.runner import CommandRunner


class FakeRouter:
    async def generate(self, request, role="general"):
        if role == "architect":
            return ModelResponse(
                text=json.dumps({"plan": "pytest project", "files": ["test_ok.py"]}),
                provider="fake",
                model="fake",
            )
        if role == "tester":
            return ModelResponse(text="No test issues.", provider="fake", model="fake")
        if role == "reviewer":
            return ModelResponse(text="No review issues.", provider="fake", model="fake")
        return ModelResponse(text="{}", provider="fake", model="fake")


class FakeCoder:
    def __init__(self):
        self.router = FakeRouter()

    async def implement(self, workspace, instruction):
        (workspace / "test_ok.py").write_text("def test_ok(): assert True", encoding="utf-8")
        return ["test_ok.py"]


@pytest.mark.asyncio
async def test_pipeline_builds_and_tests(tmp_path):
    manager = WorkspaceManager(tmp_path)
    store = StateStore(tmp_path / "state.db")
    pipeline = AutonomousPipeline(
        FakeCoder(), manager, CommandRunner(), max_repairs=0, state_store=store
    )
    project = ProjectSpec(name="demo", description="demo")
    result = await pipeline.run(project, ["python", "-m", "pytest", "-q"])
    assert result.tests_passed is True
    assert result.resumed is False
    assert project.status.value == "completed"
    assert store.get_latest_run(project.id)["status"] == "completed"
    stages = [event["stage"] for event in store.list_events(project.id)]
    assert "developer.started" in stages
    assert "developer.completed" in stages
    assert "tester.started" in stages
    assert "tester.completed" in stages
    assert "tester.assessed" in stages
    assert "reviewer.started" in stages
    assert "reviewer.assessed" in stages
    assert stages[-1] == "completed"


@pytest.mark.asyncio
async def test_pipeline_resumes_existing_workspace(tmp_path):
    manager = WorkspaceManager(tmp_path)
    store = StateStore(tmp_path / "state.db")
    project = ProjectSpec(name="resume-demo", description="demo")
    store.save_project(project)
    store.start_run(project.id, ["python", "-m", "pytest", "-q"], stage="testing")
    workspace = manager.create_project_workspace(project.id)
    (workspace / "test_ok.py").write_text(
        "def test_ok(): assert True", encoding="utf-8"
    )

    pipeline = AutonomousPipeline(
        FakeCoder(), manager, CommandRunner(), max_repairs=0, state_store=store
    )
    result = await pipeline.run(project, ["python", "-m", "pytest", "-q"])
    assert result.resumed is True
    assert result.tests_passed is True
    assert project.status.value == "completed"
