"""Agent roles used by the AstraForge orchestration pipeline."""

from dataclasses import dataclass
from enum import StrEnum


class AgentRole(StrEnum):
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    TESTER = "tester"


@dataclass(frozen=True)
class AgentTask:
    role: AgentRole
    instruction: str
    project_id: str
