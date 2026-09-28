"""API endpoints for starting orchestration runs."""

from fastapi import APIRouter

from astraforge.agents.coder import CodingAgent
from astraforge.agents.factory import build_router
from astraforge.orchestration.engine import Orchestrator
from astraforge.orchestration.pipeline import AutonomousPipeline
from astraforge.projects.schemas import ProjectSpec
from astraforge.workspace.manager import WorkspaceManager
from astraforge.workspace.runner import CommandRunner

router = APIRouter(prefix="/projects", tags=["projects"])
orchestrator = Orchestrator()


@router.post("/plan")
def create_project_plan(project: ProjectSpec) -> dict:
    plan = orchestrator.create_plan(project)
    return {
        "project_id": plan.project_id,
        "status": project.status,
        "tasks": [{"role": task.role, "instruction": task.instruction} for task in plan.tasks],
    }


@router.post("/build")
async def build_project(project: ProjectSpec) -> dict:
    model_router = build_router()
    workspace_manager = WorkspaceManager()
    coder = CodingAgent(model_router, workspace_manager)
    pipeline = AutonomousPipeline(coder, workspace_manager, CommandRunner())
    result = await pipeline.run(project, ["python", "-m", "pytest", "-q"])
    return {
        "project_id": result.project_id,
        "status": project.status,
        "workspace": str(result.workspace),
        "files": result.files,
        "tests_passed": result.tests_passed,
        "repair_attempts": result.attempts,
    }
