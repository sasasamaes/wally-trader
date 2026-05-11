"""Schemas for equity curves + daily summaries."""

from __future__ import annotations

from datetime import date as _date

from pydantic import BaseModel, ConfigDict


class EquityPointView(BaseModel):
    """One row in the equity series — shape that Lightweight Charts expects."""

    model_config = ConfigDict(populate_by_name=True)

    date: _date  # serialized as ISO yyyy-mm-dd
    equity: float
    daily_pnl_pct: float | None = None
    dd_pct: float | None = None
    outperformance_vs_hodl_pct: float | None = None
    win_rate_pct: float | None = None
    trade_count: int = 0


class EquitySummary(BaseModel):
    """Latest snapshot + computed cumulative metrics."""

    capital_initial: float
    capital_current: float
    total_pnl_usd: float
    total_pnl_pct: float
    max_dd_pct: float | None
    trading_days: int
    last_updated: _date | None


class EquitySeriesResponse(BaseModel):
    points: list[EquityPointView]
    summary: EquitySummary
