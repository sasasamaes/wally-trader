"""Tests for market_context.py — discovery + context fetchers (mocked HTTP)."""
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import market_context as mctx  # noqa: E402


# ─── Cache helpers ────────────────────────────────────────────────────────────

def test_cache_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(mctx, "CACHE_DIR", tmp_path)
    payload = {"foo": "bar", "n": 42}
    mctx._write_cache("unit_test", payload)
    out = mctx._read_cache("unit_test", ttl=60)
    assert out == payload


def test_cache_expired_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(mctx, "CACHE_DIR", tmp_path)
    p = tmp_path / "market_stale.json"
    p.write_text(json.dumps({"ts": time.time() - 7200, "payload": {"x": 1}}))
    assert mctx._read_cache("stale", ttl=600) is None


def test_cache_corrupt_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(mctx, "CACHE_DIR", tmp_path)
    p = tmp_path / "market_bad.json"
    p.write_text("{ not json")
    assert mctx._read_cache("bad", ttl=600) is None


# ─── Discovery — Binance volume/movers ────────────────────────────────────────

def _mock_binance_24hr_response():
    return [
        {"symbol": "BTCUSDT", "quoteVolume": "9000000000", "priceChangePercent": "-0.3",
         "lastPrice": "80000", "highPrice": "81000", "lowPrice": "79000"},
        {"symbol": "ETHUSDT", "quoteVolume": "5000000000", "priceChangePercent": "-1.2",
         "lastPrice": "2300", "highPrice": "2350", "lowPrice": "2270"},
        {"symbol": "DOGEUSDT", "quoteVolume": "200000000", "priceChangePercent": "+15.5",
         "lastPrice": "0.11", "highPrice": "0.12", "lowPrice": "0.10"},
        {"symbol": "PUMPUSDT", "quoteVolume": "5000000", "priceChangePercent": "+45.0",
         "lastPrice": "0.001", "highPrice": "0.002", "lowPrice": "0.0008"},
        {"symbol": "BUSDUSDT", "quoteVolume": "100000", "priceChangePercent": "0.0",
         "lastPrice": "1.0", "highPrice": "1.0", "lowPrice": "1.0"},
        {"symbol": "ETHBTC", "quoteVolume": "50000000", "priceChangePercent": "-0.5",
         "lastPrice": "0.05", "highPrice": "0.051", "lowPrice": "0.049"},  # non-USDT, must be excluded
    ]


def test_top_volume_orders_correctly_and_excludes_non_usdt(tmp_path, monkeypatch):
    monkeypatch.setattr(mctx, "CACHE_DIR", tmp_path)
    with patch.object(mctx, "_http_json", return_value=_mock_binance_24hr_response()):
        rows = mctx.fetch_top_volume_binance(n=3)
    assert rows is not None
    assert [r["symbol"] for r in rows] == ["BTCUSDT", "ETHUSDT", "DOGEUSDT"]
    assert rows[0]["vol_24h_usd"] == 9_000_000_000.0
    # ETHBTC was non-USDT — must be excluded entirely
    assert all(r["symbol"].endswith("USDT") for r in rows)


def test_top_movers_filters_low_volume_pump(tmp_path, monkeypatch):
    monkeypatch.setattr(mctx, "CACHE_DIR", tmp_path)
    with patch.object(mctx, "_http_json", return_value=_mock_binance_24hr_response()):
        # min_volume_usd=$50M → DOGEUSDT (15.5%, $200M vol) qualifies, PUMPUSDT (45%, $5M vol) excluded
        rows = mctx.fetch_top_movers_binance(n=3, min_volume_usd=50_000_000)
    assert rows is not None
    syms = [r["symbol"] for r in rows]
    assert "DOGEUSDT" in syms
    assert "PUMPUSDT" not in syms  # excluded by liquidity filter


def test_top_volume_handles_api_failure_gracefully(tmp_path, monkeypatch):
    monkeypatch.setattr(mctx, "CACHE_DIR", tmp_path)
    with patch.object(mctx, "_http_json", side_effect=TimeoutError("simulated")):
        assert mctx.fetch_top_volume_binance(n=10) is None


# ─── Discovery — CoinGecko trending ───────────────────────────────────────────

def test_trending_coingecko_parses_response(tmp_path, monkeypatch):
    monkeypatch.setattr(mctx, "CACHE_DIR", tmp_path)
    mock = {"coins": [
        {"item": {"symbol": "btc", "name": "Bitcoin", "market_cap_rank": 1, "score": 0}},
        {"item": {"symbol": "sol", "name": "Solana", "market_cap_rank": 5, "score": 1}},
    ]}
    with patch.object(mctx, "_http_json", return_value=mock):
        rows = mctx.fetch_trending_coingecko(n=5)
    assert rows is not None
    assert rows[0]["symbol"] == "BTCUSDT"
    assert rows[1]["symbol"] == "SOLUSDT"
    assert rows[0]["rank_market_cap"] == 1


# ─── Bitunix tradeable filter ─────────────────────────────────────────────────

def test_filter_tradeable_uses_full_usdt_symbol(tmp_path, monkeypatch):
    """Regression: Bitunix uses BTCUSDT (with suffix), not BTC."""
    monkeypatch.setattr(mctx, "CACHE_DIR", tmp_path)
    bitunix_mock = {
        "data": [
            {"symbol": "BTCUSDT", "quoteVol": "1500000000", "last": "80500"},
            {"symbol": "ETHUSDT", "quoteVol": "1200000000", "last": "2295"},
            {"symbol": "DOGEUSDT", "quoteVol": "30000000", "last": "0.111"},
            # XRPUSDT is in Binance but NOT in Bitunix → must be filtered out
        ]
    }
    with patch.object(mctx, "_http_json", return_value=bitunix_mock):
        out = mctx.filter_tradeable_bitunix(
            ["BTCUSDT", "ETHUSDT", "XRPUSDT", "DOGEUSDT"], min_vol_usd=10_000_000,
        )
    assert [r["symbol"] for r in out] == ["BTCUSDT", "ETHUSDT", "DOGEUSDT"]
    # Sorted by Bitunix volume descending
    assert out[0]["bitunix_vol_24h_usd"] > out[1]["bitunix_vol_24h_usd"]


def test_filter_tradeable_drops_below_min_volume(tmp_path, monkeypatch):
    monkeypatch.setattr(mctx, "CACHE_DIR", tmp_path)
    bitunix_mock = {
        "data": [
            {"symbol": "BTCUSDT", "quoteVol": "1500000000", "last": "80500"},
            {"symbol": "DEADUSDT", "quoteVol": "5000", "last": "0.001"},  # dead pair
        ]
    }
    with patch.object(mctx, "_http_json", return_value=bitunix_mock):
        out = mctx.filter_tradeable_bitunix(
            ["BTCUSDT", "DEADUSDT"], min_vol_usd=1_000_000,
        )
    assert [r["symbol"] for r in out] == ["BTCUSDT"]
    assert all(r["bitunix_vol_24h_usd"] >= 1_000_000 for r in out)


def test_filter_tradeable_returns_empty_on_bitunix_down(tmp_path, monkeypatch):
    monkeypatch.setattr(mctx, "CACHE_DIR", tmp_path)
    with patch.object(mctx, "_http_json", side_effect=TimeoutError("Bitunix down")):
        assert mctx.filter_tradeable_bitunix(["BTCUSDT", "ETHUSDT"]) == []


# ─── Global context ───────────────────────────────────────────────────────────

def test_global_context_returns_dict_even_on_total_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(mctx, "CACHE_DIR", tmp_path)
    with patch.object(mctx, "_http_json", side_effect=TimeoutError("all down")):
        ctx = mctx.fetch_global_context()
    assert isinstance(ctx, dict)
    assert ctx["fng"] is None
    assert ctx["dominance"] is None
    assert "fetched_at" in ctx


def test_global_context_parses_coingecko_dominance(tmp_path, monkeypatch):
    monkeypatch.setattr(mctx, "CACHE_DIR", tmp_path)

    def fake_http(url, timeout=8):
        if "coingecko.com" in url:
            return {"data": {"market_cap_percentage": {"btc": 58.123, "usdt": 6.789}}}
        if "alternative.me" in url:
            return {"data": [{"value": "42"}]}
        raise ValueError(f"unexpected url: {url}")

    with patch.object(mctx, "_http_json", side_effect=fake_http):
        ctx = mctx.fetch_global_context()
    assert ctx["fng"] == 42
    assert ctx["dominance"]["btc_dominance"] == 58.123
    assert ctx["dominance"]["usdt_dominance"] == 6.789


# ─── Per-asset context ────────────────────────────────────────────────────────

def test_asset_context_combines_ticker_and_funding(tmp_path, monkeypatch):
    monkeypatch.setattr(mctx, "CACHE_DIR", tmp_path)

    def fake_http(url, timeout=8):
        if "premiumIndex" in url:
            return {"lastFundingRate": "0.0001"}
        if "ticker/24hr" in url:
            return _mock_binance_24hr_response()
        raise ValueError(url)

    with patch.object(mctx, "_http_json", side_effect=fake_http):
        ctx = mctx.fetch_asset_context("BTCUSDT")
    assert ctx["symbol"] == "BTCUSDT"
    assert ctx["binance_24h"]["vol_24h_usd"] == 9_000_000_000.0
    assert ctx["funding_rate_8h"] == 0.0001
    assert ctx["funding_pct_8h"] == 0.01  # 0.0001 * 100 = 0.01


def test_asset_context_handles_unknown_symbol(tmp_path, monkeypatch):
    monkeypatch.setattr(mctx, "CACHE_DIR", tmp_path)

    def fake_http(url, timeout=8):
        if "premiumIndex" in url:
            return {"lastFundingRate": "0.0001"}
        return _mock_binance_24hr_response()

    with patch.object(mctx, "_http_json", side_effect=fake_http):
        ctx = mctx.fetch_asset_context("NOPE_DOES_NOT_EXIST_USDT")
    assert ctx["binance_24h"] is None
    assert ctx["funding_pct_8h"] is not None  # funding endpoint still hit
