"""Tests for extreme_momentum_fade.py — pure logic without network."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch


def _load():
    sp = Path(__file__).resolve().parents[3] / ".claude" / "scripts" / "extreme_momentum_fade.py"
    assert sp.exists(), sp
    spec = importlib.util.spec_from_file_location("ext_mom", str(sp))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ext_mom"] = mod
    spec.loader.exec_module(mod)
    return mod


emf = _load()


def _mock_data(
    chg_24h: float,
    rsi: float,
    last: float = 100.0,
    high_24h: float = 110.0,
    low_24h: float = 90.0,
    vol_decay: float = 0.3,  # buyers exhausted
    smart_ls: float | None = 1.2,
    retail_ls: float | None = 1.7,
):
    """Generate mock fetch data for detect_pattern."""
    # 24hr ticker
    t24 = {
        "priceChangePercent": str(chg_24h),
        "lastPrice": str(last),
        "highPrice": str(high_24h),
        "lowPrice": str(low_24h),
    }
    # 1H bars: last has low vol = exhaustion
    bars_1h = []
    peak_vol = 1000000
    for i in range(24):
        # Make i=12 the peak (12h ago), i=23 is last bar
        if i == 12:
            v = peak_vol
        elif i == 23:
            v = peak_vol * vol_decay
        else:
            v = peak_vol * 0.7
        bars_1h.append([0, last, last + 1, last - 1, last, v, 0, 0, 0, 0, 0, 0])
    return t24, bars_1h, smart_ls, retail_ls


def test_no_match_when_lateral_market():
    """Low chg + neutral RSI → NO_MATCH."""
    t24, bars, smart, retail = _mock_data(chg_24h=-1.0, rsi=50.0)
    with patch.object(emf, "http_get", side_effect=lambda u, **kw: (
        t24 if "ticker/24hr" in u else
        bars if "klines" in u else
        [{"longShortRatio": str(smart)}] if "topLongShort" in u else
        [{"longShortRatio": str(retail)}]
    )):
        with patch.object(emf, "compute_rsi_1h", return_value=50.0):
            r = emf.detect_pattern("LATERALCOIN")
    assert r["verdict"] == "NO_MATCH"
    assert r["side"] is None


def test_match_short_when_extreme_pump():
    """24h +20% + RSI 80 + vol decay → SHORT match."""
    t24, bars, smart, retail = _mock_data(chg_24h=20.0, rsi=82.0, last=100.0, high_24h=102.0)
    with patch.object(emf, "http_get", side_effect=lambda u, **kw: (
        t24 if "ticker/24hr" in u else
        bars if "klines" in u else
        [{"longShortRatio": str(smart)}] if "topLongShort" in u else
        [{"longShortRatio": str(retail)}]
    )):
        with patch.object(emf, "compute_rsi_1h", return_value=82.0):
            r = emf.detect_pattern("PUMPCOIN")
    assert r["side"] == "SHORT"
    assert r["verdict"] in ("MATCH", "STRONG_MATCH")
    assert r["score"] >= 50
    assert any("PUMP_FADE" in s for s in r["signals"]) or "PUMP_FADE" in r["side_signal"]


def test_match_long_when_extreme_dump():
    """24h -10% + RSI 22 + vol decay → LONG match."""
    t24, bars, smart, retail = _mock_data(
        chg_24h=-10.0, rsi=22.0, last=100.0, low_24h=98.0,
        smart_ls=0.8, retail_ls=0.5,
    )
    with patch.object(emf, "http_get", side_effect=lambda u, **kw: (
        t24 if "ticker/24hr" in u else
        bars if "klines" in u else
        [{"longShortRatio": str(smart)}] if "topLongShort" in u else
        [{"longShortRatio": str(retail)}]
    )):
        with patch.object(emf, "compute_rsi_1h", return_value=22.0):
            r = emf.detect_pattern("DUMPCOIN")
    assert r["side"] == "LONG"
    assert r["verdict"] in ("MATCH", "STRONG_MATCH")


def test_hard_reject_when_smart_money_extreme_against():
    """Smart Money L/S > 4.0 → HARD_REJECT regardless of pattern."""
    t24, bars, smart, retail = _mock_data(chg_24h=20.0, rsi=85.0, smart_ls=4.5)
    with patch.object(emf, "http_get", side_effect=lambda u, **kw: (
        t24 if "ticker/24hr" in u else
        bars if "klines" in u else
        [{"longShortRatio": str(smart)}] if "topLongShort" in u else
        [{"longShortRatio": str(retail)}]
    )):
        with patch.object(emf, "compute_rsi_1h", return_value=85.0):
            r = emf.detect_pattern("BLOCKED")
    assert r["verdict"] == "HARD_REJECT"
    assert "extreme bull" in r["reason"]


def test_strong_match_when_all_signals_align():
    """Maximum score combination → STRONG_MATCH (score >=70)."""
    # Pump 25% + RSI 88 + vol decay 0.2 + close to peak + retail trapped
    t24, bars, smart, retail = _mock_data(
        chg_24h=25.0, rsi=88.0, last=100.0, high_24h=101.0,
        vol_decay=0.2, smart_ls=1.2, retail_ls=1.9,
    )
    with patch.object(emf, "http_get", side_effect=lambda u, **kw: (
        t24 if "ticker/24hr" in u else
        bars if "klines" in u else
        [{"longShortRatio": str(smart)}] if "topLongShort" in u else
        [{"longShortRatio": str(retail)}]
    )):
        with patch.object(emf, "compute_rsi_1h", return_value=88.0):
            r = emf.detect_pattern("PERFECTSHORT")
    assert r["verdict"] == "STRONG_MATCH"
    assert r["score"] >= 70


def test_partial_match_when_only_some_signals():
    """Pump but weak vol decay + medium RSI + far from peak → low score."""
    t24, bars, smart, retail = _mock_data(
        chg_24h=16.0, rsi=76.0, last=95.0, high_24h=110.0,  # 13.6% from peak
        vol_decay=0.7, smart_ls=1.4, retail_ls=1.3,
    )
    with patch.object(emf, "http_get", side_effect=lambda u, **kw: (
        t24 if "ticker/24hr" in u else
        bars if "klines" in u else
        [{"longShortRatio": str(smart)}] if "topLongShort" in u else
        [{"longShortRatio": str(retail)}]
    )):
        with patch.object(emf, "compute_rsi_1h", return_value=76.0):
            r = emf.detect_pattern("MIDPATTERN")
    assert r["side"] == "SHORT"
    # Partial signals → low score (NO_MATCH or PARTIAL_MATCH)
    assert r["verdict"] in ("NO_MATCH", "PARTIAL_MATCH", "MATCH")
    # The setup direction is detected even if score is low
    assert "PUMP_FADE" in r.get("side_signal", "")


def test_handles_missing_ls_data():
    """If LS API returns empty, still produce verdict (no crash)."""
    t24, bars, smart, retail = _mock_data(chg_24h=20.0, rsi=82.0, smart_ls=None, retail_ls=None)

    def mock_http(u, **kw):
        if "ticker/24hr" in u:
            return t24
        if "klines" in u:
            return bars
        # Simulate failure on L/S endpoints
        raise Exception("404 not on Binance Futures")

    with patch.object(emf, "http_get", side_effect=mock_http):
        with patch.object(emf, "compute_rsi_1h", return_value=82.0):
            r = emf.detect_pattern("NEWCOIN")
    # Should not crash, returns NO_MATCH or similar
    assert "verdict" in r


def test_compute_rsi_extreme_overbought():
    """RSI computation correctness — synthetic strong-uptrend bars."""
    bars = [[0, 100.0 + i, 100.0 + i, 100.0 + i, 100.0 + i, 100, 0, 0, 0, 0, 0, 0] for i in range(30)]
    with patch.object(emf, "http_get", return_value=bars):
        rsi = emf.compute_rsi_1h("FAKE", length=14)
    # Strong uptrend: RSI should be >70
    assert rsi >= 70


def test_compute_rsi_no_loss_returns_100():
    """If avg_loss == 0, RSI returns 100 (no division-by-zero)."""
    bars = [[0, 100.0, 100.0, 100.0, 100.0 + i, 100, 0, 0, 0, 0, 0, 0] for i in range(20)]
    with patch.object(emf, "http_get", return_value=bars):
        rsi = emf.compute_rsi_1h("FAKE")
    assert rsi == 100.0
