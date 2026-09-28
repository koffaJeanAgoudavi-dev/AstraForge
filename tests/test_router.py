import pytest

from astraforge.providers.base import ModelProvider, ModelRequest, ModelResponse
from astraforge.providers.router import ModelRouter


class FailingProvider(ModelProvider):
    name = "failing"

    async def generate(self, request: ModelRequest) -> ModelResponse:
        raise RuntimeError("provider unavailable")


class WorkingProvider(ModelProvider):
    name = "working"

    async def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(text="ok", provider=self.name, model="test")


@pytest.mark.asyncio
async def test_router_falls_back_to_next_provider() -> None:
    response = await ModelRouter([FailingProvider(), WorkingProvider()]).generate(ModelRequest(prompt="hello"))
    assert response.text == "ok"
    assert response.provider == "working"
