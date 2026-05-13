"""Tests for hmm_lib.backtest — per-regime backtest harness."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))

from hmm_lib import backtest


def _fake_bars_15m(n: int, start_ts: int = 1_700_000_000) -> list[dict]:
    """list of dicts matching backtest_regime_matrix.py bar format."""
    return [{
        "t": start_ts + i * 900,
        "o": 100.0,
        "h": 101.0,
        "l": 99.0,
        "c": 100.0 + (i % 10) * 0.1,
        "v": 1000.0,
    } for i in range(n)]


def _fake_bars_1h(bars_15m: list[dict]) -> list[dict]:
    """Aggregate 15m to 1h."""
    out = []
    for i in range(0, len(bars_15m), 4):
        chunk = bars_15m[i:i + 4]
        out.append({
            "t": chunk[0]["t"],
            "o": chunk[0]["o"],
            "h": max(b["h"] for b in chunk),
            "l": min(b["l"] for b in chunk),
            "c": chunk[-1]["c"],
            "v": sum(b["v"] for b in chunk),
        })
    return out


def _trivial_strategy(bars_15m, bars_1h, i):
    """A toy strategy that always signals LONG at i, exit at i+1."""
    if i < 10 or i >= len(bars_15m) - 2:
        return None
    if i % 50 == 0:  # one signal per 50 bars
        entry = bars_15m[i]["c"]
        return {"side": "LONG", "entry": entry, "sl": entry * 0.99,
                "tp1": entry * 1.01, "tp2": entry * 1.02}
    return None


def test_partition_by_entry_regime():
    bars_15m = _fake_bars_15m(400)
    bars_1h = _fake_bars_1h(bars_15m)
    # 100 hourly bars → assign first 50 to regime CHOP (state 0), next 50 to STRESS (state 1)
    states_1h = np.array([0] * 50 + [1] * 50)
    labels = {0: {"label": "CHOP"}, 1: {"label": "STRESS"}}
    results = backtest.backtest_per_regime(
        bars_15m, bars_1h, states_1h, labels,
        strategy_fn=_trivial_strategy, strategy_name="TEST_STRAT",
    )
    labels_seen = {r.regime_label for r in results}
    assert "GLOBAL" in labels_seen
    assert "CHOP" in labels_seen or "STRESS" in labels_seen


def test_global_baseline_matches_unfiltered():
    bars_15m = _fake_bars_15m(400)
    bars_1h = _fake_bars_1h(bars_15m)
    states_1h = np.array([0] * 100)
    labels = {0: {"label": "CHOP"}}
    results = backtest.backtest_per_regime(
        bars_15m, bars_1h, states_1h, labels,
        strategy_fn=_trivial_strategy, strategy_name="TEST_STRAT",
    )
    global_row = next(r for r in results if r.regime_label == "GLOBAL")
    chop_row = next((r for r in results if r.regime_label == "CHOP"), None)
    # With only one regime, GLOBAL trades == CHOP trades
    assert chop_row is not None
    assert global_row.trades == chop_row.trades


def test_zero_trades_in_regime_emits_row():
    bars_15m = _fake_bars_15m(400)
    bars_1h = _fake_bars_1h(bars_15m)
    states_1h = np.array([0] * 100)
    labels = {0: {"label": "STRESS"}, 1: {"label": "CHOP"}}  # state 1 never appears
    # Strategy that never signals
    results = backtest.backtest_per_regime(
        bars_15m, bars_1h, states_1h, labels,
        strategy_fn=lambda *_: None, strategy_name="NO_SIGNAL",
    )
    global_row = next(r for r in results if r.regime_label == "GLOBAL")
    assert global_row.trades == 0


def test_strategy_exception_propagates_with_bar_index():
    from hmm_lib.errors import StrategyExecError

    def crashing_strategy(bars_15m, bars_1h, i):
        if i == 50:
            raise ValueError("simulated crash")
        return None

    bars_15m = _fake_bars_15m(200)
    bars_1h = _fake_bars_1h(bars_15m)
    states_1h = np.array([0] * 50)
    labels = {0: {"label": "CHOP"}}
    with pytest.raises(StrategyExecError) as exc_info:
        backtest.backtest_per_regime(
            bars_15m, bars_1h, states_1h, labels,
            strategy_fn=crashing_strategy, strategy_name="BOOM",
        )
    assert exc_info.value.bar_index == 50
