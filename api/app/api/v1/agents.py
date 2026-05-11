"""Agents API — POST /api/v1/agents/{name}/run streaming via SSE.

Server-Sent Events are wire-compatible with `fetch` + `ReadableStream` in
modern browsers and trivially proxied. We use them instead of WebSockets
for agent runs because there's no client→server message after the request
body — the client just consumes a unidirectional stream of tokens.

Each event is `data: <json>\\n\\n` per the SSE spec.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.agents import AGENTS, get_agent
from app.deps import get_current_user, get_db_session, get_llm_gateway
from app.llm_gateway.router import LLMGateway
from app.models.agent_run import AgentRun
from app.models.api_key import LLMProvider
from app.models.user import User
from app.schemas.agent import AgentMetaResponse, AgentRunRequest, AgentRunSummary

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentMetaResponse])
async def list_agents() -> list[AgentMetaResponse]:
    """List all registered agents and their input schemas."""
    return [
        AgentMetaResponse(
            name=cls.name,
            description=cls.description,
            input_schema=cls.input_schema,
            requires_profile=getattr(cls, "requires_profile", False),
        )
        for cls in AGENTS.values()
    ]


@router.post(
    "/{name}/run",
    status_code=status.HTTP_200_OK,
    response_class=EventSourceResponse,
    responses={
        200: {
            "description": "Server-Sent Events stream",
            "content": {"text/event-stream": {}},
        },
        404: {"description": "Unknown agent name"},
    },
)
async def run_agent(
    body: AgentRunRequest,
    name: str = Path(..., description="Agent name from /agents list"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> EventSourceResponse:
    """Run an agent and stream output via SSE.

    Event shape: `data: {"type": "...", "payload": {...}}`

    Event types (in order):
    - `run_started` — `{"run_id": "<uuid>", "agent": "<name>"}`
    - `text` — `{"delta": "<incremental text>"}`
    - `usage` — `{"prompt_tokens": ..., "cost_usd": ...}`
    - `done` — `{}`
    - `error` — `{"error": "..."}`  (terminal)
    """
    agent = get_agent(name, db, gateway)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown agent '{name}'"
        )

    profile_uuid: uuid.UUID | None = None
    if body.profile_id:
        try:
            profile_uuid = uuid.UUID(body.profile_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid profile_id"
            ) from exc

    # `provider` is auto-converted to LLMProvider by Pydantic via use_enum_values
    provider = (
        body.provider
        if isinstance(body.provider, LLMProvider)
        else LLMProvider(body.provider)
    )

    async def event_stream() -> AsyncIterator[dict]:
        async for event_type, payload in agent.run(
            user=user,
            provider=provider,
            model=body.model,
            payload=body.input,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            profile_id=profile_uuid,
        ):
            yield {
                "event": event_type,
                "data": json.dumps({"type": event_type, **payload}),
            }

    return EventSourceResponse(event_stream())


@router.get("/runs/{run_id}", response_model=AgentRunSummary)
async def get_run(
    run_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AgentRunSummary:
    """Fetch a completed (or in-flight) agent run by id."""
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid run_id"
        ) from exc

    stmt = select(AgentRun).where(
        AgentRun.id == run_uuid, AgentRun.user_id == user.id
    )
    run = (await db.execute(stmt)).scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
        )
    return AgentRunSummary(
        id=str(run.id),
        agent_name=run.agent_name,
        status=run.status.value,
        provider=run.llm_provider.value if run.llm_provider else None,
        model=run.model,
        prompt_tokens=run.prompt_tokens,
        completion_tokens=run.completion_tokens,
        cost_usd=float(run.cost_usd) if run.cost_usd is not None else None,
        duration_ms=run.duration_ms,
        output_md=run.output_md,
        error=run.error,
    )
