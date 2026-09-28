"""Sandboxed command execution for generated projects."""

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
    """Legacy local runner for trusted development environments.

    Production orchestration should use DockerCommandRunner.
    """

    def __init__(self, allowed_commands: set[str] | None = None) -> None:
        self.allowed_commands = allowed_commands or {"pytest", "python", "ruff"}

    def run(self, workspace: Path, command: list[str], timeout: int = 30) -> CommandResult:
        if not command or command[0] not in self.allowed_commands:
            raise ValueError("Command is not allowlisted")
        result = subprocess.run(
            command, cwd=workspace, capture_output=True, text=True,
            timeout=timeout, check=False,
        )
        return CommandResult(command, result.returncode, result.stdout, result.stderr)


class DockerCommandRunner:
    """Run generated-project commands inside an isolated Docker container.

    The container has no network, no Linux capabilities, no privilege escalation,
    a read-only root filesystem, bounded memory/CPU/PIDs, and only the workspace
    mounted read-write.
    """

    def __init__(
        self,
        image: str = "python:3.12-slim",
        allowed_commands: set[str] | None = None,
        memory: str = "512m",
        cpus: str = "1.0",
        pids_limit: int = 128,
    ) -> None:
        self.image = image
        self.allowed_commands = allowed_commands or {"pytest", "python", "ruff"}
        self.memory = memory
        self.cpus = cpus
        self.pids_limit = pids_limit

    def run(self, workspace: Path, command: list[str], timeout: int = 60) -> CommandResult:
        if not command or command[0] not in self.allowed_commands:
            raise ValueError("Command is not allowlisted")
        workspace = workspace.resolve()
        if not workspace.is_dir():
            raise ValueError("Workspace directory does not exist")

        docker_command = [
            "docker", "run", "--rm",
            "--network", "none",
            "--read-only",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--pids-limit", str(self.pids_limit),
            "--memory", self.memory,
            "--cpus", self.cpus,
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=128m",
            "-v", f"{workspace}:/workspace:rw",
            "-w", "/workspace",
            self.image,
            *command,
        ]
        try:
            result = subprocess.run(
                docker_command,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Docker is required for sandboxed execution") from exc
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                command, 124,
                exc.stdout or "",
                (exc.stderr or "") + "\nSandbox execution timed out",
            )
        return CommandResult(command, result.returncode, result.stdout, result.stderr)
