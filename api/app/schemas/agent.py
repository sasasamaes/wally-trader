"""Request/response schemas for the agents API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.api_key import LLMProvider


class AgentRunRequest(BaseModel):
    """Body of `POST /api/v1/agents/{name}/run`."""

    model_config = ConfigDict(use_enum_values=True)

    provider: LLMProvider
    model: str = Field(description="Provider-specific model id, e.g. claude-sonnet-4-6")
    input: dict[str, Any] = Field(
        default_factory=dict,
        description="Agent-specific input payload (symbol, bars, etc.).",
    )
    profile_id: str | None = Field(
        default=None, description="Optional profile UUID for context isolation."
    )
    temperature: float = Field(default=0.4, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=64, le=16_384)


class AgentMetaResponse(BaseModel):
    """`GET /api/v1/agents` — list available agents."""

    name: str
    description: str
    input_schema: dict[str, Any]
    requires_profile: bool


class AgentRunSummary(BaseModel):
    """`GET /api/v1/agents/runs/{id}` — completed run."""

    id: str
    agent_name: str
    status: str
    provider: str | None
    model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    cost_usd: float | None
    duration_ms: int | None
    output_md: str | None
    error: str | None


# Streaming envelope (SSE) — keep stable; the frontend depends on this shape.
class SSEEvent(BaseModel):
    """Server-Sent Event payload."""

    type: Literal["text", "usage", "error", "done", "run_started"]
    delta: str | None = None
    run_id: str | None = None
    usage: dict[str, Any] | None = None
    error: str | None = None
