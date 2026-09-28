"""Model-backed code review agent."""

import json
from dataclasses import dataclass

from astraforge.providers.base import ModelRequest
from astraforge.providers.router import ModelRouter
from astraforge.workspace.manager import WorkspaceManager


@dataclass(frozen=True)
class ReviewResult:
    approved: bool
    findings: str


class ReviewerAgent:
    def __init__(self, router: ModelRouter, workspace_manager: WorkspaceManager) -> None:
        self.router = router
        self.workspace_manager = workspace_manager

    async def review(self, workspace, files: list[str]) -> ReviewResult:
        contents = []
        for path in files:
            contents.append(f"FILE: {path}\n{self.workspace_manager.read_file(workspace, path)}")
        response = await self.router.generate(
            ModelRequest(
                system_prompt=(
                    "You are AstraForge Reviewer. Review the supplied project for correctness, "
                    "security, maintainability and requirement coverage. "
                    "Return ONLY JSON with keys approved (boolean) and findings (string). "
                    "Approve only when there are no concrete blocking defects."
                ),
                prompt="\n\n".join(contents),
                temperature=0.0,
                max_tokens=5000,
            )
        )
        data = json.loads(response.text.strip())
        if not isinstance(data.get("approved"), bool) or not isinstance(data.get("findings"), str):
            raise ValueError("Invalid reviewer response")
        return ReviewResult(data["approved"], data["findings"])
