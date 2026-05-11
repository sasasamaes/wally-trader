"""Keys API — manage BYOK LLM keys per user."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.deps import get_current_user, get_db_session, get_settings_dep
from app.models.api_key import LLMProvider
from app.models.user import User
from app.schemas.key import LLMKeyCreate, LLMKeyView
from app.security.key_service import (
    KeyServiceError,
    delete_llm_key,
    list_llm_keys,
    store_llm_key,
)

router = APIRouter(prefix="/keys", tags=["keys"])


@router.get("/llm", response_model=list[LLMKeyView])
async def list_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[LLMKeyView]:
    rows = await list_llm_keys(db, user_id=user.id)
    return [
        LLMKeyView(
            id=str(r.id),
            provider=r.provider.value,
            last4=r.last4,
            label=r.label,
            created_at=r.created_at,
            last_used=r.last_used,
        )
        for r in rows
    ]


@router.post(
    "/llm",
    response_model=LLMKeyView,
    status_code=status.HTTP_201_CREATED,
)
async def add_key(
    body: LLMKeyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dep),
) -> LLMKeyView:
    """Store an encrypted LLM key. Overwrites any existing key for the same provider."""
    provider = (
        body.provider
        if isinstance(body.provider, LLMProvider)
        else LLMProvider(body.provider)
    )
    try:
        row = await store_llm_key(
            db,
            settings,
            user_id=user.id,
            provider=provider,
            plaintext=body.api_key,
            label=body.label,
        )
    except KeyServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return LLMKeyView(
        id=str(row.id),
        provider=row.provider.value,
        last4=row.last4,
        label=row.label,
        created_at=row.created_at,
        last_used=row.last_used,
    )


@router.delete("/llm/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        key_uuid = uuid.UUID(key_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid key_id"
        ) from exc
    deleted = await delete_llm_key(db, user_id=user.id, key_id=key_uuid)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Key not found"
        )
