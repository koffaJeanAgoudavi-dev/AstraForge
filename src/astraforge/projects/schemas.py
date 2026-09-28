"""Typed project and task schemas for orchestration."""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class ProjectStatus(StrEnum):
    CREATED = "created"
    PLANNING = "planning"
    BUILDING = "building"
    TESTING = "testing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProjectSpec(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1)
    requirements: list[str] = Field(default_factory=list)
    status: ProjectStatus = ProjectStatus.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
