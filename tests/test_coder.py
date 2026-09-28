import json

import pytest

from astraforge.agents.coder import CodingAgent
from astraforge.providers.base import ModelResponse
from astraforge.workspace.manager import WorkspaceManager


class FakeRouter:
    async def generate(self, request):
        return ModelResponse(
            text=json.dumps({"files": [{"path": "app.py", "content": "print('ok')"}]}),
            provider="fake",
            model="test",
        )


@pytest.mark.asyncio
async def test_coder_writes_model_files(tmp_path):
    manager = WorkspaceManager(tmp_path)
    workspace = manager.create("demo")
    written = await CodingAgent(FakeRouter(), manager).implement(workspace, "create app")
    assert written == ["app.py"]
    assert (workspace / "app.py").read_text() == "print('ok')"


@pytest.mark.asyncio
async def test_coder_rejects_path_traversal(tmp_path):
    manager = WorkspaceManager(tmp_path)
    workspace = manager.create("demo")

    class UnsafeRouter:
        async def generate(self, request):
            return ModelResponse(
                text=json.dumps({"files": [{"path": "../secret", "content": "bad"}]}),
                provider="fake",
                model="test",
            )

    with pytest.raises(ValueError):
        await CodingAgent(UnsafeRouter(), manager).implement(workspace, "unsafe")
