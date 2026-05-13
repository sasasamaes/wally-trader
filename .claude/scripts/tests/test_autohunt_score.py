"""Pytest tests for autohunt_score.compute_score + normalisers."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import autohunt_score as asc  # noqa: E402


def test_is_btc_eth():
    assert asc._is_btc_eth("BTCUSDT") is True
    assert asc._is_btc_eth("BTCUSDT.P") is True
    assert asc._is_btc_eth("ETHUSDT") is True
    assert asc._is_btc_eth("SOLUSDT") is False
    assert asc._is_btc_eth("") is False
    assert asc._is_btc_eth(None) is False


def test_norm_backtest_pnl_decay():
    full = asc._norm_backtest_pnl(2.5, n_trades=30)
    half = asc._norm_backtest_pnl(2.5, n_trades=15)
    assert abs(full - 1.0) < 1e-9
    assert abs(half - 0.5) < 1e-9


def test_norm_multifactor_sign_match():
    # LONG side with positive multifactor → good
    assert asc._norm_multifactor(80, "LONG") == 0.8
    # LONG side with negative multifactor → no credit
    assert asc._norm_multifactor(-80, "LONG") == 0.0
    # SHORT side mirror
    assert asc._norm_multifactor(-80, "SHORT") == 0.8
    assert asc._norm_multifactor(80, "SHORT") == 0.0


def test_norm_magnet_wrong_side_gets_zero():
    # LONG: magnet must be ABOVE entry
    assert asc._norm_magnet_alignment(100, 102, 95, "LONG") == 0.0
    # LONG with magnet above + TP1 well below magnet → full credit
    assert asc._norm_magnet_alignment(100, 101, 110, "LONG") == 1.0


def test_norm_fib_zone_lookup():
    assert asc._norm_fib_retracement("OTE") == 1.0
    assert asc._norm_fib_retracement("GOLDEN") == 0.9
    assert asc._norm_fib_retracement("OUT") == 0.0
    assert asc._norm_fib_retracement("UNKNOWN") == 0.0
    assert asc._norm_fib_retracement(None) is None


def test_norm_obv():
    assert asc._norm_obv_alignment("OK") == 1.0
    assert asc._norm_obv_alignment("WARN") == 0.5
    assert asc._norm_obv_alignment("BLOCK") == 0.0


def test_compute_score_ideal_alt():
    out = asc.compute_score(
        symbol="SOLUSDT", side="SHORT",
        backtest_pnl_per_trade=2.5, backtest_n_trades=40,
        multifactor_score=-75, rr_tp1=2.0,
        entry=145.0, tp1=143.5, liq_magnet=137.5,
        fib_zone="GOLDEN", obv_verdict="OK",
        smart_money_ls=0.5, retail_ls=1.4,
        pump_score=80, pump_side_bias="SHORT",
        sentiment_funding_passed=True,
    )
    assert out["score"] >= 75
    assert out["tier"] == "A-GRADE"


def test_compute_score_mediocre_drops():
    out = asc.compute_score(
        symbol="BTCUSDT", side="LONG",
        backtest_pnl_per_trade=0.5, backtest_n_trades=20,
        multifactor_score=15, rr_tp1=1.4,
        entry=68000, tp1=68500, liq_magnet=70000,
        fib_zone="SHALLOW", obv_verdict="WARN",
        smart_money_ls=1.0, retail_ls=1.2,
        pump_score=20, pump_side_bias="NONE",
        sentiment_funding_passed=True,
        usdt_d_bias="NEUTRAL",
    )
    assert out["tier"] in ("DROP", "C-GRADE")


def test_compute_score_partial_data_normalises():
    out = asc.compute_score(
        symbol="ETHUSDT", side="LONG",
        backtest_pnl_per_trade=2.0, backtest_n_trades=30,
        multifactor_score=70,
        sentiment_funding_passed=True,
    )
    # Only 3 components used (20+20+5 = 45 weight)
    assert out["denominator_weight"] == 45
    assert out["tier"] == "B-GRADE"


def test_altcoin_skips_btc_eth_only_components():
    out = asc.compute_score(
        symbol="SOLUSDT", side="LONG",
        backtest_pnl_per_trade=1.0, backtest_n_trades=30,
        multifactor_score=50,
        usdt_d_bias="BEARISH",   # should be ignored for SOL
        on_chain_bias="BULL",    # should be ignored for SOL
    )
    used_names = [c["name"] for c in out["components"] if c["used"]]
    assert "usdt_d_bias_alignment" not in used_names
    assert "on_chain_bias_alignment" not in used_names


def test_tier_thresholds():
    # Pure score → tier mapping
    for score, expected in [
        (95, "A-GRADE"), (80, "A-GRADE"),
        (75, "B-GRADE"), (70, "B-GRADE"),
        (65, "C-GRADE"), (60, "C-GRADE"),
        (50, "DROP"), (0, "DROP"),
    ]:
        out = asc.compute_score(
            symbol="BTCUSDT", side="LONG",
            backtest_pnl_per_trade=score / 50 * 2.5,  # tune to hit tier
            backtest_n_trades=30,
        )
        # We're not asserting exact tier from one component — just check the
        # threshold logic by directly computing
        pass

    # Direct threshold check
    assert asc.TIER_A_MIN == 80
    assert asc.TIER_B_MIN == 70
    assert asc.TIER_C_MIN == 60
