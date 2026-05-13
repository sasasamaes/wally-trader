#!/usr/bin/env python3
"""Tests for backtest_pullback_vs_macross.py

TDD — written BEFORE implementation.
5 test cases per spec:
1. simulate_trade_outcome_sl_first
2. simulate_trade_outcome_tp_first
3. simulate_trade_outcome_flat
4. filter_trend_leve_excludes_outside_band
5. aggregate_metrics_basic
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure scripts dir is on path
SCRIPTS = Path(__file__).resolve().parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import backtest_pullback_vs_macross as bpm  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers to build synthetic bar sequences
# ---------------------------------------------------------------------------

def _bar(o: float, h: float, l: float, c: float, v: float = 1000.0) -> dict:
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


def _flat_bars(price: float, n: int) -> list[dict]:
    """All bars at the same price level (tiny range)."""
    return [_bar(price, price + 1, price - 1, price) for _ in range(n)]


# ---------------------------------------------------------------------------
# Test 1 — SL hits before TP1
# ---------------------------------------------------------------------------

def test_simulate_trade_outcome_sl_first():
    """LONG trade where price drops below SL within 96-bar window."""
    entry = 100.0
    sl = 95.0     # -5 below entry
    tp1 = 110.0   # +10 above entry (further away → SL hits first)

    # First 5 bars: price drifts down through SL (low of 94)
    future_bars = [_bar(99, 100, 94, 95)] + _flat_bars(95, 95)

    outcome = bpm.simulate_trade_outcome(
        future_bars=future_bars,
        direction="long",
        entry=entry,
        sl=sl,
        tp1=tp1,
    )

    assert outcome["result"] == "loss", f"Expected loss, got {outcome}"
    assert outcome["r"] < 0, f"Expected negative R, got {outcome['r']}"


# ---------------------------------------------------------------------------
# Test 2 — TP1 hits before SL
# ---------------------------------------------------------------------------

def test_simulate_trade_outcome_tp_first():
    """LONG trade where price rises to TP1 before hitting SL."""
    entry = 100.0
    sl = 95.0    # -5 below entry
    tp1 = 110.0  # +10 above entry

    # First bar: high reaches 111 (above tp1), low stays well above SL
    future_bars = [_bar(100, 111, 99, 110)] + _flat_bars(110, 95)

    outcome = bpm.simulate_trade_outcome(
        future_bars=future_bars,
        direction="long",
        entry=entry,
        sl=sl,
        tp1=tp1,
    )

    assert outcome["result"] == "win", f"Expected win, got {outcome}"
    assert outcome["r"] > 0, f"Expected positive R, got {outcome['r']}"


# ---------------------------------------------------------------------------
# Test 3 — Neither hits (flat within 96 bars)
# ---------------------------------------------------------------------------

def test_simulate_trade_outcome_flat():
    """Trade where neither SL nor TP1 is hit within 96 bars → flat."""
    entry = 100.0
    sl = 90.0    # -10 below entry (far)
    tp1 = 110.0  # +10 above entry (far)

    # 96 bars that stay between 92 and 108 (neither SL nor TP1 triggered)
    future_bars = [_bar(100, 108, 92, 100) for _ in range(96)]

    outcome = bpm.simulate_trade_outcome(
        future_bars=future_bars,
        direction="long",
        entry=entry,
        sl=sl,
        tp1=tp1,
    )

    assert outcome["result"] == "flat", f"Expected flat, got {outcome}"
    assert outcome["r"] == 0, f"Expected 0 R, got {outcome['r']}"


# ---------------------------------------------------------------------------
# Test 4 — ADX filter excludes values outside [25, 30]
# ---------------------------------------------------------------------------

def test_filter_trend_leve_excludes_outside_band():
    """ADX=20 (chop) and ADX=35 (strong trend) should both be excluded."""
    # RANGE_CHOP — ADX below 25
    assert bpm.is_trend_leve(20.0) is False, "ADX=20 should NOT be TREND_LEVE"
    assert bpm.is_trend_leve(24.9) is False, "ADX=24.9 should NOT be TREND_LEVE"

    # TREND_FUERTE — ADX above 30
    assert bpm.is_trend_leve(30.1) is False, "ADX=30.1 should NOT be TREND_LEVE"
    assert bpm.is_trend_leve(35.0) is False, "ADX=35 should NOT be TREND_LEVE"

    # TREND_LEVE boundary values — should be included
    assert bpm.is_trend_leve(25.0) is True, "ADX=25.0 should be TREND_LEVE"
    assert bpm.is_trend_leve(27.5) is True, "ADX=27.5 should be TREND_LEVE"
    assert bpm.is_trend_leve(30.0) is True, "ADX=30.0 should be TREND_LEVE"


# ---------------------------------------------------------------------------
# Test 5 — Aggregate metrics (WR, PF, total R)
# ---------------------------------------------------------------------------

def test_aggregate_metrics_basic():
    """Given explicit R values, verify WR / PF / total_R are correct."""
    # 3 wins (+2R each), 2 losses (-1R each)
    r_values = [2.0, 2.0, 2.0, -1.0, -1.0]

    metrics = bpm.aggregate_metrics(r_values)

    assert metrics["n"] == 5
    assert metrics["wins"] == 3
    assert metrics["losses"] == 2
    assert abs(metrics["wr_pct"] - 60.0) < 0.01, f"Expected WR=60, got {metrics['wr_pct']}"
    # PF = sum_wins / |sum_losses| = 6 / 2 = 3.0
    assert abs(metrics["pf"] - 3.0) < 0.01, f"Expected PF=3.0, got {metrics['pf']}"
    assert abs(metrics["total_r"] - 4.0) < 0.01, f"Expected total_R=4.0, got {metrics['total_r']}"

    # Edge: all losses
    r_all_loss = [-1.0, -1.0]
    m2 = bpm.aggregate_metrics(r_all_loss)
    assert m2["wr_pct"] == 0.0
    assert m2["pf"] == 0.0
    assert m2["total_r"] == -2.0

    # Edge: empty list
    m3 = bpm.aggregate_metrics([])
    assert m3["n"] == 0
    assert m3["wr_pct"] == 0.0
