"""Tests for backtest_asian_range_fotmarkets.py — TDD first.

Run: .claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_backtest_asian_range_fotmarkets.py -v
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import the module under test (will fail until implemented)
import backtest_asian_range_fotmarkets as bt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bar(utc_dt: datetime, o: float, h: float, l: float, c: float, v: float = 1000.0) -> dict:
    """Create a bar dict in the asian_range format (ts = ISO with tz)."""
    return {
        "ts": utc_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
    }


def _dt(y, mo, d, h, mi=0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Test 1 — yfinance DataFrame → asian_range bar format conversion
# ---------------------------------------------------------------------------

def test_yf_to_asian_range_format_conversion():
    """Mock yfinance DataFrame rows → bar dicts with ISO ts + tz + float fields."""
    import pandas as pd

    # Simulate what yfinance returns: DatetimeIndex + OHLCV columns
    idx = pd.DatetimeIndex(
        ["2026-05-12 08:00:00+00:00", "2026-05-12 08:05:00+00:00"],
        tz="UTC",
    )
    df = pd.DataFrame(
        {
            "Open": [1.1234, 1.1240],
            "High": [1.1250, 1.1260],
            "Low": [1.1220, 1.1230],
            "Close": [1.1245, 1.1255],
            "Volume": [1000.0, 1200.0],
        },
        index=idx,
    )

    bars = bt.yf_df_to_bars(df)

    assert len(bars) == 2

    b = bars[0]
    assert "ts" in b, "bar must have 'ts' key"
    assert "open" in b and "high" in b and "low" in b and "close" in b and "volume" in b

    # ts must be ISO string with timezone info
    dt = datetime.fromisoformat(b["ts"])
    assert dt.tzinfo is not None, "ts must be timezone-aware"

    # Fields must be float
    assert isinstance(b["open"], float)
    assert isinstance(b["high"], float)
    assert isinstance(b["low"], float)
    assert isinstance(b["close"], float)
    assert isinstance(b["volume"], float)

    # Values must round-trip correctly
    assert abs(b["open"] - 1.1234) < 1e-9
    assert abs(b["high"] - 1.1250) < 1e-9
    assert abs(b["close"] - 1.1245) < 1e-9


# ---------------------------------------------------------------------------
# Test 2 — simulate_fill: SL hit before TP
# ---------------------------------------------------------------------------

def test_simulate_fill_sl_first():
    """LONG trade where SL is hit before TP → returns loss."""
    entry_price = 1.1000
    sl_price = 1.0980     # 20 pips below entry
    tp_price = 1.1050     # 50 pips above entry

    # First bar: SL tagged, TP not reached
    bars = [
        _make_bar(_dt(2026, 5, 12, 13, 5), entry_price, 1.1010, 1.0975, 1.0985),  # low < sl
        _make_bar(_dt(2026, 5, 12, 13, 10), 1.0985, 1.1060, 1.0985, 1.1055),       # TP would be here
    ]

    result = bt.simulate_fill(
        bars=bars,
        direction="long",
        entry_price=entry_price,
        sl_price=sl_price,
        tp_price=tp_price,
        eod_utc_hour=16,
        eod_utc_minute=55,
        risk_usd=0.30,
        slippage_pips=0.5,
    )

    assert result["outcome"] == "SL", f"Expected SL, got {result['outcome']}"
    assert result["pnl_usd"] < 0, "SL hit must be a loss"


# ---------------------------------------------------------------------------
# Test 3 — simulate_fill: TP hit before SL
# ---------------------------------------------------------------------------

def test_simulate_fill_tp_first():
    """LONG trade where TP is hit before SL → returns win."""
    entry_price = 1.1000
    sl_price = 1.0980     # 20 pips below entry
    tp_price = 1.1040     # 40 pips above entry (R:R = 2)

    # First bar: TP tagged, SL not reached
    bars = [
        _make_bar(_dt(2026, 5, 12, 13, 5), entry_price, 1.1045, 1.0995, 1.1042),  # high > tp
        _make_bar(_dt(2026, 5, 12, 13, 10), 1.1042, 1.1050, 1.0975, 1.0980),       # SL would be here
    ]

    result = bt.simulate_fill(
        bars=bars,
        direction="long",
        entry_price=entry_price,
        sl_price=sl_price,
        tp_price=tp_price,
        eod_utc_hour=16,
        eod_utc_minute=55,
        risk_usd=0.30,
        slippage_pips=0.5,
    )

    assert result["outcome"] == "TP", f"Expected TP, got {result['outcome']}"
    assert result["pnl_usd"] > 0, "TP hit must be a profit"


# ---------------------------------------------------------------------------
# Test 4 — simulate_fill: EOD force close (no SL or TP hit)
# ---------------------------------------------------------------------------

def test_simulate_fill_eod_close():
    """Neither SL nor TP hit by EOD → force close at bar.close of last bar."""
    entry_price = 1.1000
    sl_price = 1.0950     # 50 pips below entry — won't be touched
    tp_price = 1.1100     # 100 pips above — won't be touched

    # Bars all within window but neither SL nor TP
    bars = [
        _make_bar(_dt(2026, 5, 12, 13, 5), 1.1000, 1.1020, 1.0990, 1.1015),
        _make_bar(_dt(2026, 5, 12, 13, 10), 1.1015, 1.1030, 1.0985, 1.1025),
        _make_bar(_dt(2026, 5, 12, 16, 50), 1.1025, 1.1040, 1.1010, 1.1035),  # last bar ≥ EOD
    ]

    result = bt.simulate_fill(
        bars=bars,
        direction="long",
        entry_price=entry_price,
        sl_price=sl_price,
        tp_price=tp_price,
        eod_utc_hour=16,
        eod_utc_minute=55,
        risk_usd=0.30,
        slippage_pips=0.5,
    )

    assert result["outcome"] == "FORCE_CLOSE_EOD", f"Expected FORCE_CLOSE_EOD, got {result['outcome']}"
    # Exit price should be close of last bar (1.1035), possibly adjusted by slippage
    assert result["exit_price"] is not None


# ---------------------------------------------------------------------------
# Test 5 — max_dd_tracker: equity curve [100, 110, 95, 105]
# ---------------------------------------------------------------------------

def test_max_dd_tracker():
    """Equity curve 100→110→95→105 should yield max_dd ≈ 13.636%."""
    equity_curve = [100.0, 110.0, 95.0, 105.0]

    max_dd = bt.compute_max_dd(equity_curve)

    # Peak = 110 at index 1, trough = 95 at index 2 → DD = (110-95)/110 = 13.636...%
    expected = (110.0 - 95.0) / 110.0 * 100.0  # ≈ 13.636%
    assert abs(max_dd - expected) < 0.01, f"Expected ≈{expected:.3f}%, got {max_dd:.3f}%"


# ---------------------------------------------------------------------------
# Test 6 — skip trade outside fotmarkets window
# ---------------------------------------------------------------------------

def test_skip_trade_outside_window():
    """Signal generated at UTC 17:00 (after fotmarkets window 13:00–16:55) → SKIP."""
    signal = {
        "direction": "long",
        "entry": 1.1000,
        "sl": 1.0980,
        "tp": 1.1040,
        "rr": 2.0,
        "entry_bar_ts": "2026-05-12T17:00:00+00:00",  # UTC 17:00 — outside window
    }

    should_trade = bt.signal_in_fotmarkets_window(signal)

    assert should_trade is False, "UTC 17:00 is outside fotmarkets window (13:00–16:55)"


def test_signal_inside_window():
    """Signal at UTC 13:30 should be INSIDE fotmarkets window."""
    signal = {
        "direction": "long",
        "entry": 1.1000,
        "sl": 1.0980,
        "tp": 1.1040,
        "rr": 2.0,
        "entry_bar_ts": "2026-05-12T13:30:00+00:00",  # UTC 13:30 — inside window
    }

    should_trade = bt.signal_in_fotmarkets_window(signal)

    assert should_trade is True, "UTC 13:30 should be inside fotmarkets window"


def test_signal_at_window_boundary_1300():
    """UTC 13:00 exactly is the OPEN of the fotmarkets window → valid."""
    signal = {
        "direction": "short",
        "entry": 1.1050,
        "sl": 1.1070,
        "tp": 1.1010,
        "rr": 2.0,
        "entry_bar_ts": "2026-05-12T13:00:00+00:00",
    }
    assert bt.signal_in_fotmarkets_window(signal) is True


def test_signal_at_window_boundary_1655():
    """UTC 16:55 exactly is the CLOSE of the fotmarkets window → NOT valid (force close moment)."""
    signal = {
        "direction": "short",
        "entry": 1.1050,
        "sl": 1.1070,
        "tp": 1.1010,
        "rr": 2.0,
        "entry_bar_ts": "2026-05-12T16:55:00+00:00",
    }
    assert bt.signal_in_fotmarkets_window(signal) is False
