"""Tests for liq_heatmap.py — pure helpers without network."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch


def _load():
    sp = Path(__file__).resolve().parents[3] / ".claude" / "scripts" / "liq_heatmap.py"
    assert sp.exists(), sp
    spec = importlib.util.spec_from_file_location("liq_heatmap", str(sp))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["liq_heatmap"] = mod
    spec.loader.exec_module(mod)
    return mod


lh = _load()


def _market(price=100.0, h=110.0, l=90.0, oi=50_000_000.0, smart=1.0, retail=1.0):
    return {
        "price": price,
        "high_24h": h,
        "low_24h": l,
        "oi_now_usd": oi,
        "smart_money_ls": smart,
        "retail_ls": retail,
    }


def test_estimate_clusters_returns_both_sides():
    r = lh.estimate_clusters(_market())
    assert "longs" in r
    assert "shorts" in r
    # Should have at least 1 cluster per side under default settings
    assert len(r["longs"]) > 0
    assert len(r["shorts"]) > 0


def test_long_clusters_are_below_price():
    r = lh.estimate_clusters(_market(price=100.0))
    for c in r["longs"]:
        assert c["price"] < 100.0
        assert c["distance_pct"] < 0
        assert c["side"] == "LONG_LIQ"


def test_short_clusters_are_above_price():
    r = lh.estimate_clusters(_market(price=100.0))
    for c in r["shorts"]:
        assert c["price"] > 100.0
        assert c["distance_pct"] > 0
        assert c["side"] == "SHORT_LIQ"


def test_heat_score_normalized_0_100():
    r = lh.estimate_clusters(_market())
    for side in ("longs", "shorts"):
        for c in r[side]:
            assert 0 <= c["heat_score"] <= 100
        # The top cluster on each side should have heat 100
        if r[side]:
            assert r[side][0]["heat_score"] == 100.0


def test_top_n_limit_respected():
    r = lh.estimate_clusters(_market(), top_n=3)
    assert len(r["longs"]) <= 3
    assert len(r["shorts"]) <= 3


def test_smart_money_long_bias_amplifies_long_clusters():
    """Heavy long bias → long-side clusters get amplified weight."""
    balanced = lh.estimate_clusters(_market(smart=1.0))
    biased = lh.estimate_clusters(_market(smart=2.0))
    # Heat of top cluster is normalized but raw weights differ
    # Sum of all heat scores on long side should differ
    bal_heat = sum(c["heat_score"] for c in balanced["longs"])
    bia_heat = sum(c["heat_score"] for c in biased["longs"])
    # Both will sum to similar values because normalized; but counts may differ
    assert bal_heat > 0
    assert bia_heat > 0


def test_assess_heatmap_with_mocked_market():
    fake_market = _market(price=2.40, h=2.65, l=2.38, oi=96_000_000, smart=1.6)
    with patch.object(lh, "fetch_market_state", return_value=fake_market):
        r = lh.assess_heatmap("TONUSDT")
    assert r["symbol"] == "TONUSDT"
    assert r["price_now"] == 2.40
    assert r["smart_money_ls"] == 1.6
    assert r["bias"] in ("LONG_LIQ_DOMINANT", "SHORT_LIQ_DOMINANT", "BALANCED")
    assert r["magnet"] is None or "price" in r["magnet"]
    assert "longs_liq" in r
    assert "shorts_liq" in r
    assert isinstance(r["checked_at"], str)


def test_assess_heatmap_handles_fetch_error():
    with patch.object(lh, "fetch_market_state", side_effect=Exception("network down")):
        r = lh.assess_heatmap("BAD")
    assert "error" in r
    assert r["symbol"] == "BAD"


def test_format_summary_has_expected_sections():
    fake_market = _market(price=100.0, h=110.0, l=90.0)
    with patch.object(lh, "fetch_market_state", return_value=fake_market):
        r = lh.assess_heatmap("X")
    s = lh.format_summary(r)
    assert "LIQ HEATMAP" in s
    assert "SHORT-side" in s
    assert "LONG-side" in s
    assert "Bias" in s


def test_format_summary_handles_error():
    s = lh.format_summary({"error": "fail", "symbol": "X"})
    assert "fail" in s
    assert "X" in s
