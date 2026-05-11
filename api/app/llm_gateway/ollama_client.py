"""Ollama provider client.

Talks to a user-hosted Ollama HTTP server. For BYOK we treat the "API
key" field as the **base URL** of the user's Ollama instance (e.g.
`http://localhost:11434` if they ran an ngrok tunnel, or a Tailscale
host). It's not really a key; the storage is the same so reusing the
encrypted-secret column keeps the data model uniform.

We bill 0 USD per token (the user paid for their own GPU). Wally still
charges the base subscription + per-agent-call fee.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from ollama import AsyncClient as OllamaAsyncClient

from app.llm_gateway.base_client import LLMClient
from app.llm_gateway.pricing import compute_cost
from app.llm_gateway.schemas import ChatRequest, StreamChunk, UsageSummary


class OllamaClient(LLMClient):
    provider_name = "ollama"

    def __init__(self, api_key: str) -> None:
        # `api_key` here is the base URL of the user's Ollama instance.
        super().__init__(api_key)
        self._sdk = OllamaAsyncClient(host=api_key)

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

            async for chunk in await self._sdk.chat(
                model=req.model,
                messages=messages,
                stream=True,
                options={
                    "num_predict": req.max_tokens,
                    "temperature": req.temperature,
                },
            ):
                content = chunk.get("message", {}).get("content")
                if content:
                    yield StreamChunk(type="text", delta=content)
                if chunk.get("done"):
                    prompt_tokens = chunk.get("prompt_eval_count", 0) or 0
                    completion_tokens = chunk.get("eval_count", 0) or 0

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
            yield StreamChunk(type="error", error=f"Ollama: {exc}")
            yield StreamChunk(type="done")
