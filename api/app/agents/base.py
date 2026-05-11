"""Base agent: shared plumbing for run lifecycle, LLM streaming, and DB recording.

Every concrete agent subclasses `BaseAgent` and implements:
- `name` + `description` (registry metadata)
- `system_prompt()` — instructions for the LLM
- `user_prompt(input)` — formats the user request from the input dict
- (optional) `precompute(input)` — pure-Python work that happens BEFORE
  the LLM is called, results passed into `user_prompt()` as context.

The base handles AgentRun row creation/finalization, streaming through
`LLMGateway`, and translating the gateway's `StreamChunk` into our API
`SSEEvent` shape.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log
from app.llm_gateway.router import LLMGateway
from app.llm_gateway.schemas import ChatRequest, Message, Role, StreamChunk
from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.api_key import LLMProvider
from app.models.user import User


class BaseAgent(ABC):
    """Subclass to define a new agent."""

    name: str
    description: str
    requires_profile: bool = False
    input_schema: dict[str, Any] = {}

    def __init__(self, db: AsyncSession, gateway: LLMGateway) -> None:
        self._db = db
        self._gateway = gateway

    @abstractmethod
    def system_prompt(self) -> str:
        ...

    @abstractmethod
    def user_prompt(self, payload: dict[str, Any], precomputed: dict[str, Any]) -> str:
        ...

    async def precompute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Optional sync/async work before the LLM is called.

        Override to load market data, run regime detection, etc. Return a
        dict that `user_prompt()` can format into the LLM context.
        """
        return {}

    async def run(
        self,
        *,
        user: User,
        provider: LLMProvider,
        model: str,
        payload: dict[str, Any],
        temperature: float = 0.4,
        max_tokens: int = 2048,
        profile_id: uuid.UUID | None = None,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        """Execute the agent, yielding `(event_type, event_payload)` tuples.

        Event types: `run_started`, `text`, `usage`, `error`, `done`.
        """
        # Open AgentRun row
        run = AgentRun(
            user_id=user.id,
            profile_id=profile_id,
            agent_name=self.name,
            input=payload,
            status=AgentRunStatus.running,
        )
        self._db.add(run)
        await self._db.flush()
        log.info("agent.run.started", agent=self.name, run_id=str(run.id), user_id=str(user.id))

        yield "run_started", {"run_id": str(run.id), "agent": self.name}

        start = time.perf_counter()
        try:
            precomputed = await self.precompute(payload)
            req = ChatRequest(
                messages=[
                    Message(role=Role.user, content=self.user_prompt(payload, precomputed))
                ],
                system=self.system_prompt(),
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            async for chunk in self._gateway.stream(
                user_id=user.id,
                provider=provider,
                request=req,
                agent_name=self.name,
                agent_run_id=run.id,
            ):
                async for event in self._chunk_to_events(chunk):
                    yield event

            run.duration_ms = int((time.perf_counter() - start) * 1000)
            if run.status != AgentRunStatus.completed:
                # Gateway only sets `completed` on usage; if we got `error` first,
                # mark accordingly.
                run.status = AgentRunStatus.failed if run.error else AgentRunStatus.completed
        except Exception as exc:  # noqa: BLE001
            run.status = AgentRunStatus.failed
            run.error = str(exc)
            run.duration_ms = int((time.perf_counter() - start) * 1000)
            log.error("agent.run.exception", agent=self.name, run_id=str(run.id), error=str(exc))
            yield "error", {"error": str(exc)}
            yield "done", {}

    async def _chunk_to_events(
        self, chunk: StreamChunk
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        """Translate a gateway StreamChunk into one or more SSE events."""
        if chunk.type == "text" and chunk.delta is not None:
            yield "text", {"delta": chunk.delta}
        elif chunk.type == "usage" and chunk.usage is not None:
            yield "usage", chunk.usage.model_dump()
        elif chunk.type == "error" and chunk.error is not None:
            yield "error", {"error": chunk.error}
        elif chunk.type == "done":
            yield "done", {}


def get_agent(
    name: str, db: AsyncSession, gateway: LLMGateway
) -> BaseAgent | None:
    """Factory: look up an agent class by name and instantiate it.

    Imports `AGENTS` lazily to avoid circular-import headaches.
    """
    from app.agents import AGENTS

    cls = AGENTS.get(name)
    if cls is None:
        return None
    return cls(db, gateway)
