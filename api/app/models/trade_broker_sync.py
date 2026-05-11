"""Real broker positions snapshotted from broker APIs (read-only)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.api_key import BrokerName

if TYPE_CHECKING:
    from app.models.profile import Profile


class TradeBrokerStatus(str, enum.Enum):
    open = "OPEN"
    closed = "CLOSED"
    cancelled = "CANCELLED"


class TradeBrokerSync(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "trades_broker_sync"
    __table_args__ = (
        UniqueConstraint(
            "profile_id", "broker", "broker_order_id",
            name="uq_profile_broker_order",
        ),
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    broker: Mapped[BrokerName] = mapped_column(
        Enum(BrokerName, name="broker_name"), nullable=False
    )
    broker_order_id: Mapped[str] = mapped_column(String(80), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    qty: Mapped[float] = mapped_column(Numeric(28, 10), nullable=False)
    entry: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    mark: Mapped[float | None] = mapped_column(Numeric(18, 8))
    pnl_unrealized: Mapped[float | None] = mapped_column(Numeric(18, 4))
    sl: Mapped[float | None] = mapped_column(Numeric(18, 8))
    tp: Mapped[float | None] = mapped_column(Numeric(18, 8))
    leverage: Mapped[int | None] = mapped_column()
    liq_price: Mapped[float | None] = mapped_column(Numeric(18, 8))
    status: Mapped[TradeBrokerStatus] = mapped_column(
        Enum(TradeBrokerStatus, name="trade_broker_status"),
        default=TradeBrokerStatus.open,
        nullable=False,
    )

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    profile: Mapped[Profile] = relationship(back_populates="broker_syncs")
