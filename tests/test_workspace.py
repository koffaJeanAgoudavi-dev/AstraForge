import pytest

from astraforge.workspace.manager import WorkspaceManager
from astraforge.workspace.runner import CommandRunner


def test_workspace_rejects_path_escape(tmp_path) -> None:
    manager = WorkspaceManager(tmp_path)
    workspace = manager.create("demo")
    with pytest.raises(ValueError):
        manager.write_file(workspace, "../outside.txt", "blocked")


def test_runner_rejects_unknown_command(tmp_path) -> None:
    with pytest.raises(ValueError):
        CommandRunner().run(tmp_path, ["rm", "-rf", "."])
