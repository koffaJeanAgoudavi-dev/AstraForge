import pytest

from astraforge.orchestration.loop import BuildTestLoop
from astraforge.workspace.runner import CommandResult


class FakeRunner:
    def __init__(self):
        self.calls = 0

    def run(self, workspace, command):
        self.calls += 1
        return CommandResult(command, 0 if self.calls > 1 else 1, "", "failure" if self.calls == 1 else "")


class FakeRepair:
    def __init__(self):
        self.calls = 0

    async def repair(self, failure):
        self.calls += 1


@pytest.mark.asyncio
async def test_loop_repairs_then_retests(tmp_path):
    repair = FakeRepair()
    result = await BuildTestLoop(FakeRunner(), max_repairs=2).run(tmp_path, ["python", "-c", "pass"], repair)
    assert result.passed is True
    assert result.attempts == 1
    assert repair.calls == 1
