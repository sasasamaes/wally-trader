"""Tests for usdtd_tracker.py."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import usdtd_tracker as ut


def test_classify_trend_up():
    assert ut.classify_trend(change_7d_pct=2.5) == "UP"


def test_classify_trend_down():
    assert ut.classify_trend(change_7d_pct=-1.2) == "DOWN"


def test_classify_trend_flat():
    assert ut.classify_trend(change_7d_pct=0.3) == "FLAT"


def test_btc_bias_from_usdtd_up_is_bearish():
    # USDT.D UP → BEARISH for BTC (capital flowing into stables)
    assert ut.btc_bias_from_usdtd("UP") == "BEARISH"


def test_btc_bias_from_usdtd_down_is_bullish():
    assert ut.btc_bias_from_usdtd("DOWN") == "BULLISH"


def test_btc_bias_from_usdtd_flat_is_neutral():
    assert ut.btc_bias_from_usdtd("FLAT") == "NEUTRAL"
