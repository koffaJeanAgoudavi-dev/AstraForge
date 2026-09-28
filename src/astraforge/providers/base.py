"""Provider contracts used by the model router."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelRequest:
    prompt: str
    system_prompt: str | None = None
    model: str | None = None
    temperature: float = 0.2
    max_tokens: int = 4096


@dataclass(frozen=True)
class ModelResponse:
    text: str
    provider: str
    model: str
    usage: dict[str, Any] | None = None


class ModelProvider(ABC):
    """Interface every model provider adapter must implement."""

    name: str

    @abstractmethod
    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate a response from a model."""
        raise NotImplementedError
