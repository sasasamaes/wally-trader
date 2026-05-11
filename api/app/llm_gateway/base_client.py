"""Abstract base for provider clients.

Each provider (Anthropic, OpenAI, Google, Ollama) implements `stream()`
returning an async iterator of `StreamChunk`. The final yielded chunk
must be either `type="usage"` followed by `type="done"`, or `type="error"`
followed by `type="done"`.

We hide all SDK-specific request shaping behind this surface so agent
code stays provider-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.llm_gateway.schemas import ChatRequest, StreamChunk


class LLMClient(ABC):
    """Provider client contract."""

    provider_name: str

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @abstractmethod
    async def stream(self, req: ChatRequest) -> AsyncIterator[StreamChunk]:
        """Stream a chat completion. Must always yield a final `done` chunk."""
        ...
