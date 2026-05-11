"""Google Gemini provider client.

`google-generativeai` is sync-first; we wrap its sync streaming iterator
with `asyncio.to_thread` to drain it from async land without blocking
the event loop. Per-chunk overhead is fine because chunks are small.

Token counts come from `usage_metadata` on the final response candidate.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import google.generativeai as genai

from app.llm_gateway.base_client import LLMClient
from app.llm_gateway.pricing import compute_cost
from app.llm_gateway.schemas import ChatRequest, StreamChunk, UsageSummary


def _gemini_history(messages: list, system: str | None) -> tuple[list[dict[str, Any]], str | None]:
    """Convert our Message list into Gemini's `contents` shape.

    Gemini uses `role="user"` / `role="model"` (not "assistant"). System
    prompts are passed separately via `system_instruction`.
    """
    out: list[dict[str, Any]] = []
    for m in messages:
        role = m.role.value if hasattr(m.role, "value") else m.role
        gem_role = "model" if role == "assistant" else "user"
        out.append({"role": gem_role, "parts": [{"text": m.content}]})
    return out, system


class GoogleClient(LLMClient):
    provider_name = "google"

    def __init__(self, api_key: str) -> None:
        super().__init__(api_key)
        # Per-request configure — genai stores key in a module global, so
        # we have to set it on every call to avoid races between users.
        # In practice we instantiate the SDK with key at request time.
        self._configured_key = api_key

    async def stream(self, req: ChatRequest) -> AsyncIterator[StreamChunk]:
        try:
            genai.configure(api_key=self._configured_key)
            history, system = _gemini_history(req.messages, req.system)

            model = genai.GenerativeModel(
                model_name=req.model,
                system_instruction=system,
                generation_config={
                    "max_output_tokens": req.max_tokens,
                    "temperature": req.temperature,
                },
            )

            # genai streaming is sync; iterate in a thread to avoid blocking.
            def _iter() -> Any:
                return model.generate_content(history, stream=True)

            response = await asyncio.to_thread(_iter)

            prompt_tokens = 0
            completion_tokens = 0

            def _drain() -> list:
                chunks: list[dict] = []
                for chunk in response:
                    text = getattr(chunk, "text", None)
                    if text:
                        chunks.append({"type": "text", "delta": text})
                # usage_metadata is on the final aggregated response
                usage = getattr(response, "usage_metadata", None)
                if usage:
                    chunks.append({"type": "_usage_meta", "prompt": usage.prompt_token_count, "completion": usage.candidates_token_count})
                return chunks

            collected = await asyncio.to_thread(_drain)
            for c in collected:
                if c["type"] == "text":
                    yield StreamChunk(type="text", delta=c["delta"])
                else:
                    prompt_tokens = c["prompt"]
                    completion_tokens = c["completion"]

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
            yield StreamChunk(type="error", error=f"Google: {exc}")
            yield StreamChunk(type="done")
