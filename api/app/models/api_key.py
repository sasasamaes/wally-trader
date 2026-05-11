"""Encrypted BYOK storage for LLM providers and broker credentials.

Plaintext keys NEVER hit the DB. Each row stores:
- `encrypted_key`: AES-256-GCM ciphertext of the secret
- `encrypted_dek`: the per-user DEK encrypted with the server-side KEK
- `salt`, `nonce`: random per-key for AEAD
- `last4`: last four chars of plaintext for UI display (so the user can
  recognize which key is which without revealing the full secret)
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class LLMProvider(str, enum.Enum):
    anthropic = "anthropic"
    openai = "openai"
    google = "google"
    ollama = "ollama"


class BrokerName(str, enum.Enum):
    bitunix = "bitunix"
    binance = "binance"
    okx = "okx"
    mt5 = "mt5"


class ApiKeyLLM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "api_keys_llm"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_llm_provider"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[LLMProvider] = mapped_column(
        Enum(LLMProvider, name="llm_provider"), nullable=False
    )
    encrypted_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encrypted_dek: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary(12), nullable=False)
    salt: Mapped[bytes] = mapped_column(LargeBinary(16), nullable=False)
    last4: Mapped[str] = mapped_column(String(4), nullable=False)
    label: Mapped[str | None] = mapped_column(String(80))
    last_used: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="llm_keys")


class ApiKeyBroker(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "api_keys_broker"
    __table_args__ = (
        UniqueConstraint("user_id", "broker", "label", name="uq_user_broker_label"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    broker: Mapped[BrokerName] = mapped_column(
        Enum(BrokerName, name="broker_name"), nullable=False
    )
    encrypted_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encrypted_secret: Mapped[bytes | None] = mapped_column(LargeBinary)
    encrypted_dek: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce_key: Mapped[bytes] = mapped_column(LargeBinary(12), nullable=False)
    nonce_secret: Mapped[bytes | None] = mapped_column(LargeBinary(12))
    salt: Mapped[bytes] = mapped_column(LargeBinary(16), nullable=False)
    last4_key: Mapped[str] = mapped_column(String(4), nullable=False)
    label: Mapped[str | None] = mapped_column(String(80))
    read_only_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_synced: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="broker_keys")
