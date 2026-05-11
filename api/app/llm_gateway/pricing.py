"""Per-model token pricing for cost computation.

Source of truth for what we'll bill the user. We keep this in code (not
the DB) because pricing changes happen rarely and need a code review.

Prices are **USD per 1M tokens** of each type. If a model isn't listed,
we fall back to `_DEFAULT_PRICE` (conservative — slightly above retail
to avoid undercharging on a typo).

Update as providers publish new prices. Cross-check against:
- https://www.anthropic.com/pricing
- https://openai.com/api/pricing/
- https://ai.google.dev/pricing
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    """Per-1M-token pricing in USD."""

    input_per_million: float
    output_per_million: float

    def cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (
            prompt_tokens * self.input_per_million / 1_000_000
            + completion_tokens * self.output_per_million / 1_000_000
        )


# Anthropic (as of 2026-01)
_ANTHROPIC: dict[str, ModelPrice] = {
    "claude-opus-4-7": ModelPrice(15.00, 75.00),
    "claude-opus-4-6": ModelPrice(15.00, 75.00),
    "claude-sonnet-4-6": ModelPrice(3.00, 15.00),
    "claude-haiku-4-5": ModelPrice(0.80, 4.00),
}

# OpenAI (as of 2026-01)
_OPENAI: dict[str, ModelPrice] = {
    "gpt-4o": ModelPrice(2.50, 10.00),
    "gpt-4o-mini": ModelPrice(0.15, 0.60),
    "o1": ModelPrice(15.00, 60.00),
    "o1-mini": ModelPrice(3.00, 12.00),
    "gpt-4-turbo": ModelPrice(10.00, 30.00),
}

# Google Gemini (as of 2026-01)
_GOOGLE: dict[str, ModelPrice] = {
    "gemini-2.0-flash": ModelPrice(0.10, 0.40),
    "gemini-1.5-pro": ModelPrice(1.25, 5.00),
    "gemini-1.5-flash": ModelPrice(0.075, 0.30),
}

# Ollama — user runs the model on their own hardware, so we charge nothing
# for tokens. Wally still bills the base subscription + per-agent-call fee.
_OLLAMA_DEFAULT = ModelPrice(0.0, 0.0)

# Fallback when a model isn't in our table. Conservative on the high side
# so we don't undercharge users on a missing entry.
_DEFAULT_PRICE = ModelPrice(5.0, 20.0)

_TABLE: dict[str, dict[str, ModelPrice]] = {
    "anthropic": _ANTHROPIC,
    "openai": _OPENAI,
    "google": _GOOGLE,
}


def lookup_price(provider: str, model: str) -> ModelPrice:
    """Return the price tuple for a given (provider, model)."""
    if provider == "ollama":
        return _OLLAMA_DEFAULT
    table = _TABLE.get(provider)
    if table is None:
        return _DEFAULT_PRICE
    # Match exact first, then prefix (so claude-sonnet-4-6-20251211 still hits the row)
    if model in table:
        return table[model]
    for known, price in table.items():
        if model.startswith(known):
            return price
    return _DEFAULT_PRICE


def compute_cost(
    provider: str, model: str, prompt_tokens: int, completion_tokens: int
) -> float:
    return lookup_price(provider, model).cost(prompt_tokens, completion_tokens)
