"""DeepSeek provider adapter via OpenAI-compatible API."""

from openai import AsyncOpenAI
from astraforge.config import settings
from astraforge.providers.base import ModelProvider, ModelRequest, ModelResponse

class DeepSeekProvider(ModelProvider):
    name = "deepseek"

    def __init__(self, api_key: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key or settings.deepseek_api_key,
                                   base_url="https://api.deepseek.com")

    async def generate(self, request: ModelRequest) -> ModelResponse:
        messages = ([{"role": "system", "content": request.system_prompt}]
                    if request.system_prompt else [])
        messages.append({"role": "user", "content": request.prompt})
        result = await self._client.chat.completions.create(
            model=request.model or settings.deepseek_default_model,
            messages=messages, temperature=request.temperature,
            max_tokens=request.max_tokens)
        choice = result.choices[0]
        return ModelResponse(text=choice.message.content or "", provider=self.name,
                             model=result.model,
                             usage=result.usage.model_dump() if result.usage else None)
