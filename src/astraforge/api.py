"""API endpoints for starting orchestration runs."""

from fastapi import APIRouter

from astraforge.orchestration.engine import Orchestrator
from astraforge.projects.schemas import ProjectSpec

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
