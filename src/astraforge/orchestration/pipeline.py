"""End-to-end autonomous build pipeline."""

from dataclasses import dataclass
from pathlib import Path

from astraforge.agents.coder import CodingAgent
from astraforge.orchestration.engine import Orchestrator
from astraforge.orchestration.loop import BuildTestLoop, RepairAgent
from astraforge.projects.schemas import ProjectSpec, ProjectStatus
from astraforge.workspace.manager import WorkspaceManager
from astraforge.workspace.runner import CommandRunner


@dataclass(frozen=True)
class PipelineResult:
    project_id: str
    workspace: Path
    files: list[str]
    tests_passed: bool
    attempts: int


class PipelineRepairAgent(RepairAgent):
    def __init__(self, coder: CodingAgent, workspace: Path) -> None:
        self.coder = coder
        self.workspace = workspace

    async def repair(self, failure) -> None:
        instruction = (
            "Repair the project based on this test failure. Return the complete replacement "
            "contents for every file you change.\n\n"
            f"Command: {' '.join(failure.command)}\n"
            f"Exit code: {failure.return_code}\n"
            f"STDOUT:\n{failure.stdout}\nSTDERR:\n{failure.stderr}"
        )
        await self.coder.implement(self.workspace, instruction)


class AutonomousPipeline:
    def __init__(
        self,
        coder: CodingAgent,
        workspace_manager: WorkspaceManager,
        runner: CommandRunner,
        max_repairs: int = 3,
    ) -> None:
        self.coder = coder
        self.workspace_manager = workspace_manager
        self.runner = runner
        self.max_repairs = max_repairs

    async def run(self, project: ProjectSpec, command: list[str]) -> PipelineResult:
        project.status = ProjectStatus.BUILDING
        workspace = self.workspace_manager.create(project.id)

        plan = Orchestrator().create_plan(project)
        developer_task = next(task for task in plan.tasks if task.role.value == "developer")
        instruction = (
            f"Project: {project.name}\nDescription: {project.description}\n"
            f"Requirements: {project.requirements}\n"
            f"Implementation task: {developer_task.instruction}\n"
            "Generate a complete runnable project in the workspace."
        )
        files = await self.coder.implement(workspace, instruction)

        project.status = ProjectStatus.TESTING
        loop = BuildTestLoop(self.runner, self.max_repairs)
        result = await loop.run(
            workspace,
            command,
            PipelineRepairAgent(self.coder, workspace),
        )
        project.status = ProjectStatus.COMPLETED if result.passed else ProjectStatus.FAILED
        return PipelineResult(project.id, workspace, files, result.passed, result.attempts)
