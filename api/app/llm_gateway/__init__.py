"""LLM Gateway — BYOK provider abstraction.

The gateway is the single point through which agent code talks to any LLM.
The agent code says "give me a stream from provider X with model Y and these
messages" and the gateway handles:

- Looking up + decrypting the user's API key for that provider
- Routing to the right SDK (Anthropic / OpenAI / Google / Ollama)
- Yielding stream chunks in a normalized shape
- Recording token usage + cost into the `usage_events` table for billing

Agents must not import provider SDKs directly — that would defeat the
purpose. Always go through `LLMGateway.stream()`.
"""

from app.llm_gateway.router import LLMGateway
from app.llm_gateway.schemas import (
    Message,
    Role,
    StreamChunk,
    UsageSummary,
)

__all__ = ["LLMGateway", "Message", "Role", "StreamChunk", "UsageSummary"]
