"""Tests for pullback_detector.py — impulse → pullback → continuation pattern."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pullback_detector import (
    detect_impulse,
    detect_pullback,
    detect_continuation,
    evaluate_setup,
)


def _bar(o, h, l, c, v=1000):
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


def test_impulse_detected_on_5_green_with_above_avg_atr():
    """Five green candles with ATR > rolling mean → impulse identified."""
    chop = [_bar(100, 101, 99, 100) for _ in range(20)]
    impulse = [
        _bar(100, 103, 100, 102),
        _bar(102, 106, 101, 105),
        _bar(105, 110, 104, 109),
        _bar(109, 114, 108, 113),
        _bar(113, 118, 112, 117),
    ]
    bars = chop + impulse
    result = detect_impulse(bars, min_streak=3)
    assert result is not None
    assert result["color"] == "green"
    assert result["start_idx"] == 20
    assert result["end_idx"] == 24


def test_pullback_into_fib_zone_detected():
    """After impulse, 3 red candles retracing into 0.5 fib → pullback identified."""
    impulse_end_price = 117.0
    impulse_start_price = 100.0
    bars = [_bar(117, 117, 113, 113), _bar(113, 113, 109, 109), _bar(109, 109, 108, 108.5)]
    fib_50 = impulse_end_price - (impulse_end_price - impulse_start_price) * 0.5
    pb = detect_pullback(
        bars, impulse_high=impulse_end_price, impulse_low=impulse_start_price
    )
    assert pb is not None
    assert pb["end_price"] <= fib_50 + 1


def test_continuation_after_valid_pullback():
    """First impulse-color candle after pullback closes back inside zone → signal."""
    bars = [_bar(108.5, 112, 108, 111.5)]  # green close
    cont = detect_continuation(bars, impulse_color="green")
    assert cont is not None
    assert cont["confirmed"] is True


def test_no_signal_in_chop_low_adx():
    """ADX < 25 → evaluate_setup returns None."""
    bars = [_bar(100 + i % 2, 101, 99, 100 + (i + 1) % 2) for i in range(60)]
    out = evaluate_setup(bars, adx_proxy=15.0)
    assert out is None or out["signal"] is None


def test_no_signal_when_pullback_breaks_fib_786():
    """Pullback beyond 0.786 → invalidation, no signal."""
    impulse_high = 117.0
    impulse_low = 100.0
    bars = [_bar(117, 117, 103, 103)]  # retraces all the way past 0.786 (≈103.7)
    pb = detect_pullback(bars, impulse_high=impulse_high, impulse_low=impulse_low)
    assert pb is None


def test_evaluate_full_happy_path():
    """Full impulse + pullback + continuation in TREND_LEVE → signal with confidence."""
    chop = [_bar(100, 101, 99, 100) for _ in range(20)]
    impulse = [
        _bar(100, 103, 100, 102),
        _bar(102, 106, 101, 105),
        _bar(105, 110, 104, 109),
        _bar(109, 114, 108, 113),
        _bar(113, 118, 112, 117),
    ]
    pullback = [
        _bar(117, 117, 113, 113),
        _bar(113, 113, 109, 109),
        _bar(109, 109, 108, 108.5),
    ]
    continuation = [_bar(108.5, 112, 108, 111.5)]
    bars = chop + impulse + pullback + continuation
    out = evaluate_setup(bars, adx_proxy=30.0)
    assert out is not None and out["signal"] is not None
    assert out["signal"]["direction"] == "long"
    assert out["signal"]["confidence"] >= 60
