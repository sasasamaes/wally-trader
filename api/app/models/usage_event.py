"""Usage events — fuel for Stripe meter billing.

One row per metered agent call. We snapshot the cost and meter event ID
returned by Stripe so reconciliation can be done after the fact and we
have a verifiable audit trail of what we billed.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class UsageEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "usage_events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL")
    )

    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    unit_cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    total_cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)

    stripe_meter_event_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    billed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
