"""Model routing with provider fallback."""

from astraforge.providers.base import ModelProvider, ModelRequest, ModelResponse


class ModelRouter:
    def __init__(self, providers: list[ModelProvider]) -> None:
        if not providers:
            raise ValueError("At least one model provider is required")
        self.providers = providers

    async def generate(self, request: ModelRequest) -> ModelResponse:
        errors: list[Exception] = []
        for provider in self.providers:
            try:
                return await provider.generate(request)
            except Exception as exc:
                errors.append(exc)
        raise RuntimeError(f"All model providers failed: {errors}") from errors[-1]
