"""Sandboxed command execution for generated projects."""

import shlex
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
    """Legacy local runner for trusted development environments."""

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
    """Run commands in a restricted local Docker container."""

    def __init__(
        self,
        image: str = "astraforge-sandbox:latest",
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
            "docker", "run", "--rm", "--network", "none", "--read-only",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--pids-limit", str(self.pids_limit), "--memory", self.memory,
            "--cpus", self.cpus, "--tmpfs", "/tmp:rw,noexec,nosuid,size=128m",
            "-v", f"{workspace}:/workspace:rw", "-w", "/workspace",
            self.image, *command,
        ]
        try:
            result = subprocess.run(
                docker_command, cwd=workspace, capture_output=True, text=True,
                timeout=timeout, check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Docker is required for sandboxed execution") from exc
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                command, 124, exc.stdout or "",
                (exc.stderr or "") + "\\nSandbox execution timed out",
            )
        return CommandResult(command, result.returncode, result.stdout, result.stderr)


class E2BCommandRunner:
    """Execute allowlisted checks in an ephemeral, remote E2B sandbox.

    Only project files are uploaded. Application secrets and backend environment
    variables are never copied into the sandbox. E2B is an optional dependency.
    """

    def __init__(
        self,
        allowed_commands: set[str] | None = None,
        max_file_bytes: int = 2_000_000,
        max_workspace_bytes: int = 10_000_000,
    ) -> None:
        self.allowed_commands = allowed_commands or {"pytest", "python", "ruff"}
        self.max_file_bytes = max_file_bytes
        self.max_workspace_bytes = max_workspace_bytes

    def run(self, workspace: Path, command: list[str], timeout: int = 60) -> CommandResult:
        if not command or command[0] not in self.allowed_commands:
            raise ValueError("Command is not allowlisted")
        workspace = workspace.resolve()
        if not workspace.is_dir():
            raise ValueError("Workspace directory does not exist")

        files: list[tuple[Path, str]] = []
        total_bytes = 0
        for path in sorted(workspace.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            relative = path.relative_to(workspace)
            if any(part in {".git", ".venv", "node_modules", "__pycache__"} for part in relative.parts):
                continue
            size = path.stat().st_size
            if size > self.max_file_bytes:
                raise ValueError(f"Workspace file exceeds sandbox upload limit: {relative}")
            total_bytes += size
            if total_bytes > self.max_workspace_bytes:
                raise ValueError("Workspace exceeds sandbox upload limit")
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Test/code workspaces are text-first; binary artifacts are not uploaded.
                continue
            files.append((relative, text))

        try:
            from e2b import Sandbox
        except ImportError as exc:
            raise RuntimeError(
                "E2B sandbox support is optional; install AstraForge with the 'sandbox' extra"
            ) from exc

        try:
            with Sandbox.create(timeout=max(60, timeout + 30)) as sandbox:
                sandbox.commands.run("mkdir -p /workspace", timeout=10)
                for relative, content in files:
                    remote_path = "/workspace/" + relative.as_posix()
                    remote_parent = remote_path.rsplit("/", 1)[0]
                    sandbox.commands.run("mkdir -p " + shlex.quote(remote_parent), timeout=10)
                    sandbox.files.write(remote_path, content)
                if command[0] == "pytest":
                    install = sandbox.commands.run("python -m pip install --quiet pytest", timeout=min(timeout, 120))
                    if install.exit_code != 0:
                        return CommandResult(command, install.exit_code, install.stdout or "", install.stderr or "")
                elif command[0] == "ruff":
                    install = sandbox.commands.run("python -m pip install --quiet ruff", timeout=min(timeout, 120))
                    if install.exit_code != 0:
                        return CommandResult(command, install.exit_code, install.stdout or "", install.stderr or "")
                result = sandbox.commands.run(
                    "cd /workspace && " + shlex.join(command),
                    timeout=timeout,
                )
                return CommandResult(
                    command,
                    int(result.exit_code),
                    result.stdout or "",
                    result.stderr or "",
                )
        except TimeoutError as exc:
            return CommandResult(command, 124, "", f"Sandbox execution timed out: {exc}")
