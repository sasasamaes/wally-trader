"""Trading profile — multi-tenant version of `.claude/profiles/<name>/`."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.equity_point import EquityPoint
    from app.models.signal import Signal
    from app.models.trade_broker_sync import TradeBrokerSync
    from app.models.user import User


class ProfileKind(str, enum.Enum):
    retail = "retail"
    retail_bingx = "retail-bingx"
    ftmo = "ftmo"
    fundingpips = "fundingpips"
    fotmarkets = "fotmarkets"
    bitunix = "bitunix"
    quantfury = "quantfury"
    custom = "custom"


class Profile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "slug", name="uq_user_profile_slug"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[ProfileKind] = mapped_column(
        Enum(ProfileKind, name="profile_kind"), nullable=False
    )
    capital_initial: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    capital_current: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    strategy_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    rules_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="profiles")
    signals: Mapped[list[Signal]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    equity_points: Mapped[list[EquityPoint]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    broker_syncs: Mapped[list[TradeBrokerSync]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
