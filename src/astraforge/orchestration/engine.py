"""Deterministic orchestration state machine."""

from dataclasses import dataclass

from astraforge.orchestration.agents import AgentRole, AgentTask
from astraforge.projects.schemas import ProjectSpec, ProjectStatus


@dataclass
class OrchestrationPlan:
    project_id: str
    tasks: list[AgentTask]


class Orchestrator:
    """Build the execution plan before any model or tool is invoked."""

    def create_plan(self, project: ProjectSpec) -> OrchestrationPlan:
        tasks = [
            AgentTask(AgentRole.ARCHITECT, "Produce a technical architecture and implementation plan.", project.id),
            AgentTask(AgentRole.DEVELOPER, "Implement the approved plan in the project workspace.", project.id),
            AgentTask(AgentRole.TESTER, "Run the project's automated checks and report failures.", project.id),
            AgentTask(AgentRole.REVIEWER, "Review the implementation and identify concrete defects.", project.id),
        ]
        project.status = ProjectStatus.PLANNING
        return OrchestrationPlan(project_id=project.id, tasks=tasks)
