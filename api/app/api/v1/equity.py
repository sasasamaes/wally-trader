"""Equity curve API — one row per profile per day + cumulative summary."""

from __future__ import annotations

import uuid
from datetime import date as _date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db_session
from app.models.equity_point import EquityPoint
from app.models.profile import Profile
from app.models.user import User
from app.schemas.equity import EquityPointView, EquitySeriesResponse
from app.services.metrics import compute_equity_summary

router = APIRouter(prefix="/equity", tags=["equity"])


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


@router.get("", response_model=EquitySeriesResponse)
async def get_equity_series(
    profile_id: str = Query(...),
    from_date: _date | None = Query(default=None),
    to_date: _date | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> EquitySeriesResponse:
    profile = await _resolve_profile(db, user, profile_id)

    conds = [EquityPoint.profile_id == profile.id]
    if from_date:
        conds.append(EquityPoint.date >= from_date)
    if to_date:
        conds.append(EquityPoint.date <= to_date)

    stmt = select(EquityPoint).where(and_(*conds)).order_by(EquityPoint.date.asc())
    rows = list((await db.execute(stmt)).scalars().all())

    points = [
        EquityPointView(
            date=r.date,
            equity=float(r.equity),
            daily_pnl_pct=r.daily_pnl_pct,
            dd_pct=r.dd_pct,
            outperformance_vs_hodl_pct=r.outperformance_vs_hodl_pct,
            win_rate_pct=r.win_rate_pct,
            trade_count=r.trade_count,
        )
        for r in rows
    ]
    summary = await compute_equity_summary(
        db, profile_id=profile.id, capital_initial=float(profile.capital_initial)
    )
    return EquitySeriesResponse(points=points, summary=summary)


class EquityPointUpsert(BaseModel):
    """`POST /equity/upsert` — manually set an equity point for a date."""

    profile_id: str
    date: _date
    equity: float = Field(gt=0)
    daily_pnl_pct: float | None = None
    dd_pct: float | None = None
    win_rate_pct: float | None = None
    trade_count: int = 0


@router.post("/upsert", response_model=EquityPointView, status_code=status.HTTP_200_OK)
async def upsert_equity_point(
    body: EquityPointUpsert,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> EquityPointView:
    profile = await _resolve_profile(db, user, body.profile_id)
    stmt = select(EquityPoint).where(
        EquityPoint.profile_id == profile.id, EquityPoint.date == body.date
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        row = EquityPoint(
            profile_id=profile.id,
            date=body.date,
            equity=body.equity,
            daily_pnl_pct=body.daily_pnl_pct,
            dd_pct=body.dd_pct,
            win_rate_pct=body.win_rate_pct,
            trade_count=body.trade_count,
        )
        db.add(row)
    else:
        row.equity = body.equity
        if body.daily_pnl_pct is not None:
            row.daily_pnl_pct = body.daily_pnl_pct
        if body.dd_pct is not None:
            row.dd_pct = body.dd_pct
        if body.win_rate_pct is not None:
            row.win_rate_pct = body.win_rate_pct
        row.trade_count = body.trade_count

    # Mirror to profile.capital_current if this is the latest date we have
    latest_stmt = (
        select(EquityPoint.date)
        .where(EquityPoint.profile_id == profile.id)
        .order_by(EquityPoint.date.desc())
        .limit(1)
    )
    latest = (await db.execute(latest_stmt)).scalar_one_or_none()
    if latest is None or body.date >= latest:
        profile.capital_current = body.equity

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Equity point conflict",
        ) from exc

    return EquityPointView(
        date=row.date,
        equity=float(row.equity),
        daily_pnl_pct=row.daily_pnl_pct,
        dd_pct=row.dd_pct,
        outperformance_vs_hodl_pct=row.outperformance_vs_hodl_pct,
        win_rate_pct=row.win_rate_pct,
        trade_count=row.trade_count,
    )
