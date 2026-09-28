import pytest

from astraforge.orchestration.pipeline import AutonomousPipeline
from astraforge.projects.schemas import ProjectSpec
from astraforge.workspace.manager import WorkspaceManager
from astraforge.workspace.runner import CommandRunner


class FakeCoder:
    async def implement(self, workspace, instruction):
        (workspace / "test_ok.py").write_text("def test_ok(): assert True")
        return ["test_ok.py"]


@pytest.mark.asyncio
async def test_pipeline_builds_and_tests(tmp_path):
    manager = WorkspaceManager(tmp_path)
    pipeline = AutonomousPipeline(FakeCoder(), manager, CommandRunner(), max_repairs=0)
    project = ProjectSpec(name="demo", description="demo")
    result = await pipeline.run(project, ["python", "-m", "pytest", "-q"])
    assert result.tests_passed is True
    assert project.status.value == "completed"
