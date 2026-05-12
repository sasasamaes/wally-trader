"""Profiles API — CRUD for trading profiles, user-scoped."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db_session
from app.models.profile import Profile, ProfileKind
from app.models.user import User
from app.schemas.profile import (
    ProfileCreate,
    ProfileList,
    ProfileMetrics,
    ProfileUpdate,
    ProfileView,
)
from app.services.metrics import compute_signal_stats

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _serialize(p: Profile, metrics: ProfileMetrics | None = None) -> ProfileView:
    return ProfileView(
        id=str(p.id),
        slug=p.slug,
        name=p.name,
        kind=p.kind.value if hasattr(p.kind, "value") else p.kind,
        capital_initial=float(p.capital_initial),
        capital_current=float(p.capital_current),
        currency=p.currency,
        config_json=p.config_json,
        strategy_json=p.strategy_json,
        rules_json=p.rules_json,
        created_at=p.created_at,
        updated_at=p.updated_at,
        metrics=metrics,
    )


@router.get("", response_model=ProfileList)
async def list_profiles(
    include_metrics: bool = Query(default=True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProfileList:
    stmt = select(Profile).where(Profile.user_id == user.id).order_by(
        Profile.created_at.asc()
    )
    rows = list((await db.execute(stmt)).scalars().all())

    out: list[ProfileView] = []
    for p in rows:
        m: ProfileMetrics | None = None
        if include_metrics:
            stats = await compute_signal_stats(db, profile_id=p.id)
            m = ProfileMetrics(
                trade_count=stats.total,
                closed_trade_count=stats.closed,
                win_count=stats.wins,
                loss_count=stats.losses,
                win_rate_pct=stats.win_rate_pct,
                avg_win_usd=stats.avg_win_usd,
                avg_loss_usd=stats.avg_loss_usd,
                profit_factor=stats.profit_factor,
                total_pnl_usd=stats.total_pnl_usd,
                capital_current=float(p.capital_current),
                capital_initial=float(p.capital_initial),
            )
        out.append(_serialize(p, m))
    return ProfileList(profiles=out, total=len(out))


@router.post("", response_model=ProfileView, status_code=status.HTTP_201_CREATED)
async def create_profile(
    body: ProfileCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProfileView:
    kind = (
        body.kind if isinstance(body.kind, ProfileKind) else ProfileKind(body.kind)
    )
    p = Profile(
        user_id=user.id,
        slug=body.slug,
        name=body.name,
        kind=kind,
        capital_initial=body.capital_initial,
        capital_current=body.capital_initial,
        currency=body.currency,
        config_json=body.config_json,
        strategy_json=body.strategy_json,
        rules_json=body.rules_json,
    )
    db.add(p)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Profile with slug '{body.slug}' already exists",
        ) from exc
    return _serialize(p)


@router.get("/{slug}", response_model=ProfileView)
async def get_profile(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProfileView:
    stmt = select(Profile).where(Profile.user_id == user.id, Profile.slug == slug)
    p = (await db.execute(stmt)).scalar_one_or_none()
    if p is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    stats = await compute_signal_stats(db, profile_id=p.id)
    metrics = ProfileMetrics(
        trade_count=stats.total,
        closed_trade_count=stats.closed,
        win_count=stats.wins,
        loss_count=stats.losses,
        win_rate_pct=stats.win_rate_pct,
        avg_win_usd=stats.avg_win_usd,
        avg_loss_usd=stats.avg_loss_usd,
        profit_factor=stats.profit_factor,
        total_pnl_usd=stats.total_pnl_usd,
        capital_current=float(p.capital_current),
        capital_initial=float(p.capital_initial),
    )
    return _serialize(p, metrics)


@router.patch("/{slug}", response_model=ProfileView)
async def update_profile(
    slug: str,
    body: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProfileView:
    stmt = select(Profile).where(Profile.user_id == user.id, Profile.slug == slug)
    p = (await db.execute(stmt)).scalar_one_or_none()
    if p is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    if body.name is not None:
        p.name = body.name
    if body.capital_current is not None:
        p.capital_current = body.capital_current
    if body.config_json is not None:
        p.config_json = body.config_json
    if body.strategy_json is not None:
        p.strategy_json = body.strategy_json
    if body.rules_json is not None:
        p.rules_json = body.rules_json
    await db.flush()
    return _serialize(p)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    stmt = select(Profile).where(Profile.user_id == user.id, Profile.slug == slug)
    p = (await db.execute(stmt)).scalar_one_or_none()
    if p is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    await db.delete(p)
    await db.flush()
