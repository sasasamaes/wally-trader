"""SQLAlchemy ORM models.

Importing this package triggers registration of every model with the
metadata, which is what Alembic autogenerate depends on.
"""

from app.models.agent_run import AgentMessage, AgentRun
from app.models.api_key import ApiKeyBroker, ApiKeyLLM
from app.models.audit_log import AuditLog
from app.models.equity_point import EquityPoint
from app.models.journal_entry import JournalEntry
from app.models.profile import Profile, ProfileKind
from app.models.signal import Signal, SignalOutcome, SignalSide
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.trade_broker_sync import TradeBrokerSync
from app.models.usage_event import UsageEvent
from app.models.user import User

__all__ = [
    "AgentMessage",
    "AgentRun",
    "ApiKeyBroker",
    "ApiKeyLLM",
    "AuditLog",
    "EquityPoint",
    "JournalEntry",
    "Profile",
    "ProfileKind",
    "Signal",
    "SignalOutcome",
    "SignalSide",
    "Subscription",
    "SubscriptionStatus",
    "TradeBrokerSync",
    "UsageEvent",
    "User",
]
