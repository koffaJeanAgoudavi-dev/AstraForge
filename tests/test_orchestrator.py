from astraforge.orchestration.agents import AgentRole
from astraforge.orchestration.engine import Orchestrator
from astraforge.projects.schemas import ProjectSpec, ProjectStatus


def test_orchestrator_builds_ordered_plan() -> None:
    project = ProjectSpec(name="Demo", description="Build a demo")
    plan = Orchestrator().create_plan(project)

    assert [task.role for task in plan.tasks] == [
        AgentRole.ARCHITECT,
        AgentRole.DEVELOPER,
        AgentRole.TESTER,
        AgentRole.REVIEWER,
    ]
    assert project.status == ProjectStatus.PLANNING
