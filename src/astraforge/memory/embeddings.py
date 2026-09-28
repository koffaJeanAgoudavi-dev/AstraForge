"""Embedding providers for semantic memory."""

from abc import ABC, abstractmethod

from astraforge.config import settings


class EmbeddingProvider(ABC):
    name: str

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class GeminiEmbeddingProvider(EmbeddingProvider):
    name = "gemini"

    def __init__(self, model: str = "gemini-embedding-2") -> None:
        from google import genai

        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for semantic memory")
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = model or settings.gemini_embedding_model

    async def embed(self, text: str) -> list[float]:
        result = await self.client.aio.models.embed_content(
            model=self.model,
            contents=text,
        )
        return list(result.embeddings[0].values)


def build_embedding_provider() -> EmbeddingProvider | None:
    if settings.gemini_api_key:
        return GeminiEmbeddingProvider()
    return None
