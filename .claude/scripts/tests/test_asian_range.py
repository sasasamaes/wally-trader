"""Tests for asian_range.py — Asian session range + grab/fakeout detector."""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from asian_range import (
    asian_session_high_low,
    detect_break_and_grab,
    evaluate_setup,
)


def _bar(ts_iso, o, h, l, c, v=1000):
    return {
        "ts": ts_iso,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
    }


def test_asian_high_low_computed_from_session_bars():
    """Bars between 23:00-08:00 UTC contribute; outside ignored."""
    bars = [
        _bar("2026-05-12T22:00:00+00:00", 1.10, 1.101, 1.099, 1.100),  # pre-Asian
        _bar("2026-05-12T23:00:00+00:00", 1.100, 1.102, 1.099, 1.101),
        _bar("2026-05-13T00:00:00+00:00", 1.101, 1.105, 1.098, 1.104),  # high here
        _bar("2026-05-13T04:00:00+00:00", 1.104, 1.107, 1.090, 1.092),  # low here (1.090)
        _bar("2026-05-13T07:00:00+00:00", 1.092, 1.095, 1.091, 1.094),
        _bar("2026-05-13T08:00:00+00:00", 1.094, 1.110, 1.094, 1.109),  # post-Asian
    ]
    out = asian_session_high_low(bars, anchor="2026-05-13T08:00:00+00:00")
    assert abs(out["high"] - 1.107) < 1e-9
    assert abs(out["low"] - 1.090) < 1e-9


def test_break_above_then_close_back_inside_is_grab():
    """Price breaks above Asian high then closes back inside within 4 bars → grab."""
    asian_high = 1.107
    asian_low = 1.090
    london_bars = [
        _bar("2026-05-13T08:00:00+00:00", 1.094, 1.112, 1.094, 1.110),  # break above
        _bar("2026-05-13T08:05:00+00:00", 1.110, 1.111, 1.103, 1.104),  # back inside
    ]
    grab = detect_break_and_grab(london_bars, asian_high=asian_high, asian_low=asian_low)
    assert grab is not None
    assert grab["side"] == "high"
    assert grab["direction"] == "short"


def test_break_below_then_close_back_inside_is_grab():
    asian_high = 1.107
    asian_low = 1.090
    london_bars = [
        _bar("2026-05-13T08:00:00+00:00", 1.094, 1.094, 1.085, 1.087),  # break below
        _bar("2026-05-13T08:05:00+00:00", 1.087, 1.099, 1.087, 1.095),  # back inside
    ]
    grab = detect_break_and_grab(london_bars, asian_high=asian_high, asian_low=asian_low)
    assert grab is not None
    assert grab["side"] == "low"
    assert grab["direction"] == "long"


def test_one_sided_trend_no_range_returns_no_signal():
    """Asian session that just trends one direction — no clear range, no grab logic."""
    bars = [_bar(f"2026-05-13T0{i}:00:00+00:00", 1.1 + i * 0.001, 1.1 + i * 0.001 + 0.002,
                  1.1 + i * 0.001 - 0.0005, 1.1 + i * 0.001 + 0.0015) for i in range(9)]
    out = evaluate_setup(bars, anchor="2026-05-13T08:30:00+00:00")
    # range exists but very narrow; grab requires a true break-then-reverse which won't happen
    assert out["signal"] is None or out["signal"].get("confidence", 0) < 30


def test_break_without_grab_no_signal():
    """Price breaks high and continues — no close back inside → no grab."""
    asian_high = 1.107
    asian_low = 1.090
    london_bars = [
        _bar("2026-05-13T08:00:00+00:00", 1.094, 1.115, 1.094, 1.113),
        _bar("2026-05-13T08:05:00+00:00", 1.113, 1.120, 1.110, 1.118),
        _bar("2026-05-13T08:10:00+00:00", 1.118, 1.125, 1.115, 1.122),
    ]
    grab = detect_break_and_grab(london_bars, asian_high=asian_high, asian_low=asian_low)
    assert grab is None


def test_grab_too_late_after_4_bars_no_signal():
    """Close back inside happens on bar 5 → no signal (window is 4 bars)."""
    asian_high = 1.107
    asian_low = 1.090
    london_bars = [
        _bar("2026-05-13T08:00:00+00:00", 1.094, 1.112, 1.094, 1.111),  # break
        _bar("2026-05-13T08:05:00+00:00", 1.111, 1.115, 1.110, 1.113),
        _bar("2026-05-13T08:10:00+00:00", 1.113, 1.114, 1.110, 1.112),
        _bar("2026-05-13T08:15:00+00:00", 1.112, 1.113, 1.110, 1.111),
        _bar("2026-05-13T08:20:00+00:00", 1.111, 1.112, 1.103, 1.104),  # too late
    ]
    grab = detect_break_and_grab(london_bars, asian_high=asian_high, asian_low=asian_low)
    assert grab is None
