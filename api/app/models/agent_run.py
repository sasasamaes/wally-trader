"""Agent execution records — one row per `/agents/<name>/run` call."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.api_key import LLMProvider

if TYPE_CHECKING:
    pass


class AgentRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class AgentRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "agent_runs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), index=True
    )

    agent_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    input: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    output_md: Mapped[str | None] = mapped_column(Text)

    llm_provider: Mapped[LLMProvider | None] = mapped_column(
        Enum(LLMProvider, name="llm_provider", create_type=False)
    )
    model: Mapped[str | None] = mapped_column(String(96))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(12, 6))
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    status: Mapped[AgentRunStatus] = mapped_column(
        Enum(AgentRunStatus, name="agent_run_status"),
        default=AgentRunStatus.pending,
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text)

    messages: Mapped[list[AgentMessage]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="AgentMessage.created_at"
    )


class AgentMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "agent_messages"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    run: Mapped[AgentRun] = relationship(back_populates="messages")
