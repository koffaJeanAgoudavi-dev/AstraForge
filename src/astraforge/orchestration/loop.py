"""Bounded autonomous build/test/repair loop."""

from dataclasses import dataclass
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


class BuildTestLoop:
    def __init__(self, runner: CommandRunner, max_repairs: int = 3) -> None:
        if max_repairs < 0:
            raise ValueError("max_repairs must be >= 0")
        self.runner = runner
        self.max_repairs = max_repairs

    async def run(self, workspace, command: list[str], repair_agent: RepairAgent | None = None) -> LoopResult:
        attempts = 0
        while True:
            result = self.runner.run(workspace, command)
            if result.return_code == 0:
                return LoopResult(True, attempts, result)
            if attempts >= self.max_repairs or repair_agent is None:
                return LoopResult(False, attempts, result)
            await repair_agent.repair(result)
            attempts += 1
