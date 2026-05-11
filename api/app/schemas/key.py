"""Schemas for managing user API keys (LLM + broker)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.api_key import BrokerName, LLMProvider


class LLMKeyCreate(BaseModel):
    """`POST /api/v1/keys/llm`."""

    model_config = ConfigDict(use_enum_values=True)

    provider: LLMProvider
    api_key: str = Field(min_length=8, description="Raw API key — never logged.")
    label: str | None = Field(default=None, max_length=80)


class LLMKeyView(BaseModel):
    """`GET /api/v1/keys/llm` — never exposes the plaintext, only last4."""

    id: str
    provider: str
    last4: str
    label: str | None
    created_at: datetime
    last_used: datetime | None


class BrokerKeyCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    broker: BrokerName
    api_key: str = Field(min_length=8)
    api_secret: str | None = Field(default=None, min_length=8)
    label: str | None = Field(default=None, max_length=80)


class BrokerKeyView(BaseModel):
    id: str
    broker: str
    last4: str
    label: str | None
    read_only_verified: bool
    created_at: datetime
    last_synced: datetime | None
