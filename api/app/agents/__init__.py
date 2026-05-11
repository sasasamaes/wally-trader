"""Backend agents — ports of the `.opencode/agents/` CLI subagents.

Each agent is an async generator that yields `StreamChunk`s to the API
layer (which writes them as SSE events). Agents combine:

- **Pure logic** from `shared/wally_core/` (regime detection, risk math,
  multifactor scoring, journal metrics)
- **LLM reasoning** via the user's BYOK key, called through `LLMGateway`

The base agent below handles common plumbing: opening an AgentRun row,
streaming LLM chunks, and finalizing the run record. Concrete agents
implement `system_prompt()` and `user_prompt()` from their input dict.
"""

from app.agents.base import BaseAgent, get_agent
from app.agents.journal import JournalAgent
from app.agents.multifactor import MultifactorAgent
from app.agents.regime import RegimeAgent
from app.agents.risk import RiskAgent
from app.agents.sentiment import SentimentAgent
from app.agents.signal_validator import SignalValidatorAgent

AGENTS: dict[str, type[BaseAgent]] = {
    "regime": RegimeAgent,
    "risk": RiskAgent,
    "signal_validator": SignalValidatorAgent,
    "multifactor": MultifactorAgent,
    "journal": JournalAgent,
    "sentiment": SentimentAgent,
}

__all__ = ["AGENTS", "BaseAgent", "get_agent"]
