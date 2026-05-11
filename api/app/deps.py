"""FastAPI dependency factories.

Imported by every route module. Keep this lean — heavy logic belongs in
services, not in dependencies (deps run on every request).

`get_current_user` is stubbed for Phase 1 (returns a demo user via DB lookup
by Clerk-issued JWT, or a header-provided UUID for tests). Real Clerk JWT
verification lands in Phase 1.5 once we wire the Clerk webhook.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.llm_gateway.router import LLMGateway
from app.models.user import User


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """Re-exported under a stable name for routes."""
    async for session in get_db():
        yield session


async def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_user(
    db: AsyncSession = Depends(get_db_session),
    x_user_id: str | None = Header(default=None, description="Dev-only override"),
) -> User:
    """Return the authenticated user.

    Phase 1: trusts the `X-User-Id` header (UUID). This is acceptable for
    local dev + the early beta because the API isn't yet exposed to the
    public internet. In Phase 1.5 we'll require a verified Clerk JWT and
    drop this header path entirely.

    Tests pass `X-User-Id` directly.
    """
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header (Clerk JWT verification lands in Phase 1.5)",
        )
    try:
        user_uuid = uuid.UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-User-Id is not a valid UUID",
        ) from exc

    stmt = select(User).where(User.id == user_uuid)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user"
        )
    return user


async def get_llm_gateway(
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dep),
) -> LLMGateway:
    return LLMGateway(db, settings)
