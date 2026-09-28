"""Model-backed code review agent."""

from astraforge.providers.base import ModelRequest
from astraforge.providers.router import ModelRouter
from astraforge.workspace.manager import WorkspaceManager


class ReviewerAgent:
    def __init__(self, router: ModelRouter, workspace_manager: WorkspaceManager) -> None:
        self.router = router
        self.workspace_manager = workspace_manager

    async def review(self, workspace, files: list[str]) -> str:
        contents = []
        for path in files:
            contents.append(f"FILE: {path}\n{self.workspace_manager.read_file(workspace, path)}")
        response = await self.router.generate(
            ModelRequest(
                system_prompt=(
                    "You are AstraForge Reviewer. Review the supplied project for correctness, "
                    "security, maintainability and requirement coverage. Return concise findings."
                ),
                prompt="\n\n".join(contents),
                temperature=0.0,
                max_tokens=5000,
            )
        )
        return response.text
