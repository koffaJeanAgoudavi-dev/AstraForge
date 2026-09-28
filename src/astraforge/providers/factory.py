"""Provider stack factory with configured fallback order."""

from astraforge.config import settings
from astraforge.providers.deepseek import DeepSeekProvider
from astraforge.providers.gemini import GeminiProvider
from astraforge.providers.groq import GroqProvider
from astraforge.providers.router import ModelRouter

def build_router() -> ModelRouter:
    providers = []
    if settings.groq_api_key: providers.append(GroqProvider())
    if settings.gemini_api_key: providers.append(GeminiProvider())
    if settings.deepseek_api_key: providers.append(DeepSeekProvider())
    if not providers: raise RuntimeError("No model provider is configured")
    return ModelRouter(providers)
