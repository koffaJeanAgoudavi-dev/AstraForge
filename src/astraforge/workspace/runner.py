"""Allowlisted subprocess execution for project checks."""

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    return_code: int
    stdout: str
    stderr: str


class CommandRunner:
    """Run only explicitly allowlisted commands from a workspace."""

    def __init__(self, allowed_commands: set[str] | None = None) -> None:
        self.allowed_commands = allowed_commands or {"pytest", "python", "ruff"}

    def run(self, workspace: Path, command: list[str], timeout: int = 30) -> CommandResult:
        if not command or command[0] not in self.allowed_commands:
            raise ValueError("Command is not allowlisted")
        result = subprocess.run(
            command,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return CommandResult(command, result.returncode, result.stdout, result.stderr)
