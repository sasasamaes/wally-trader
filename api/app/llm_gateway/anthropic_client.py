"""Anthropic provider client.

Uses the official `anthropic` Python SDK in async streaming mode. The SDK
emits typed event objects; we translate them into our normalized
`StreamChunk` shape. Token counts come from the final `message_delta`
event's `usage` field — we pin that to our own pricing table rather than
trusting the SDK's `usage.input_tokens` rounding.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic
from anthropic.types import (
    MessageDeltaEvent,
    MessageStartEvent,
)

from app.llm_gateway.base_client import LLMClient
from app.llm_gateway.pricing import compute_cost
from app.llm_gateway.schemas import ChatRequest, StreamChunk, UsageSummary


class AnthropicClient(LLMClient):
    provider_name = "anthropic"

    def __init__(self, api_key: str) -> None:
        super().__init__(api_key)
        self._sdk = AsyncAnthropic(api_key=api_key)

    async def stream(self, req: ChatRequest) -> AsyncIterator[StreamChunk]:
        prompt_tokens = 0
        completion_tokens = 0
        try:
            kwargs: dict = {
                "model": req.model,
                "max_tokens": req.max_tokens,
                "temperature": req.temperature,
                "messages": [
                    {"role": m.role.value if hasattr(m.role, "value") else m.role,
                     "content": m.content}
                    for m in req.messages
                ],
            }
            if req.system:
                kwargs["system"] = req.system

            async with self._sdk.messages.stream(**kwargs) as stream:
                async for event in stream:
                    if isinstance(event, MessageStartEvent):
                        prompt_tokens = event.message.usage.input_tokens
                    elif isinstance(event, MessageDeltaEvent):
                        completion_tokens = event.usage.output_tokens
                    else:
                        # text_delta events surface via stream.text_stream below
                        pass
                # Drain the text stream — we get incremental text without
                # needing to type-switch on every event
                async for text in stream.text_stream:
                    if text:
                        yield StreamChunk(type="text", delta=text)

                # Final usage from the closed stream
                final_message = await stream.get_final_message()
                prompt_tokens = final_message.usage.input_tokens
                completion_tokens = final_message.usage.output_tokens

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
            yield StreamChunk(type="error", error=f"Anthropic: {exc}")
            yield StreamChunk(type="done")
