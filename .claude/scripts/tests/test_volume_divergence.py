"""Tests for volume_divergence.py."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import volume_divergence as vd


def _synthetic_bars(price_slope: float, volume_slope: float, n: int = 50) -> list[dict]:
    """Generate n bars with given linear price and volume slopes."""
    bars = []
    base_price = 70000.0
    base_vol = 1000.0
    for i in range(n):
        close = base_price + price_slope * i
        prev_close = base_price + price_slope * (i - 1) if i > 0 else close
        vol = max(10.0, base_vol + volume_slope * i)
        bars.append({
            "open": prev_close,
            "high": close + 50,
            "low": close - 50,
            "close": close,
            "volume": vol,
        })
    return bars


def test_obv_slope_positive_when_price_and_volume_up():
    bars = _synthetic_bars(price_slope=10.0, volume_slope=20.0)
    obv = vd.compute_obv(bars)
    slope = vd.linear_slope(obv)
    assert slope > 0


def test_bearish_divergence_price_up_obv_down():
    bars = _synthetic_bars(price_slope=10.0, volume_slope=-15.0)
    result = vd.detect_divergence(bars, direction="LONG")
    assert result["divergence"] == "BEARISH"


def test_no_divergence_when_aligned():
    bars = _synthetic_bars(price_slope=10.0, volume_slope=20.0)
    result = vd.detect_divergence(bars, direction="LONG")
    assert result["divergence"] == "NONE"


def test_insufficient_data():
    result = vd.detect_divergence([{"close": 1, "volume": 1}] * 5, direction="LONG")
    assert result["divergence"] == "INSUFFICIENT_DATA"


def test_bullish_divergence_warns_against_short():
    bars = _synthetic_bars(price_slope=-10.0, volume_slope=20.0)
    result = vd.detect_divergence(bars, direction="SHORT")
    assert result["divergence"] == "BULLISH"
    assert "WARN" in result["verdict"]
