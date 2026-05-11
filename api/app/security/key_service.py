"""High-level helpers for storing + retrieving user API keys.

These wrap `encryption.py` and the SQLAlchemy models so callers don't
have to think about envelope encryption every time they touch a key.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.api_key import ApiKeyLLM, LLMProvider
from app.security.encryption import (
    EncryptionError,
    decrypt_secret,
    encrypt_secret,
)


class KeyServiceError(Exception):
    pass


async def store_llm_key(
    db: AsyncSession,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    provider: LLMProvider,
    plaintext: str,
    label: str | None = None,
) -> ApiKeyLLM:
    """Encrypt + upsert an LLM key. Returns the persisted row (without plaintext)."""
    try:
        enc = encrypt_secret(plaintext, settings.MASTER_KEK.get_secret_value())
    except EncryptionError as exc:
        raise KeyServiceError(f"Encryption failed: {exc}") from exc

    # Upsert: one row per (user, provider). If exists, replace.
    stmt = select(ApiKeyLLM).where(
        ApiKeyLLM.user_id == user_id, ApiKeyLLM.provider == provider
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing is not None:
        existing.encrypted_key = enc.encrypted_key
        existing.encrypted_dek = enc.encrypted_dek
        existing.nonce = enc.nonce
        existing.salt = enc.salt
        existing.last4 = enc.last4
        existing.label = label
        existing.last_used = None
        row = existing
    else:
        row = ApiKeyLLM(
            user_id=user_id,
            provider=provider,
            encrypted_key=enc.encrypted_key,
            encrypted_dek=enc.encrypted_dek,
            nonce=enc.nonce,
            salt=enc.salt,
            last4=enc.last4,
            label=label,
        )
        db.add(row)

    await db.flush()
    return row


async def get_llm_key_plaintext(
    db: AsyncSession,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    provider: LLMProvider,
) -> str:
    """Fetch + decrypt a user's LLM key. Returns plaintext.

    Plaintext must never leave the calling request. Callers are expected
    to pass it directly to a provider client and discard it.
    """
    stmt = select(ApiKeyLLM).where(
        ApiKeyLLM.user_id == user_id, ApiKeyLLM.provider == provider
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise KeyServiceError(f"No key set for provider '{provider.value}'.")
    plaintext = decrypt_secret(
        row.encrypted_key,
        row.encrypted_dek,
        row.nonce,
        row.salt,
        settings.MASTER_KEK.get_secret_value(),
    )
    row.last_used = datetime.utcnow()
    return plaintext


async def list_llm_keys(
    db: AsyncSession, *, user_id: uuid.UUID
) -> list[ApiKeyLLM]:
    """List all LLM keys for a user (ciphertext only, never decrypt)."""
    stmt = select(ApiKeyLLM).where(ApiKeyLLM.user_id == user_id).order_by(
        ApiKeyLLM.created_at.desc()
    )
    return list((await db.execute(stmt)).scalars().all())


async def delete_llm_key(
    db: AsyncSession, *, user_id: uuid.UUID, key_id: uuid.UUID
) -> bool:
    """Delete an LLM key. Returns True if the row existed and was deleted."""
    row = await db.get(ApiKeyLLM, key_id)
    if row is None or row.user_id != user_id:
        return False
    await db.delete(row)
    await db.flush()
    return True
