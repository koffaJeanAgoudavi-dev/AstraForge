from pathlib import Path

import pytest

from astraforge.workspace.runner import E2BCommandRunner


def test_e2b_runner_rejects_unallowlisted_commands(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="allowlisted"):
        E2BCommandRunner().run(tmp_path, ["bash", "-lc", "echo unsafe"])


def test_e2b_runner_rejects_missing_workspace(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(ValueError, match="does not exist"):
        E2BCommandRunner().run(missing, ["pytest"])


def test_e2b_runner_rejects_oversized_file_before_remote_call(tmp_path: Path) -> None:
    (tmp_path / "large.txt").write_text("x" * 12, encoding="utf-8")
    runner = E2BCommandRunner(max_file_bytes=10)
    with pytest.raises(ValueError, match="exceeds sandbox upload limit"):
        runner.run(tmp_path, ["pytest"])


def test_e2b_runner_rejects_oversized_workspace_before_remote_call(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("123456", encoding="utf-8")
    (tmp_path / "b.txt").write_text("abcdef", encoding="utf-8")
    runner = E2BCommandRunner(max_file_bytes=10, max_workspace_bytes=10)
    with pytest.raises(ValueError, match="Workspace exceeds sandbox upload limit"):
        runner.run(tmp_path, ["pytest"])
