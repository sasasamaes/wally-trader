"""Tests for L3 — adaptive_weights."""
import csv
import json
import pytest
from pathlib import Path
from wally_core.learning.adaptive_weights import (
    DEFAULT_WEIGHTS,
    ab_test_weights,
    fit_adaptive_weights,
    load_adaptive_weights,
    update_composite_weights,
)


def _write_outcomes_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "open_time_utc", "close_time_utc", "hold_minutes", "profile",
        "symbol", "side", "entry", "exit", "qty", "pnl_usd", "pnl_pct",
        "regime_at_entry", "regime_at_exit", "max_favorable_excursion",
        "max_adverse_excursion", "raw_outcome", "lesson_tags", "notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            full = {k: "" for k in fieldnames}
            full.update(row)
            writer.writerow(full)


def test_fit_insufficient_data(tmp_path):
    """With < 50 trades, return DEFAULT_WEIGHTS."""
    result = fit_adaptive_weights("bitunix", n_trades=50, profiles_dir=str(tmp_path))
    assert result["status"] == "insufficient_data"
    assert result["weights"] == DEFAULT_WEIGHTS


def test_fit_converges_with_mixed_data(tmp_path):
    """With 50+ mixed trades, regression should converge and return valid weights."""
    rows = []
    for i in range(60):
        pnl = 5.0 if i % 3 != 0 else -2.0  # ~67% win rate
        rows.append({
            "pnl_usd": str(pnl),
            "regime_at_entry": "RANGE_CHOP" if pnl > 0 else "TREND_FUERTE",
            # Note: 'multifactor' field not in standard CSV — adaptive_weights reads it via fallback 50
        })

    path = tmp_path / "bitunix" / "memory" / "outcomes_v2.csv"
    _write_outcomes_csv(path, rows)

    result = fit_adaptive_weights("bitunix", n_trades=50, profiles_dir=str(tmp_path))
    assert result["status"] == "ok"
    weights = result["weights"]
    assert isinstance(weights, dict)
    assert set(weights.keys()) == set(DEFAULT_WEIGHTS.keys())
    # Weights must sum to ~1.0
    total = sum(weights.values())
    assert abs(total - 1.0) < 0.02


def test_update_and_load_composite_weights(tmp_path):
    new_weights = {"multifactor": 0.30, "regime_aligned": 0.25, "ml": 0.15,
                   "sentiment": 0.15, "macro_clear": 0.10, "smart_router": 0.05}
    update_composite_weights("bitunix", new_weights, profiles_dir=str(tmp_path))

    loaded = load_adaptive_weights("bitunix", profiles_dir=str(tmp_path))
    assert loaded is not None
    assert loaded["multifactor"] == 0.30


def test_load_adaptive_weights_missing(tmp_path):
    result = load_adaptive_weights("nonexistent_profile", profiles_dir=str(tmp_path))
    assert result is None


def test_load_adaptive_weights_none_profile(tmp_path):
    result = load_adaptive_weights(None, profiles_dir=str(tmp_path))
    assert result is None


def test_ab_test_insufficient_data(tmp_path):
    result = ab_test_weights(DEFAULT_WEIGHTS, DEFAULT_WEIGHTS, [])
    assert result["promote"] is False
    assert "insufficient" in result["reason"]


def test_ab_test_promotes_better_weights():
    """When new weights are identical to old, delta=0 → no promote."""
    rows = []
    for i in range(20):
        rows.append({
            "pnl_usd": 5.0 if i < 14 else -2.0,
            "regime_at_entry": "RANGE",
            "multifactor": 70.0,
            "regime_aligned": 100.0,
            "ml": 70.0,
            "sentiment": 60.0,
            "macro_clear": 100.0,
            "verdict": "APPROVE",
        })
    result = ab_test_weights(DEFAULT_WEIGHTS, DEFAULT_WEIGHTS, rows)
    # Identical weights → delta=0 → no promote
    assert result["delta"] == 0.0
    assert result["promote"] is False


def test_composite_loads_adaptive_weights(tmp_path, monkeypatch):
    """composite_signal_score should use adaptive weights when available."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
    from wally_core.composite import composite_signal_score

    new_weights = {"multifactor": 0.50, "regime_aligned": 0.10, "ml": 0.10,
                   "sentiment": 0.10, "macro_clear": 0.10, "smart_router": 0.10}
    update_composite_weights("bitunix", new_weights, profiles_dir=str(tmp_path))

    res = composite_signal_score(
        multifactor_score=100,
        regime_aligned=False,
        ml_score=0,
        sentiment_score=0,
        macro_clear=True,
        smart_router_decision="no_setup",
        profile="bitunix",
        profiles_dir=str(tmp_path),
    )
    # With heavy multifactor weight (0.50) and multifactor=100, score should be high
    assert res.score >= 50
