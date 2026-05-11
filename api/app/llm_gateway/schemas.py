"""Shared types for the LLM Gateway.

These types are provider-agnostic. Each provider client converts to/from
its SDK-specific shapes inside its own module — agents and the rest of
the app see only this normalized surface.
"""

from __future__ import annotations

import enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Role(str, enum.Enum):
    system = "system"
    user = "user"
    assistant = "assistant"


class Message(BaseModel):
    """A single turn in a chat conversation."""

    model_config = ConfigDict(use_enum_values=True)

    role: Role
    content: str


class UsageSummary(BaseModel):
    """Token + cost accounting for a single completed call.

    Provided in the final stream chunk (`type="usage"`). Cost is computed
    by the gateway, not the provider, so the user always sees what we'll
    actually bill them.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    provider: str
    model: str


class StreamChunk(BaseModel):
    """One unit emitted by `LLMGateway.stream()`.

    `type` discriminates the payload:
    - `"text"`: incremental assistant text in `delta`
    - `"usage"`: final accounting in `usage`
    - `"error"`: provider or gateway-level failure in `error`
    - `"done"`: clean end of stream (no further chunks follow)
    """

    type: Literal["text", "usage", "error", "done"]
    delta: str | None = None
    usage: UsageSummary | None = None
    error: str | None = None


class ChatRequest(BaseModel):
    """Input to `LLMGateway.stream()`.

    `system` is split out from `messages` because Anthropic, OpenAI, and
    Google all model the system prompt differently. The gateway handles
    the per-provider wiring.
    """

    messages: list[Message] = Field(min_length=1)
    system: str | None = None
    model: str
    max_tokens: int = 2048
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
