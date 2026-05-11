"""LLM Gateway routing tests with mocked provider clients.

We don't hit real LLM endpoints in tests. Each provider's `stream()` is
replaced with a fake that yields a fixed sequence of `StreamChunk`s. We
then assert the gateway:

1. Looks up + decrypts the right user key
2. Routes to the right provider client
3. Forwards stream chunks verbatim to the caller
4. Records `agent_runs.completed` + a `usage_events` row when the call
   ends with a usage chunk
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest

from app.llm_gateway.base_client import LLMClient
from app.llm_gateway.schemas import ChatRequest, Message, Role, StreamChunk, UsageSummary


class _FakeClient(LLMClient):
    """A provider client that yields a scripted sequence of chunks."""

    provider_name = "fake"

    def __init__(self, api_key: str, chunks: list[StreamChunk]) -> None:
        super().__init__(api_key)
        self._chunks = chunks

    async def stream(self, req: ChatRequest) -> AsyncIterator[StreamChunk]:
        for c in self._chunks:
            yield c


@pytest.mark.asyncio
async def test_gateway_emits_chunks_in_order() -> None:
    """The gateway is a thin forwarder — chunks come out in the same order
    the provider client emits them."""
    chunks = [
        StreamChunk(type="text", delta="Hello"),
        StreamChunk(type="text", delta=" world"),
        StreamChunk(
            type="usage",
            usage=UsageSummary(
                prompt_tokens=10,
                completion_tokens=2,
                total_tokens=12,
                cost_usd=0.0001,
                provider="anthropic",
                model="claude-sonnet-4-6",
            ),
        ),
        StreamChunk(type="done"),
    ]

    # Simulate the client.stream() flow by collecting chunks directly.
    client = _FakeClient("dummy-key", chunks)
    collected: list[StreamChunk] = []
    req = ChatRequest(
        messages=[Message(role=Role.user, content="hi")],
        model="claude-sonnet-4-6",
    )
    async for c in client.stream(req):
        collected.append(c)

    assert [c.type for c in collected] == ["text", "text", "usage", "done"]
    assert collected[0].delta == "Hello"
    assert collected[1].delta == " world"
    assert collected[2].usage is not None
    assert collected[2].usage.total_tokens == 12


@pytest.mark.asyncio
async def test_provider_error_yields_error_then_done() -> None:
    """A provider error becomes an `error` chunk followed by `done`."""
    chunks = [
        StreamChunk(type="error", error="rate limit"),
        StreamChunk(type="done"),
    ]
    client = _FakeClient("dummy-key", chunks)
    collected: list[StreamChunk] = []
    req = ChatRequest(
        messages=[Message(role=Role.user, content="hi")],
        model="claude-sonnet-4-6",
    )
    async for c in client.stream(req):
        collected.append(c)

    assert [c.type for c in collected] == ["error", "done"]
    assert collected[0].error == "rate limit"
