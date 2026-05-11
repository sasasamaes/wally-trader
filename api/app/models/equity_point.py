"""Daily equity points — one row per profile per day."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.profile import Profile


class EquityPoint(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "equity_points"
    __table_args__ = (
        UniqueConstraint("profile_id", "date", name="uq_profile_date"),
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    equity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    daily_pnl_pct: Mapped[float | None] = mapped_column(Float)
    dd_pct: Mapped[float | None] = mapped_column(Float)
    outperformance_vs_hodl_pct: Mapped[float | None] = mapped_column(Float)
    win_rate_pct: Mapped[float | None] = mapped_column(Float)
    trade_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="equity_points")
