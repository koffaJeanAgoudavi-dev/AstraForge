"""Autonomous build, test, review and delivery pipeline."""

from dataclasses import dataclass

import asyncio
from pathlib import Path

from astraforge.agents.coder import CodingAgent
from astraforge.agents.reviewer import ReviewerAgent
from astraforge.agents.roles import ArchitectAgent, TesterAgent, ReviewerAgentV2
from astraforge.integrations.github import GitHubAdapter, PullRequestInfo
from astraforge.integrations.deployment import DeploymentResult
from astraforge.memory.embeddings import build_embedding_provider
from astraforge.memory.store import MemoryStore
from astraforge.orchestration.context import ExecutionContext
from astraforge.orchestration.engine import Orchestrator
from astraforge.orchestration.events import build_events
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
    deployment: DeploymentResult | None = None
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
        deployer=None,
    ) -> None:
        self.coder = coder
        self.workspace_manager = workspace_manager
        self.runner = runner
        self.github = github
        self.reviewer = reviewer
        self.max_repairs = max_repairs
        self.max_review_repairs = max_review_repairs
        self.state_store = state_store
        self.deployer = deployer
        self.architect = ArchitectAgent(coder.router)
        self.tester = TesterAgent(coder.router)
        self.context_reviewer = ReviewerAgentV2(coder.router)
        self.orchestrator = Orchestrator()
        self.memory = MemoryStore()
        self.embedding_provider = build_embedding_provider()

    def _existing_files(self, workspace: Path) -> list[str]:
        return sorted(str(path.relative_to(workspace)) for path in workspace.rglob("*") if path.is_file())

    async def _memory_embedding(self, text: str) -> list[float] | None:
        if not self.embedding_provider:
            return None
        try:
            return await self.embedding_provider.embed(text)
        except Exception:
            return None

    async def _load_relevant_memories(self, project: ProjectSpec) -> list[dict]:
        query = f"{project.name}\n{project.description}\n{project.requirements}"
        embedding = await self._memory_embedding(query)
        if embedding:
            results = self.memory.semantic_recall(embedding, limit=8)
            if results:
                return results
        return self.memory.recall(limit=8)

    async def run(self, project: ProjectSpec, command: list[str], resume: bool = True, run_id: int | None = None) -> PipelineResult:
        if self.state_store:
            self.state_store.save_project(project)

        resumable = (
            self.state_store.get_run(run_id)
            if self.state_store and run_id is not None
            else (
                self.state_store.find_resumable_run(project.id)
                if self.state_store and resume
                else None
            )
        )
        resumed = resumable is not None
        context = ExecutionContext(project.id, requirements=list(project.requirements))
        for memory in await self._load_relevant_memories(project):
            context.add_memory(memory)

        if resumable:
            saved = resumable.get("context", {})
            for key, value in saved.items():
                if hasattr(context, key):
                    setattr(context, key, value)

        if resumable:
            run_id = resumable["id"]
            workspace = self.workspace_manager.create_project_workspace(project.id)
            files = self._existing_files(workspace)
            context.files = files
            if not files:
                resumed = False
                self.state_store.update_run(run_id, stage="planning", status="running", attempts=0)
        else:
            run_id = self.state_store.start_run(project.id, command) if self.state_store else None
            workspace = self.workspace_manager.create_project_workspace(project.id)
            files = []

        async def checkpoint(stage: str, status: str = "running", attempts: int = 0, error: str | None = None, message: str | None = None):
            event = None
            if self.state_store and run_id is not None:
                self.state_store.update_run(
                    run_id, stage=stage, status=status, attempts=attempts,
                    error=error, context=context.snapshot(),
                )
                event = self.state_store.append_event(
                    project.id, stage, status, message or error, {"attempts": attempts}, run_id
                )
            if event is None:
                event = {"type": "stage", "stage": stage, "status": status, "attempts": attempts, "error": error}
            await build_events.publish(project.id, event)

        async def check_cancelled() -> None:
            if self.state_store and run_id is not None and self.state_store.is_cancel_requested(run_id):
                project.status = ProjectStatus.CANCELLED
                await checkpoint("cancelled", "cancelled", 0, "Build cancelled by user")
                raise asyncio.CancelledError

        try:
            await check_cancelled()
            architecture_text = context.architecture
            if not files:
                await check_cancelled()
                project.status = ProjectStatus.BUILDING
                await checkpoint("building")
                architecture = await self.architect.design(project)
                architecture_text = architecture.plan
                context.architecture = architecture.plan
                context.files = architecture.files
                context.add_decision("Architecture generated by Architect agent")

                memory_text = f"{project.name}\n{project.description}\n{architecture.plan}"
                self.memory.remember(
                    "architecture",
                    project.name,
                    {"plan": architecture.plan, "files": architecture.files},
                    project.id,
                    await self._memory_embedding(memory_text),
                )
                await checkpoint("building")

                plan = self.orchestrator.create_plan(project)
                developer_task = next(task for task in plan.tasks if task.role.value == "developer")
                developer_instruction = (
                    developer_task.instruction
                    + "\n\nARCHITECTURE:\n" + architecture.plan
                    + "\n\nRELEVANT MEMORY:\n" + context.prompt()
                )
                await self.coder.implement(workspace, developer_instruction)
                files = self._existing_files(workspace)
                context.files = files
                context.add_decision("Developer implementation generated from architecture")
            else:
                architecture_text = context.architecture

            await check_cancelled()
            project.status = ProjectStatus.TESTING
            await checkpoint("testing")

            from astraforge.orchestration.loop import BuildTestLoop, PipelineRepairAgent

            test_loop = BuildTestLoop(self.runner, max_repairs=self.max_repairs)
            repair_agent = PipelineRepairAgent(self.coder, workspace)
            test_result = await test_loop.run(workspace, command, repair_agent=repair_agent)
            attempts = test_result.attempts
            context.record_test(
                test_result.passed,
                test_result.attempts,
                test_result.stdout,
                test_result.stderr,
            )
            files = self._existing_files(workspace)
            context.files = files

            tester_findings = await self.tester.assess(
                project, files, test_result.stderr + "\n" + test_result.stdout
            )
            context.tester_findings.append(tester_findings)

            if not test_result.passed:
                project.status = ProjectStatus.FAILED
                await checkpoint("testing", "failed", attempts, "Tests failed")
                return PipelineResult(project.id, workspace, files, False, attempts, resumed=resumed)

            await check_cancelled()
            project.status = ProjectStatus.REVIEWING
            await checkpoint("reviewing", attempts=attempts)
            context_findings = await self.context_reviewer.review_context(
                project, architecture_text, files, tester_findings + "\n\nContext:\n" + context.prompt()
            )
            context.reviewer_findings.append(context_findings)

            if self.reviewer:
                approved = False
                for _ in range(self.max_review_repairs + 1):
                    review = await self.reviewer.review(workspace, files)
                    if review.approved:
                        approved = True
                        context.add_decision("Reviewer gate approved implementation")
                        break

                    context.reviewer_findings.append(review.findings)
                    context.record_repair("reviewer", review.findings)
                    await self.coder.implement(
                        workspace,
                        "Fix these blocking review findings and return complete replacement files:\n"
                        + review.findings
                        + "\n\nSHARED CONTEXT:\n"
                        + context.prompt(),
                    )
                    files = self._existing_files(workspace)
                    context.files = files
                    test_result = await test_loop.run(workspace, command, repair_agent=repair_agent)
                    attempts += test_result.attempts
                    context.record_test(
                        test_result.passed,
                        test_result.attempts,
                        test_result.stdout,
                        test_result.stderr,
                    )
                    if not test_result.passed:
                        project.status = ProjectStatus.FAILED
                        await checkpoint("testing", "failed", attempts, "Tests failed after review repair")
                        return PipelineResult(project.id, workspace, files, False, attempts, resumed=resumed)

                if not approved:
                    project.status = ProjectStatus.FAILED
                    await checkpoint("reviewing", "failed", attempts, "Review gate not approved")
                    return PipelineResult(project.id, workspace, files, True, attempts, resumed=resumed)

            pr = None
            await check_cancelled()
            if self.github:
                await checkpoint("github", attempts=attempts)
                branch = f"astraforge/{project.id}"
                self.github.create_branch(branch)
                for file_path in files:
                    self.github.commit_file(
                        branch,
                        file_path,
                        self.workspace_manager.read_file(workspace, file_path),
                        f"feat: add {file_path}",
                    )
                pr = self.github.open_pull_request(
                    branch,
                    title=f"feat: AstraForge build — {project.name}",
                    body=(
                        "Generated by AstraForge.\n\n"
                        f"Project: {project.description}\n"
                        f"Tests passed: {test_result.passed}"
                    ),
                )

            deployment = None
            await check_cancelled()
            if self.deployer:
                await checkpoint("deploying", attempts=attempts)
                deployment = await __import__("asyncio").to_thread(self.deployer.deploy, workspace)
                context.add_decision(f"Deployment completed: {deployment.url}")

            outcome_text = f"{project.name}\n{project.description}\n{files}\n{context.decisions}"
            self.memory.remember(
                "build_outcome",
                f"{project.name}:outcome",
                {"tests_passed": True, "files": files, "decisions": context.decisions},
                project.id,
                await self._memory_embedding(outcome_text),
            )
            project.status = ProjectStatus.COMPLETED
            await checkpoint("completed", "completed", attempts)
            return PipelineResult(project.id, workspace, files, True, attempts, pr, deployment, resumed)

        except asyncio.CancelledError:
            if project.status != ProjectStatus.CANCELLED:
                project.status = ProjectStatus.CANCELLED
                await checkpoint("cancelled", "cancelled", 0, "Build cancelled by user")
            return PipelineResult(project.id, workspace, self._existing_files(workspace), False, 0, resumed=resumed)
        except Exception as exc:
            project.status = ProjectStatus.FAILED
            await checkpoint(project.status.value, "failed", 0, str(exc))
            raise
