"""Bounded autonomous build/test/repair loop."""

from dataclasses import dataclass
from collections.abc import Awaitable, Callable
from typing import Protocol

from astraforge.workspace.runner import CommandResult
from astraforge.workspace.runner import CommandRunner


class RepairAgent(Protocol):
    async def repair(self, failure: CommandResult) -> None: ...


@dataclass(frozen=True)
class LoopResult:
    passed: bool
    attempts: int
    last_result: CommandResult


class PipelineRepairAgent:
    """Adapt the coding agent to the generic test-loop repair contract."""

    def __init__(self, coder, workspace) -> None:
        self.coder = coder
        self.workspace = workspace

    async def repair(self, failure: CommandResult) -> None:
        output = f"STDOUT:\n{failure.stdout}\n\nSTDERR:\n{failure.stderr}"
        await self.coder.implement(
            self.workspace,
            "Fix the failing tests or code using this test output and return complete replacement files:\n"
            + output,
        )


class BuildTestLoop:
    def __init__(self, runner: CommandRunner, max_repairs: int = 3) -> None:
        if max_repairs < 0:
            raise ValueError("max_repairs must be >= 0")
        self.runner = runner
        self.max_repairs = max_repairs

    async def run(\n        self, workspace, command: list[str], repair_agent: RepairAgent | None = None,\n        event_callback: Callable[[str, int], Awaitable[None]] | None = None,\n    ) -> LoopResult:
        attempts = 0
        while True:
            result = self.runner.run(workspace, command)
            if result.return_code == 0:
                return LoopResult(True, attempts, result)
            if attempts >= self.max_repairs or repair_agent is None:
                return LoopResult(False, attempts, result)
            attempts += 1
            if event_callback is not None:
                await event_callback("repair.started", attempts)
            await repair_agent.repair(result)
            if event_callback is not None:
                await event_callback("repair.completed", attempts)
