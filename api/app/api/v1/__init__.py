"""API v1 router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

# Sub-routers will be wired in as phases land. Keep the file thin so we
# don't end up with one mega-import that breaks every time a feature
# branch touches an unrelated endpoint.
router = APIRouter()


@router.get("/ping", tags=["meta"])
async def ping() -> dict[str, str]:
    return {"pong": "ok"}
