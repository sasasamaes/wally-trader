"""API v1 router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.agents import router as agents_router
from app.api.v1.equity import router as equity_router
from app.api.v1.keys import router as keys_router
from app.api.v1.profiles import router as profiles_router
from app.api.v1.signals import router as signals_router

router = APIRouter()
router.include_router(agents_router)
router.include_router(keys_router)
router.include_router(profiles_router)
router.include_router(signals_router)
router.include_router(equity_router)


@router.get("/ping", tags=["meta"])
async def ping() -> dict[str, str]:
    return {"pong": "ok"}
