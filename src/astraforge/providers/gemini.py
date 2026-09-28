"""Google Gemini provider adapter."""

from google import genai
from astraforge.config import settings
from astraforge.providers.base import ModelProvider, ModelRequest, ModelResponse

class GeminiProvider(ModelProvider):
    name = "gemini"

    def __init__(self, api_key: str | None = None) -> None:
        self._client = genai.Client(api_key=api_key or settings.gemini_api_key)

    async def generate(self, request: ModelRequest) -> ModelResponse:
        result = await self._client.aio.models.generate_content(
            model=request.model or settings.gemini_default_model,
            contents=request.prompt,
            config={"system_instruction": request.system_prompt,
                    "temperature": request.temperature,
                    "max_output_tokens": request.max_tokens},
        )
        return ModelResponse(text=result.text or "", provider=self.name,
                             model=request.model or settings.gemini_default_model)
