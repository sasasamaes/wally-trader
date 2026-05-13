"""Pytest tests for autohunt_tp.compute_tp_plan + helpers.

These mirror the inline --sanity self-test cases but with proper pytest
parametrize + clearer assertions. Keep both: --sanity for quick CLI smoke,
pytest for CI / coverage.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import autohunt_tp as atp  # noqa: E402


def test_baseline_move_zero_atr():
    assert atp.baseline_move_pct(0.0) == 0.0
    assert atp.baseline_move_pct(-1.0) == 0.0


def test_baseline_move_scales_with_sqrt_n():
    pct = atp.baseline_move_pct(1.0, n_bars=9)
    assert abs(pct - 3.0) < 1e-9  # sqrt(9) = 3


def test_confluence_multiplier_clamps():
    assert atp.confluence_multiplier(0) == pytest.approx(0.7)
    assert atp.confluence_multiplier(60) == pytest.approx(0.7)
    assert atp.confluence_multiplier(100) == pytest.approx(1.3)
    assert atp.confluence_multiplier(150) == pytest.approx(1.3)


def test_session_multiplier_ok_vs_warn():
    assert atp.session_multiplier("OK") == 1.0
    assert atp.session_multiplier("WARN") == 0.7
    assert atp.session_multiplier(None) == 0.7
    assert atp.session_multiplier("ok") == 1.0  # case-insensitive


def test_structural_cap_uses_smallest():
    cap = atp.structural_cap_pct(magnet_dist_pct=3.0, fib_1618_dist_pct=2.0)
    assert abs(cap - 2.0 * 1.05) < 1e-9


def test_structural_cap_hard_ceiling():
    cap = atp.structural_cap_pct(magnet_dist_pct=10.0, fib_1618_dist_pct=8.0)
    assert abs(cap - 5.0 * 1.05) < 1e-9


def test_atr_extreme_gate():
    assert atp.atr_extreme_gate(None) is False
    assert atp.atr_extreme_gate(50.0) is False
    assert atp.atr_extreme_gate(95.0) is True
    assert atp.atr_extreme_gate(99.5) is True


@pytest.mark.parametrize(
    "label, kwargs, expect_em_range, expect_floor",
    [
        ("SOL_SHORT_STRONG",
         dict(side="SHORT", entry=145.20, atr_pct_15m=0.45,
              regime="STRONG_TREND_DOWN", confluence_score=82,
              session_quality="OK", magnet_dist_pct=5.0,
              fib_1618_dist_pct=3.2, margin_usd=50.0, leverage=15),
         (1.5, 2.0), True),
        ("BTC_LONG_RANGE_WARN",
         dict(side="LONG", entry=68000, atr_pct_15m=0.18,
              regime="RANGING", confluence_score=65,
              session_quality="WARN", magnet_dist_pct=2.0,
              fib_1618_dist_pct=1.5, margin_usd=50.0, leverage=15),
         (0.15, 0.30), False),
        ("ETH_LONG_STRONG_AGRADE",
         dict(side="LONG", entry=3500, atr_pct_15m=1.3,
              regime="STRONG_TREND_UP", confluence_score=88,
              session_quality="OK", magnet_dist_pct=6.0,
              fib_1618_dist_pct=4.5, margin_usd=50.0, leverage=20),
         (3.5, 5.5), True),
    ],
)
def test_compute_tp_plan_known_cases(label, kwargs, expect_em_range, expect_floor):
    plan = atp.compute_tp_plan(**kwargs)
    em_lo, em_hi = expect_em_range
    assert em_lo <= plan["expected_move_pct"] <= em_hi, (
        f"{label}: expected_move {plan['expected_move_pct']} not in {expect_em_range}"
    )
    assert plan["floor_passed"] == expect_floor, (
        f"{label}: floor_passed {plan['floor_passed']} != {expect_floor}"
    )


def test_a_grade_margin_bump_within_cap():
    """A-GRADE setup with tp3_usd < $10 should bump margin if cap allows."""
    plan = atp.compute_tp_plan(
        side="LONG", entry=100, atr_pct_15m=0.1,  # tiny ATR → tiny move
        regime="STRONG_TREND_UP", confluence_score=85,
        session_quality="OK", magnet_dist_pct=1.0,
        fib_1618_dist_pct=1.0, margin_usd=50.0, leverage=15,
    )
    if plan["margin_bumped"]:
        assert plan["margin_used_usd"] > 50.0
        assert plan["margin_used_usd"] <= 75.0


def test_dollar_pnl_arithmetic():
    # 2% move on $50 × 15x = $750 notional → $15
    assert atp.dollar_pnl(2.0, 50.0, 15) == pytest.approx(15.0)
    # 1% move on $100 × 20x = $2000 notional → $20
    assert atp.dollar_pnl(1.0, 100.0, 20) == pytest.approx(20.0)


def test_floor_drop_below():
    """RANGING with WARN session and tiny ATR should DROP_BELOW_FLOOR."""
    plan = atp.compute_tp_plan(
        side="LONG", entry=100, atr_pct_15m=0.05,
        regime="RANGING", confluence_score=65,
        session_quality="WARN", margin_usd=50.0, leverage=15,
    )
    assert plan["floor_status"] in ("DROP_BELOW_FLOOR", "TP3_ONLY")
    assert plan["floor_passed"] is False
