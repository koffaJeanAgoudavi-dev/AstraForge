import json

import pytest

from astraforge.agents.coder import CodingAgent
from astraforge.orchestration.pipeline import AutonomousPipeline
from astraforge.projects.schemas import ProjectSpec, ProjectStatus
from astraforge.providers.base import ModelRequest, ModelResponse
from astraforge.providers.router import ModelRouter
from astraforge.workspace.manager import WorkspaceManager
from astraforge.workspace.runner import DockerCommandRunner


class FakeRouter:
    """Deterministic model router for the pipeline smoke test."""

    async def generate(self, request: ModelRequest, role: str = "general") -> ModelResponse:
        if "Architect" in (request.system_prompt or ""):
            text = json.dumps(
                {
                    "plan": "Build a tiny Python package with a unit test.",
                    "files": ["calculator.py", "test_calculator.py"],
                }
            )
        elif "Developer" in (request.system_prompt or ""):
            text = json.dumps(
                {
                    "files": [
                        {
                            "path": "calculator.py",
                            "content": "def add(a: int, b: int) -> int:\n    return a + b\n",
                        },
                        {
                            "path": "test_calculator.py",
                            "content": "from calculator import add\n\n\ndef test_add() -> None:\n    assert add(2, 3) == 5\n",
                        },
                    ]
                }
            )
        elif "Tester" in (request.system_prompt or ""):
            text = "No additional findings."
        elif "Reviewer" in (request.system_prompt or ""):
            text = "No blocking findings."
        else:
            text = "OK"
        return ModelResponse(text=text, provider="fake", model="smoke-test")


class FakeRouterAdapter(ModelRouter):
    """ModelRouter-compatible wrapper around the deterministic fake."""

    def __init__(self) -> None:
        self.fake = FakeRouter()

    async def generate(self, request: ModelRequest, role: str = "general") -> ModelResponse:
        return await self.fake.generate(request, role)


@pytest.mark.e2e
@pytest.mark.skipif(
    not __import__("shutil").which("docker"),
    reason="Docker is required for the sandbox E2E test",
)
async def test_pipeline_builds_and_tests_generated_project(tmp_path):
    router = FakeRouterAdapter()
    workspace_manager = WorkspaceManager(tmp_path / "workspaces")
    coder = CodingAgent(router, workspace_manager)

    pipeline = AutonomousPipeline(
        coder,
        workspace_manager,
        DockerCommandRunner(image="astraforge-sandbox:latest"),
        state_store=None,
    )

    project = ProjectSpec(
        name="AstraForge smoke app",
        description="A minimal generated Python application used to validate the build pipeline.",
        requirements=["Provide an add function.", "Include a passing unit test."],
    )

    result = await pipeline.run(project, ["pytest", "-q"], resume=False)

    assert result.tests_passed is True
    assert result.attempts >= 1
    assert project.status == ProjectStatus.COMPLETED
    assert set(result.files) == {"calculator.py", "test_calculator.py"}
