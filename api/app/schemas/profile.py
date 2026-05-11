"""Schemas for profiles + their computed metrics."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.profile import ProfileKind


class ProfileBase(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=120)
    kind: ProfileKind
    capital_initial: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=2, max_length=8)
    config_json: dict[str, Any] = Field(default_factory=dict)
    strategy_json: dict[str, Any] = Field(default_factory=dict)
    rules_json: dict[str, Any] = Field(default_factory=dict)


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(BaseModel):
    """All fields optional — PATCH semantics."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    capital_current: float | None = Field(default=None, gt=0)
    config_json: dict[str, Any] | None = None
    strategy_json: dict[str, Any] | None = None
    rules_json: dict[str, Any] | None = None


class ProfileMetrics(BaseModel):
    """Aggregate metrics computed on demand from signals + equity_points."""

    trade_count: int = 0
    closed_trade_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    win_rate_pct: float = 0.0
    avg_win_usd: float = 0.0
    avg_loss_usd: float = 0.0
    profit_factor: float | None = None  # None when no losses (undefined / inf)
    total_pnl_usd: float = 0.0
    capital_current: float = 0.0
    capital_initial: float = 0.0
    daily_pnl_pct_last: float | None = None
    max_dd_pct: float | None = None


class ProfileView(ProfileBase):
    id: str
    capital_current: float
    created_at: datetime
    updated_at: datetime
    metrics: ProfileMetrics | None = None


class ProfileList(BaseModel):
    profiles: list[ProfileView]
    total: int
