"""API endpoints for starting orchestration runs."""

import asyncio

from fastapi import APIRouter, HTTPException

from astraforge.agents.coder import CodingAgent
from astraforge.agents.factory import build_router
from astraforge.agents.reviewer import ReviewerAgent
from astraforge.config import settings
from astraforge.integrations.github import GitHubAdapter
from astraforge.orchestration.engine import Orchestrator
from astraforge.orchestration.pipeline import AutonomousPipeline
from astraforge.projects.schemas import ProjectSpec
from astraforge.state.store import StateStore
from astraforge.workspace.manager import WorkspaceManager
from astraforge.workspace.runner import DockerCommandRunner

router = APIRouter(prefix="/projects", tags=["projects"])
orchestrator = Orchestrator()
state_store = StateStore()


@router.post("/plan")
def create_project_plan(project: ProjectSpec) -> dict:
    state_store.save_project(project)
    plan = orchestrator.create_plan(project)
    state_store.save_project(project)
    return {
        "project_id": plan.project_id,
        "status": project.status,
        "tasks": [{"role": task.role, "instruction": task.instruction} for task in plan.tasks],
    }


@router.post("/build")
async def build_project(project: ProjectSpec, publish: bool = False) -> dict:
    state_store.save_project(project)
    model_router = build_router()
    workspace_manager = WorkspaceManager()
    coder = CodingAgent(model_router, workspace_manager)
    reviewer = ReviewerAgent(model_router, workspace_manager)

    github = None
    if publish:
        if not settings.github_token or not settings.github_repository:
            raise HTTPException(
                status_code=400,
                detail="GitHub publishing requires GITHUB_TOKEN and GITHUB_REPOSITORY",
            )
        github = GitHubAdapter(settings.github_token, settings.github_repository)

    pipeline = AutonomousPipeline(
        coder,
        workspace_manager,
        DockerCommandRunner(),
        github=github,
        reviewer=reviewer,
        state_store=state_store,
    )
    result = await pipeline.run(project, ["python", "-m", "pytest", "-q"])
    state_store.save_project(project)

    response = {
        "project_id": result.project_id,
        "status": project.status,
        "workspace": str(result.workspace),
        "files": result.files,
        "tests_passed": result.tests_passed,
        "repair_attempts": result.attempts,
        "resumed": result.resumed,
    }
    if result.pull_request:
        response["pull_request"] = {
            "number": result.pull_request.number,
            "url": result.pull_request.url,
            "branch": result.pull_request.branch,
        }
    return response


@router.get("/{project_id}")
def get_project_state(project_id: str) -> dict:
    project = state_store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    run = state_store.get_latest_run(project_id)
    return {"project": project.model_dump(mode="json"), "latest_run": run}
