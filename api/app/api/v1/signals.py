"""Signals API — CRUD + filters + stats.

The signal log is the heart of the trader's history. Every entry the
user (or an agent) logged via the bitunix pipeline ends up here. Filters
mirror what the CLI `signals_received.md` viewer offers: symbol, side,
outcome, date range.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db_session
from app.models.profile import Profile
from app.models.signal import (
    Signal,
    SignalOutcome,
    SignalSide,
    SignalVerdict,
)
from app.models.user import User
from app.schemas.signal import (
    SignalCreate,
    SignalList,
    SignalUpdateOutcome,
    SignalView,
)
from app.services.metrics import compute_signal_stats

router = APIRouter(prefix="/signals", tags=["signals"])


def _serialize(s: Signal) -> SignalView:
    return SignalView(
        id=str(s.id),
        profile_id=str(s.profile_id),
        symbol=s.symbol,
        side=s.side.value if hasattr(s.side, "value") else s.side,
        entry=float(s.entry),
        sl=float(s.sl) if s.sl is not None else None,
        tp1=float(s.tp1) if s.tp1 is not None else None,
        tp2=float(s.tp2) if s.tp2 is not None else None,
        tp3=float(s.tp3) if s.tp3 is not None else None,
        leverage=s.leverage,
        source=s.source,
        verdict=s.verdict.value if s.verdict else None,
        decision=s.decision,
        size_pct=s.size_pct,
        outcome=s.outcome.value if hasattr(s.outcome, "value") else s.outcome,
        exit_price=float(s.exit_price) if s.exit_price is not None else None,
        exit_reason=s.exit_reason,
        pnl_usd=float(s.pnl_usd) if s.pnl_usd is not None else None,
        duration_h=s.duration_h,
        multifactor_score=s.multifactor_score,
        ml_score=s.ml_score,
        regime=s.regime,
        learning=s.learning,
        opened_at=s.opened_at,
        closed_at=s.closed_at,
    )


async def _resolve_profile(
    db: AsyncSession, user: User, profile_id: str
) -> Profile:
    try:
        pid = uuid.UUID(profile_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid profile_id"
        ) from exc
    stmt = select(Profile).where(Profile.id == pid, Profile.user_id == user.id)
    p = (await db.execute(stmt)).scalar_one_or_none()
    if p is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    return p


@router.get("", response_model=SignalList)
async def list_signals(
    profile_id: str = Query(..., description="Profile UUID"),
    symbol: str | None = Query(default=None),
    side: SignalSide | None = Query(default=None),
    outcome: SignalOutcome | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SignalList:
    profile = await _resolve_profile(db, user, profile_id)

    conds = [Signal.profile_id == profile.id]
    if symbol:
        conds.append(Signal.symbol == symbol)
    if side:
        conds.append(Signal.side == side)
    if outcome:
        conds.append(Signal.outcome == outcome)
    if from_date:
        conds.append(Signal.opened_at >= from_date)
    if to_date:
        conds.append(Signal.opened_at <= to_date)

    stmt = (
        select(Signal)
        .where(and_(*conds))
        .order_by(Signal.opened_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    stats = await compute_signal_stats(db, profile_id=profile.id)
    return SignalList(
        signals=[_serialize(s) for s in rows],
        stats=stats,
        total=len(rows),
    )


@router.post("", response_model=SignalView, status_code=status.HTTP_201_CREATED)
async def create_signal(
    body: SignalCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SignalView:
    profile = await _resolve_profile(db, user, body.profile_id)
    side = body.side if isinstance(body.side, SignalSide) else SignalSide(body.side)
    verdict = None
    if body.verdict is not None:
        verdict = (
            body.verdict
            if isinstance(body.verdict, SignalVerdict)
            else SignalVerdict(body.verdict)
        )

    s = Signal(
        profile_id=profile.id,
        symbol=body.symbol,
        side=side,
        entry=body.entry,
        sl=body.sl,
        tp1=body.tp1,
        tp2=body.tp2,
        tp3=body.tp3,
        leverage=body.leverage,
        source=body.source,
        verdict=verdict,
        multifactor_score=body.multifactor_score,
        ml_score=body.ml_score,
        regime=body.regime,
        filters_4_count=body.filters_4_count,
        pillars_4_count=body.pillars_4_count,
        saturday=body.saturday,
        opened_at=body.opened_at or datetime.utcnow(),
        outcome=SignalOutcome.pending,
        extra=body.extra,
    )
    db.add(s)
    await db.flush()
    return _serialize(s)


@router.patch("/{signal_id}/outcome", response_model=SignalView)
async def update_outcome(
    signal_id: str,
    body: SignalUpdateOutcome,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SignalView:
    try:
        sid = uuid.UUID(signal_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signal_id"
        ) from exc

    # User-scope guard: join through profile
    stmt = (
        select(Signal)
        .join(Profile, Profile.id == Signal.profile_id)
        .where(Signal.id == sid, Profile.user_id == user.id)
    )
    s = (await db.execute(stmt)).scalar_one_or_none()
    if s is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found"
        )

    outcome = (
        body.outcome
        if isinstance(body.outcome, SignalOutcome)
        else SignalOutcome(body.outcome)
    )
    s.outcome = outcome
    s.exit_price = body.exit_price
    s.exit_reason = body.exit_reason
    s.pnl_usd = Decimal(str(body.pnl_usd))
    s.duration_h = body.duration_h
    s.learning = body.learning
    s.closed_at = body.closed_at or datetime.utcnow()

    # Update profile capital with realized PnL
    profile = await db.get(Profile, s.profile_id)
    if profile is not None and body.pnl_usd:
        profile.capital_current = float(profile.capital_current) + body.pnl_usd

    await db.flush()
    return _serialize(s)


@router.get("/{signal_id}", response_model=SignalView)
async def get_signal(
    signal_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SignalView:
    try:
        sid = uuid.UUID(signal_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signal_id"
        ) from exc

    stmt = (
        select(Signal)
        .join(Profile, Profile.id == Signal.profile_id)
        .where(Signal.id == sid, Profile.user_id == user.id)
    )
    s = (await db.execute(stmt)).scalar_one_or_none()
    if s is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found"
        )
    return _serialize(s)
