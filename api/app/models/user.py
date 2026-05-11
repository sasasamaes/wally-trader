"""User account — keyed by Clerk identity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.api_key import ApiKeyBroker, ApiKeyLLM
    from app.models.profile import Profile
    from app.models.subscription import Subscription


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    clerk_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(160))
    plan_tier: Mapped[str] = mapped_column(
        String(32), default="beta", nullable=False
    )

    profiles: Mapped[list[Profile]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    llm_keys: Mapped[list[ApiKeyLLM]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    broker_keys: Mapped[list[ApiKeyBroker]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    subscription: Mapped[Subscription | None] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<User {self.email}>"
