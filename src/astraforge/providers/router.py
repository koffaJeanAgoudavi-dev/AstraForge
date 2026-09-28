"""Role-aware model routing with provider fallback."""

from dataclasses import dataclass

from astraforge.providers.base import ModelProvider, ModelRequest, ModelResponse


@dataclass(frozen=True)
class RoutingProfile:
    role: str
    preferred_providers: tuple[str, ...]
    temperature: float = 0.2


DEFAULT_PROFILES = {
    "architect": RoutingProfile("architect", ("openai", "gemini", "deepseek", "mistral", "groq", "cerebras"), 0.1),
    "developer": RoutingProfile("developer", ("deepseek", "mistral", "openai", "gemini", "cerebras", "groq"), 0.1),
    "tester": RoutingProfile("tester", ("cerebras", "groq", "deepseek", "mistral", "gemini", "openai"), 0.0),
    "reviewer": RoutingProfile("reviewer", ("openai", "deepseek", "gemini", "mistral", "cerebras", "groq"), 0.0),
    "general": RoutingProfile("general", ("groq", "gemini", "deepseek", "mistral", "cerebras", "openai"), 0.2),
}


class ModelRouter:
    def __init__(
        self,
        providers: list[ModelProvider],
        profiles: dict[str, RoutingProfile] | None = None,
    ) -> None:
        if not providers:
            raise ValueError("At least one model provider is required")
        self.providers = providers
        self.profiles = profiles or DEFAULT_PROFILES

    def _ordered(self, role: str) -> list[ModelProvider]:
        profile = self.profiles.get(role, self.profiles["general"])
        by_name = {provider.name: provider for provider in self.providers}
        return [by_name[name] for name in profile.preferred_providers if name in by_name]

    async def generate(self, request: ModelRequest, role: str = "general") -> ModelResponse:
        errors = []
        providers = self._ordered(role) or self.providers
        for provider in providers:
            try:
                return await provider.generate(request)
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
        raise RuntimeError(f"All model providers failed for role '{role}': {errors}") from None
