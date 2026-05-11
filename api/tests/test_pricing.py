"""Tests for the LLM pricing table."""

from __future__ import annotations

from app.llm_gateway.pricing import compute_cost, lookup_price


def test_anthropic_sonnet_pricing() -> None:
    price = lookup_price("anthropic", "claude-sonnet-4-6")
    assert price.input_per_million == 3.00
    assert price.output_per_million == 15.00


def test_prefix_match_handles_versioned_models() -> None:
    # Provider often returns a versioned model id like `claude-sonnet-4-6-20251211`.
    # Lookup should still resolve to the base model's price.
    price = lookup_price("anthropic", "claude-sonnet-4-6-20251211")
    assert price.input_per_million == 3.00


def test_unknown_provider_falls_back() -> None:
    price = lookup_price("unknown-provider", "some-model")
    # Conservative default
    assert price.input_per_million == 5.0
    assert price.output_per_million == 20.0


def test_unknown_model_within_known_provider() -> None:
    price = lookup_price("openai", "completely-made-up-model-xyz")
    # Falls back to default rather than crashing
    assert price.input_per_million == 5.0


def test_ollama_costs_zero() -> None:
    price = lookup_price("ollama", "llama3.1")
    assert price.input_per_million == 0.0
    assert price.output_per_million == 0.0


def test_compute_cost_basic() -> None:
    # Sonnet: $3/M input, $15/M output
    cost = compute_cost("anthropic", "claude-sonnet-4-6", 1_000_000, 1_000_000)
    assert cost == 18.00


def test_compute_cost_small_call() -> None:
    cost = compute_cost("openai", "gpt-4o-mini", 500, 200)
    # 500 * 0.15/1M + 200 * 0.60/1M = 0.000075 + 0.00012 = 0.000195
    assert abs(cost - 0.000195) < 1e-9


def test_compute_cost_zero_for_ollama() -> None:
    cost = compute_cost("ollama", "llama3.1", 10_000, 10_000)
    assert cost == 0.0
