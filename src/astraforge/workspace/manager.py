"""Controlled workspace filesystem operations."""

from pathlib import Path
from uuid import uuid4


class WorkspaceManager:
    """Create and manipulate files only inside an AstraForge workspace root."""

    def __init__(self, root: str | Path = ".astraforge/workspaces") -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, project_id: str | None = None) -> Path:
        name = project_id or str(uuid4())
        workspace = (self.root / name).resolve()
        workspace.relative_to(self.root)
        workspace.mkdir(parents=True, exist_ok=False)
        return workspace

    def _safe_path(self, workspace: Path, relative_path: str) -> Path:
        target = (workspace / relative_path).resolve()
        target.relative_to(workspace.resolve())
        return target

    def write_file(self, workspace: Path, relative_path: str, content: str) -> Path:
        target = self._safe_path(workspace, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def read_file(self, workspace: Path, relative_path: str) -> str:
        return self._safe_path(workspace, relative_path).read_text(encoding="utf-8")
