"""Service-layer aggregations.

These functions answer "what's the WR for profile X?" or "what's the max
drawdown across the equity series?" — pure-ish math we want centralized
so routes/agents/workers all use the same definitions.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.equity_point import EquityPoint
from app.models.signal import Signal, SignalOutcome
from app.schemas.equity import EquitySummary
from app.schemas.signal import SignalStats


# Outcomes that count as "closed" for stats. PENDING/CANCELLED don't.
_CLOSED_OUTCOMES = (
    SignalOutcome.tp1,
    SignalOutcome.tp2,
    SignalOutcome.tp3,
    SignalOutcome.sl,
    SignalOutcome.manual,
)


async def compute_signal_stats(
    db: AsyncSession, *, profile_id: uuid.UUID
) -> SignalStats:
    """Aggregate WR / PF / avg win / avg loss over a profile's signals."""
    stmt = select(Signal).where(Signal.profile_id == profile_id)
    rows = list((await db.execute(stmt)).scalars().all())

    total = len(rows)
    open_count = sum(1 for r in rows if r.outcome == SignalOutcome.pending)
    closed = [r for r in rows if r.outcome in _CLOSED_OUTCOMES and r.pnl_usd is not None]
    wins = [r for r in closed if (r.pnl_usd or 0) > 0]
    losses = [r for r in closed if (r.pnl_usd or 0) < 0]

    total_win_usd = sum(float(r.pnl_usd or 0) for r in wins)
    total_loss_usd = sum(float(r.pnl_usd or 0) for r in losses)  # negative

    avg_win = total_win_usd / len(wins) if wins else 0.0
    avg_loss = total_loss_usd / len(losses) if losses else 0.0

    wr_denom = len(wins) + len(losses)
    wr = (len(wins) / wr_denom * 100) if wr_denom else 0.0

    pf: float | None
    if losses:
        pf = total_win_usd / abs(total_loss_usd) if total_loss_usd != 0 else None
    else:
        pf = None  # undefined — caller renders as "—" or "∞"

    return SignalStats(
        total=total,
        open=open_count,
        closed=len(closed),
        wins=len(wins),
        losses=len(losses),
        win_rate_pct=round(wr, 2),
        avg_win_usd=round(avg_win, 4),
        avg_loss_usd=round(avg_loss, 4),
        total_pnl_usd=round(total_win_usd + total_loss_usd, 4),
        profit_factor=round(pf, 3) if pf is not None else None,
    )


async def compute_equity_summary(
    db: AsyncSession, *, profile_id: uuid.UUID, capital_initial: float
) -> EquitySummary:
    """Aggregate the equity curve into a one-line summary."""
    stmt = (
        select(EquityPoint)
        .where(EquityPoint.profile_id == profile_id)
        .order_by(EquityPoint.date.asc())
    )
    points = list((await db.execute(stmt)).scalars().all())

    if not points:
        return EquitySummary(
            capital_initial=capital_initial,
            capital_current=capital_initial,
            total_pnl_usd=0.0,
            total_pnl_pct=0.0,
            max_dd_pct=None,
            trading_days=0,
            last_updated=None,
        )

    capital_current = float(points[-1].equity)
    total_pnl = capital_current - capital_initial
    pct = (total_pnl / capital_initial * 100) if capital_initial else 0.0

    # Max drawdown from rolling peak
    peak = capital_initial
    max_dd = 0.0
    for p in points:
        e = float(p.equity)
        if e > peak:
            peak = e
        if peak > 0:
            dd = (peak - e) / peak * 100
            if dd > max_dd:
                max_dd = dd

    return EquitySummary(
        capital_initial=capital_initial,
        capital_current=capital_current,
        total_pnl_usd=round(total_pnl, 4),
        total_pnl_pct=round(pct, 4),
        max_dd_pct=round(max_dd, 4) if max_dd > 0 else None,
        trading_days=len(points),
        last_updated=points[-1].date,
    )


async def count_signals_for_profile(
    db: AsyncSession, *, profile_id: uuid.UUID
) -> int:
    stmt = select(func.count()).select_from(Signal).where(Signal.profile_id == profile_id)
    return int((await db.execute(stmt)).scalar_one())
