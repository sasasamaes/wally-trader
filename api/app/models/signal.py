"""Signals — port of `signals_received.csv` to relational storage."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.journal_entry import JournalEntry
    from app.models.profile import Profile


class SignalSide(str, enum.Enum):
    long = "LONG"
    short = "SHORT"


class SignalOutcome(str, enum.Enum):
    pending = "PENDING"
    tp1 = "TP1"
    tp2 = "TP2"
    tp3 = "TP3"
    sl = "SL"
    manual = "MANUAL"
    cancelled = "CANCELLED"


class SignalVerdict(str, enum.Enum):
    approve_full = "APPROVE_FULL"
    approve_half = "APPROVE_HALF"
    reject = "REJECT"
    no_go_by_system = "NO_GO_BY_SYSTEM"
    self_generated = "SELF_GENERATED"
    visual_copy = "VISUAL_COPY"


class Signal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "signals"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )

    # Setup
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    side: Mapped[SignalSide] = mapped_column(
        Enum(SignalSide, name="signal_side"), nullable=False
    )
    entry: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    sl: Mapped[float | None] = mapped_column(Numeric(18, 8))
    tp1: Mapped[float | None] = mapped_column(Numeric(18, 8))
    tp2: Mapped[float | None] = mapped_column(Numeric(18, 8))
    tp3: Mapped[float | None] = mapped_column(Numeric(18, 8))
    leverage: Mapped[int | None] = mapped_column()

    # Validation pipeline snapshot
    filters_4_count: Mapped[int | None] = mapped_column()
    multifactor_score: Mapped[float | None] = mapped_column(Float)
    ml_score: Mapped[float | None] = mapped_column(Float)
    chainlink_delta_pct: Mapped[float | None] = mapped_column(Float)
    regime: Mapped[str | None] = mapped_column(String(48))
    pillars_4_count: Mapped[int | None] = mapped_column()
    saturday: Mapped[bool] = mapped_column(default=False, nullable=False)
    verdict: Mapped[SignalVerdict | None] = mapped_column(
        Enum(SignalVerdict, name="signal_verdict")
    )

    # Decision
    decision: Mapped[str | None] = mapped_column(String(64))
    size_pct: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(64), default="self_generated", nullable=False)

    # Outcome
    outcome: Mapped[SignalOutcome] = mapped_column(
        Enum(SignalOutcome, name="signal_outcome"),
        default=SignalOutcome.pending,
        nullable=False,
    )
    exit_price: Mapped[float | None] = mapped_column(Numeric(18, 8))
    exit_reason: Mapped[str | None] = mapped_column(String(64))
    pnl_usd: Mapped[float | None] = mapped_column(Numeric(18, 4))
    duration_h: Mapped[float | None] = mapped_column(Float)
    hypothetical_outcome: Mapped[str | None] = mapped_column(String(32))
    learning: Mapped[str | None] = mapped_column(Text)
    tier: Mapped[str | None] = mapped_column(String(32))

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Free-form for future fields without migration churn
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="signals")
    journal_entries: Mapped[list[JournalEntry]] = relationship(
        back_populates="signal", cascade="all, delete-orphan"
    )
