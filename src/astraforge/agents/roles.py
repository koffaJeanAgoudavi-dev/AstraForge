"""Role-aware agent orchestration."""

import json
from dataclasses import dataclass

from astraforge.providers.base import ModelRequest
from astraforge.providers.router import ModelRouter


@dataclass(frozen=True)
class ArchitectureResult:
    plan: str
    files: list[str]


class ArchitectAgent:
    def __init__(self, router: ModelRouter) -> None:
        self.router = router

    async def design(self, project) -> ArchitectureResult:
        response = await self.router.generate(
            ModelRequest(
                system_prompt=(
                    "You are AstraForge Architect. Design a practical software architecture. "
                    "Return ONLY JSON with keys plan (string) and files (array of relative paths). "
                    "Do not include secrets or absolute paths."
                ),
                prompt=(
                    f"Project: {project.name}\n"
                    f"Description: {project.description}\n"
                    f"Requirements: {json.dumps(project.requirements)}"
                ),
                temperature=0.1,
                max_tokens=5000,
            ),
            role="architect",
        )
        text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
        data = json.loads(text)
        return ArchitectureResult(data["plan"], data.get("files", []))


class TesterAgent:
    def __init__(self, router: ModelRouter) -> None:
        self.router = router

    async def assess(self, project, files: list[str], test_output: str) -> str:
        response = await self.router.generate(
            ModelRequest(
                system_prompt=(
                    "You are AstraForge Tester. Analyze test results and identify concrete "
                    "failures or missing tests. Return concise actionable findings."
                ),
                prompt=(
                    f"Project: {project.name}\n"
                    f"Files: {json.dumps(files)}\n"
                    f"Test output:\n{test_output}"
                ),
                temperature=0.0,
                max_tokens=3000,
            ),
            role="tester",
        )
        return response.text


class ReviewerAgentV2:
    def __init__(self, router: ModelRouter) -> None:
        self.router = router

    async def review_context(
        self, project, architecture: str, files: list[str], findings: str
    ) -> str:
        response = await self.router.generate(
            ModelRequest(
                system_prompt=(
                    "You are AstraForge Reviewer. Review implementation against architecture "
                    "and requirements. Identify blocking correctness, security, maintainability, "
                    "and coverage issues. Return actionable findings only."
                ),
                prompt=(
                    f"Project: {project.name}\n"
                    f"Architecture:\n{architecture}\n"
                    f"Files: {json.dumps(files)}\n"
                    f"Tester findings:\n{findings}"
                ),
                temperature=0.0,
                max_tokens=4000,
            ),
            role="reviewer",
        )
        return response.text
