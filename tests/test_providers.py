import pytest

from astraforge.config import settings
from astraforge.providers.factory import build_router


def test_factory_accepts_multiple_configured_providers(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "x")
    monkeypatch.setattr(settings, "gemini_api_key", "x")
    monkeypatch.setattr(settings, "deepseek_api_key", "x")
    monkeypatch.setattr(settings, "openai_api_key", "x")
    monkeypatch.setattr(settings, "mistral_api_key", "x")
    monkeypatch.setattr(settings, "cerebras_api_key", "x")
    router = build_router()
    assert [p.name for p in router.providers] == [
        "groq", "gemini", "deepseek", "openai", "mistral", "cerebras"
    ]


def test_factory_fails_without_provider(monkeypatch):
    for name in (
        "groq_api_key", "gemini_api_key", "deepseek_api_key",
        "openai_api_key", "mistral_api_key", "cerebras_api_key",
    ):
        monkeypatch.setattr(settings, name, None)
    with pytest.raises(RuntimeError):
        build_router()


def test_router_orders_providers_by_role():
    from astraforge.providers.base import ModelProvider, ModelResponse

    class P(ModelProvider):
        def __init__(self, name): self.name = name
        async def generate(self, request):
            return ModelResponse("ok", self.name, "test")

    from astraforge.providers.router import ModelRouter
    router = ModelRouter([P("groq"), P("deepseek"), P("openai")])
    assert [p.name for p in router._ordered("developer")] == ["deepseek", "openai", "groq"]
