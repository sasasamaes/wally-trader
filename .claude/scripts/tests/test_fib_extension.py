"""Tests for fib_extension.py."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import fib_extension as fe


def test_extension_pct_at_150():
    pct = fe.extension_pct(swing_low=100, swing_high=200, current=250)
    assert pct == 150.0


def test_extension_pct_at_200():
    pct = fe.extension_pct(swing_low=100, swing_high=200, current=300)
    assert pct == 200.0


def test_extension_pct_at_swing_high():
    pct = fe.extension_pct(swing_low=100, swing_high=200, current=200)
    assert pct == 100.0


def test_classify_label_ok():
    assert fe.classify_label(120.0) == "OK"


def test_classify_label_mild():
    assert fe.classify_label(155.0) == "EXHAUSTION_MILD"


def test_classify_label_high():
    assert fe.classify_label(210.0) == "EXHAUSTION_HIGH"


def test_classify_label_extreme():
    assert fe.classify_label(275.0) == "EXHAUSTION_EXTREME"


def test_detect_swing_picks_min_low_and_max_high():
    bars = [
        {"high": 100, "low": 90, "close": 95},
        {"high": 110, "low": 80, "close": 105},
        {"high": 130, "low": 95, "close": 125},
    ]
    low, high, low_idx, high_idx = fe.detect_swing(bars)
    assert low == 80
    assert high == 130
    assert low_idx == 1
    assert high_idx == 2


def test_retracement_explicit_swing_levels():
    """Given an explicit swing high/low, all 5 retracement levels are correct."""
    from fib_extension import retracement_zones

    out = retracement_zones(swing_low=73500.0, swing_high=78285.0, direction="long")

    rng = 78285.0 - 73500.0
    assert abs(out["entry_zones"]["382"] - (78285.0 - rng * 0.382)) < 1e-6
    assert abs(out["entry_zones"]["500"] - (78285.0 - rng * 0.500)) < 1e-6
    assert abs(out["entry_zones"]["618"] - (78285.0 - rng * 0.618)) < 1e-6
    assert abs(out["sl_075"] - (78285.0 - rng * 0.75)) < 1e-6
    assert out["tp_swing"] == 78285.0
    assert out["direction"] == "long"


def test_retracement_direction_autodetect():
    """A bar series ending above the midpoint of the recent swing infers LONG bias."""
    from fib_extension import autodetect_direction

    # 10 synthetic closes forming a swing low at 100, swing high at 200, ending at 175 (above mid)
    closes = [100, 110, 130, 160, 190, 200, 195, 185, 178, 175]
    assert autodetect_direction(closes) == "long"

    # ending at 125 (below mid 150) → short
    closes_short = [200, 190, 170, 150, 130, 110, 100, 105, 115, 125]
    assert autodetect_direction(closes_short) == "short"
