"""Schemas for trading signals."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.signal import SignalOutcome, SignalSide, SignalVerdict


class SignalBase(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    symbol: str = Field(min_length=1, max_length=32)
    side: SignalSide
    entry: float = Field(gt=0)
    sl: float | None = Field(default=None, gt=0)
    tp1: float | None = Field(default=None, gt=0)
    tp2: float | None = Field(default=None, gt=0)
    tp3: float | None = Field(default=None, gt=0)
    leverage: int | None = Field(default=None, ge=1, le=125)


class SignalCreate(SignalBase):
    profile_id: str
    source: str = Field(default="self_generated", max_length=64)
    verdict: SignalVerdict | None = None
    multifactor_score: float | None = None
    ml_score: float | None = None
    regime: str | None = None
    filters_4_count: int | None = Field(default=None, ge=0, le=4)
    pillars_4_count: int | None = Field(default=None, ge=0, le=4)
    saturday: bool = False
    opened_at: datetime | None = None  # default = now
    extra: dict[str, Any] = Field(default_factory=dict)


class SignalUpdateOutcome(BaseModel):
    """`PATCH /signals/{id}/outcome` — close a signal."""

    model_config = ConfigDict(use_enum_values=True)

    outcome: SignalOutcome
    exit_price: float = Field(gt=0)
    exit_reason: str | None = Field(default=None, max_length=64)
    pnl_usd: float
    duration_h: float | None = Field(default=None, ge=0)
    learning: str | None = None
    closed_at: datetime | None = None


class SignalView(SignalBase):
    id: str
    profile_id: str
    source: str
    verdict: str | None
    decision: str | None
    size_pct: float | None
    outcome: str
    exit_price: float | None
    exit_reason: str | None
    pnl_usd: float | None
    duration_h: float | None
    multifactor_score: float | None
    ml_score: float | None
    regime: str | None
    learning: str | None
    opened_at: datetime
    closed_at: datetime | None


class SignalStats(BaseModel):
    """Aggregated stats for a set of signals (e.g. one profile)."""

    total: int
    open: int
    closed: int
    wins: int
    losses: int
    win_rate_pct: float
    avg_win_usd: float
    avg_loss_usd: float
    total_pnl_usd: float
    profit_factor: float | None  # None when no losses


class SignalList(BaseModel):
    signals: list[SignalView]
    stats: SignalStats
    total: int
