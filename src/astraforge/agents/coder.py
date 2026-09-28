"""LLM-backed coding agent that writes validated file patches."""

import json
import re

from astraforge.providers.base import ModelRequest
from astraforge.providers.router import ModelRouter
from astraforge.workspace.manager import WorkspaceManager


class CodingAgent:
    def __init__(self, router: ModelRouter, workspace_manager: WorkspaceManager) -> None:
        self.router = router
        self.workspace_manager = workspace_manager

    async def implement(self, workspace, instruction: str) -> list[str]:
        response = await self.router.generate(
            ModelRequest(
                system_prompt=(
                    'You are AstraForge Developer. Return ONLY valid JSON with this shape: '
                    '{"files":[{"path":"relative/path","content":"full file content"}]}. '
                    'Never use absolute paths or paths containing .. .'
                ),
                prompt=instruction,
                temperature=0.1,
                max_tokens=12000,
            )
        )
        files = self._parse(response.text)
        written = []
        for item in files:
            path = item["path"]
            if not isinstance(path, str) or path.startswith("/") or ".." in path.split("/"):
                raise ValueError("Model returned an unsafe file path")
            if not isinstance(item.get("content"), str):
                raise ValueError("Model returned invalid file content")
            self.workspace_manager.write_file(workspace, path, item["content"])
            written.append(path)
        return written

    @staticmethod
    def _parse(text: str) -> list[dict[str, str]]:
        cleaned = re.sub(r"^\`\`\`(?:json)?\s*|\s*\`\`\`$", "", text.strip(), flags=re.IGNORECASE)
        data = json.loads(cleaned)
        if not isinstance(data, dict) or not isinstance(data.get("files"), list):
            raise ValueError("Model response does not contain a files list")
        return data["files"]
