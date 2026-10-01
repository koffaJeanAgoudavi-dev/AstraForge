"""Factory for the configured AstraForge model stack.

Providers are optional: AstraForge discovers every provider whose API key is
configured and keeps the router's role-specific fallback order.
"""

from astraforge.config import settings
from astraforge.providers.cerebras import CerebrasProvider
from astraforge.providers.deepseek import DeepSeekProvider
from astraforge.providers.gemini import GeminiProvider
from astraforge.providers.groq import GroqProvider
from astraforge.providers.mistral import MistralProvider
from astraforge.providers.openai import OpenAIProvider
from astraforge.providers.router import ModelRouter


def build_router() -> ModelRouter:
    providers = []

    if settings.groq_api_key:
        providers.append(GroqProvider())
    if settings.gemini_api_key:
        providers.append(GeminiProvider())
    if settings.deepseek_api_key:
        providers.append(DeepSeekProvider())
    if settings.openai_api_key:
        providers.append(OpenAIProvider())
    if settings.mistral_api_key:
        providers.append(MistralProvider())
    if settings.cerebras_api_key:
        providers.append(CerebrasProvider())

    if not providers:
        raise RuntimeError(
            "No model provider is configured. Set at least one provider API key."
        )

    return ModelRouter(providers)
