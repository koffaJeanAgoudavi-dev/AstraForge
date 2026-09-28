"""OpenAI provider adapter."""

from openai import AsyncOpenAI

from astraforge.config import settings
from astraforge.providers.base import ModelProvider, ModelRequest, ModelResponse


class OpenAIProvider(ModelProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)

    async def generate(self, request: ModelRequest) -> ModelResponse:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        result = await self._client.chat.completions.create(
            model=request.model or settings.openai_default_model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        choice = result.choices[0]
        return ModelResponse(
            text=choice.message.content or "",
            provider=self.name,
            model=result.model,
            usage=result.usage.model_dump() if result.usage else None,
        )
