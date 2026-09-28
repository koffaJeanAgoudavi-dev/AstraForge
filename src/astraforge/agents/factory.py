"""Factory for the initial AstraForge model stack."""

from astraforge.config import settings
from astraforge.providers.groq import GroqProvider
from astraforge.providers.router import ModelRouter


def build_router() -> ModelRouter:
    providers = []
    if settings.groq_api_key:
        providers.append(GroqProvider())
    if not providers:
        raise RuntimeError("No model provider is configured")
    return ModelRouter(providers)
