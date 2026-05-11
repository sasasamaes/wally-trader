"""OpenAI provider client.

OpenAI's Chat Completions streaming API yields chunks where:
- The last chunk before `[DONE]` has `usage` populated (when we pass
  `stream_options={"include_usage": True}`).
- All earlier chunks have `usage=None` and a single content delta.

The system prompt is a regular message with `role="system"` (unlike
Anthropic's top-level `system` parameter).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.llm_gateway.base_client import LLMClient
from app.llm_gateway.pricing import compute_cost
from app.llm_gateway.schemas import ChatRequest, StreamChunk, UsageSummary


class OpenAIClient(LLMClient):
    provider_name = "openai"

    def __init__(self, api_key: str) -> None:
        super().__init__(api_key)
        self._sdk = AsyncOpenAI(api_key=api_key)

    async def stream(self, req: ChatRequest) -> AsyncIterator[StreamChunk]:
        prompt_tokens = 0
        completion_tokens = 0
        try:
            messages: list[dict] = []
            if req.system:
                messages.append({"role": "system", "content": req.system})
            messages.extend(
                {"role": m.role.value if hasattr(m.role, "value") else m.role,
                 "content": m.content}
                for m in req.messages
            )

            stream = await self._sdk.chat.completions.create(
                model=req.model,
                messages=messages,
                max_tokens=req.max_tokens,
                temperature=req.temperature,
                stream=True,
                stream_options={"include_usage": True},
            )

            async for chunk in stream:
                # Token counts ride on the last chunk
                if chunk.usage is not None:
                    prompt_tokens = chunk.usage.prompt_tokens
                    completion_tokens = chunk.usage.completion_tokens
                # Content deltas
                for choice in chunk.choices or []:
                    delta = choice.delta.content
                    if delta:
                        yield StreamChunk(type="text", delta=delta)

            cost = compute_cost(
                self.provider_name, req.model, prompt_tokens, completion_tokens
            )
            yield StreamChunk(
                type="usage",
                usage=UsageSummary(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    cost_usd=cost,
                    provider=self.provider_name,
                    model=req.model,
                ),
            )
            yield StreamChunk(type="done")
        except Exception as exc:  # noqa: BLE001
            yield StreamChunk(type="error", error=f"OpenAI: {exc}")
            yield StreamChunk(type="done")
