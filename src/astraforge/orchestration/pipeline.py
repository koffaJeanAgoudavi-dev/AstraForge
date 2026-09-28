"""Autonomous build, test, review and delivery pipeline."""

from dataclasses import dataclass
from pathlib import Path

from astraforge.agents.coder import CodingAgent
from astraforge.agents.reviewer import ReviewerAgent
from astraforge.agents.roles import ArchitectAgent, TesterAgent, ReviewerAgentV2
from astraforge.integrations.github import GitHubAdapter, PullRequestInfo
from astraforge.orchestration.engine import Orchestrator
from astraforge.projects.schemas import ProjectSpec, ProjectStatus
from astraforge.state.store import StateStore
from astraforge.workspace.manager import WorkspaceManager
from astraforge.workspace.runner import CommandRunner


@dataclass(frozen=True)
class PipelineResult:
    project_id: str
    workspace: Path
    files: list[str]
    tests_passed: bool
    attempts: int
    pull_request: PullRequestInfo | None = None
    resumed: bool = False


class AutonomousPipeline:
    def __init__(
        self,
        coder: CodingAgent,
        workspace_manager: WorkspaceManager,
        runner: CommandRunner,
        github: GitHubAdapter | None = None,
        reviewer: ReviewerAgent | None = None,
        max_repairs: int = 3,
        max_review_repairs: int = 2,
        state_store: StateStore | None = None,
    ) -> None:
        self.coder = coder
        self.workspace_manager = workspace_manager
        self.runner = runner
        self.github = github
        self.reviewer = reviewer
        self.max_repairs = max_repairs
        self.max_review_repairs = max_review_repairs
        self.state_store = state_store
        self.architect = ArchitectAgent(coder.router)
        self.tester = TesterAgent(coder.router)
        self.context_reviewer = ReviewerAgentV2(coder.router)
        self.orchestrator = Orchestrator()

    def _existing_files(self, workspace: Path) -> list[str]:
        return sorted(
            str(path.relative_to(workspace))
            for path in workspace.rglob("*")
            if path.is_file()
        )

    async def run(
        self,
        project: ProjectSpec,
        command: list[str],
        resume: bool = True,
    ) -> PipelineResult:
        self.state_store and self.state_store.save_project(project)

        resumable = (
            self.state_store.find_resumable_run(project.id)
            if self.state_store and resume
            else None
        )
        resumed = resumable is not None

        if resumable:
            run_id = resumable["id"]
            workspace = self.workspace_manager.create_project_workspace(project.id)
            files = self._existing_files(workspace)
            if not files:
                resumed = False
                self.state_store.update_run(
                    run_id, stage="planning", status="running", attempts=0
                )
        else:
            run_id = (
                self.state_store.start_run(project.id, command)
                if self.state_store
                else None
            )
            workspace = self.workspace_manager.create_project_workspace(project.id)
            files = []

        def checkpoint(stage: str, status: str = "running", attempts: int = 0, error=None):
            if self.state_store and run_id is not None:
                self.state_store.update_run(
                    run_id, stage=stage, status=status, attempts=attempts, error=error
                )

        try:
            if not files:
                project.status = ProjectStatus.BUILDING
                checkpoint("building")
                architecture = await self.architect.design(project)
                plan = self.orchestrator.create_plan(project)
                developer_task = next(
                    task for task in plan.tasks if task.role.value == "developer"
                )
                developer_instruction = developer_task.instruction + "\n\nARCHITECTURE:\n" + architecture.plan
                files = await self.coder.implement(workspace, developer_instruction)
            else:
                project.status = ProjectStatus.TESTING

            project.status = ProjectStatus.TESTING
            checkpoint("testing")

            from astraforge.orchestration.loop import BuildTestLoop, PipelineRepairAgent

            repair_agent = PipelineRepairAgent(self.coder)
            test_loop = BuildTestLoop(
                self.runner,
                repair_agent=repair_agent,
                max_repairs=self.max_repairs,
            )
            test_result = await test_loop.run(workspace, command)
            attempts = test_result.attempts
            files = self._existing_files(workspace)

            if not test_result.passed:
                tester_findings = await self.tester.assess(project, files, test_result.stderr + "\n" + test_result.stdout)
                project.status = ProjectStatus.FAILED
                checkpoint("testing", "failed", attempts, "Tests failed")
                return PipelineResult(project.id, workspace, files, False, attempts, resumed=resumed)

            project.status = ProjectStatus.REVIEWING
            checkpoint("reviewing", attempts=attempts)
            tester_findings = await self.tester.assess(project, files, test_result.stderr + "\n" + test_result.stdout)
            architecture_text = locals().get("architecture").plan if "architecture" in locals() else "Architecture context unavailable"
            context_findings = await self.context_reviewer.review_context(project, architecture_text, files, tester_findings)

            if self.reviewer:
                for _ in range(self.max_review_repairs + 1):
                    review = await self.reviewer.review(workspace, files)
                    if context_findings.strip():
                        context_findings = await self.context_reviewer.review_context(project, architecture_text, files, context_findings)
                    if review.approved:
                        break
                    await self.coder.implement(
                        workspace,
                        "Fix these blocking review findings and return complete replacement files:\n"
                        + review.findings,
                    )
                    files = self._existing_files(workspace)
                    test_result = await test_loop.run(workspace, command)
                    attempts += test_result.attempts
                    if not test_result.passed:
                        project.status = ProjectStatus.FAILED
                        checkpoint("testing", "failed", attempts, "Tests failed after review repair")
                        return PipelineResult(
                            project.id, workspace, files, False, attempts, resumed=resumed
                        )
                else:
                    project.status = ProjectStatus.FAILED
                    checkpoint("reviewing", "failed", attempts, "Review gate not approved")
                    return PipelineResult(
                        project.id, workspace, files, True, attempts, resumed=resumed
                    )

            pr = None
            if self.github:
                project.status = ProjectStatus.REVIEWING
                checkpoint("github", attempts=attempts)
                branch = f"astraforge/{project.id}"
                self.github.create_branch(branch)
                for file_path in files:
                    self.github.commit_file(
                        branch, file_path,
                        self.workspace_manager.read_file(workspace, file_path),
                        f"feat: add {file_path}",
                    )
                pr = self.github.open_pull_request(
                    branch,
                    title=f"feat: AstraForge build — {project.name}",
                    body=(
                        f"Generated by AstraForge.\n\n"
                        f"Project: {project.description}\n"
                        f"Tests passed: {test_result.passed}"
                    ),
                )

            project.status = ProjectStatus.COMPLETED
            checkpoint("completed", "completed", attempts)
            return PipelineResult(
                project.id, workspace, files, True, attempts, pr, resumed
            )
        except Exception as exc:
            project.status = ProjectStatus.FAILED
            checkpoint(project.status.value, "failed", 0, str(exc))
            raise
