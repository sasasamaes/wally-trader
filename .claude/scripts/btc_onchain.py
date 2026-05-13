#!/usr/bin/env python3
"""btc_onchain.py — Free-tier on-chain bias for BTC (and ETH-best-effort).

Combines three free sources to derive a coarse BULL/NEUTRAL/BEAR bias:

  difficulty_progress  (mempool.space/api/v1/difficulty-adjustment)
                       — positive remaining-time = miners under pressure (BEAR
                       short-term); large negative = network hashpower surge
                       (BULL).
  txs_per_day_trend    (blockchain.info/charts/n-transactions?timespan=30days)
                       — rising = adoption proxy (mild BULL); falling = retail
                       leaving (mild BEAR).
  mvrv_z_proxy         (price vs 200-day SMA — synthetic for MVRV-Z)
                       — high z = overheated (BEAR); low z = discount (BULL).
                       Computed from Binance daily klines (no API key).

This is INTENTIONALLY coarse — real MVRV/SOPR/exchange-flows are paid only.
The output is a single bias label + confidence, cached 1 hour to avoid
hammering free endpoints.

Output JSON:
  {symbol, bias, confidence, components, freshness_sec}
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parent.parent / "cache" / "btc_onchain.json"
CACHE_TTL_SEC = 3600


def _get_json(url: str, timeout: int = 8):
    req = urllib.request.Request(url, headers={"User-Agent": "wally-trader/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _difficulty_signal() -> tuple[str, float]:
    """Return (component_label, score in [-1, +1])."""
    try:
        d = _get_json("https://mempool.space/api/v1/difficulty-adjustment")
        # remainingTime: estimate seconds until adjustment
        # progressPercent: progress through current epoch
        # difficultyChange: expected % change at next adjustment
        change = float(d.get("difficultyChange") or 0)
        if change > 4.0:
            return ("difficulty_bullish_hashrate", 0.6)
        if change > 1.0:
            return ("difficulty_neutral_up", 0.2)
        if change < -2.0:
            return ("difficulty_bearish_capitulation", -0.6)
        if change < -0.5:
            return ("difficulty_neutral_down", -0.2)
        return ("difficulty_flat", 0.0)
    except Exception:
        return ("difficulty_unavailable", 0.0)


def _tx_trend_signal() -> tuple[str, float]:
    try:
        d = _get_json(
            "https://api.blockchain.info/charts/n-transactions"
            "?timespan=30days&sampled=false&format=json"
        )
        values = d.get("values") or []
        if len(values) < 10:
            return ("tx_unavailable", 0.0)
        first_half = sum(v["y"] for v in values[: len(values) // 2])
        second_half = sum(v["y"] for v in values[len(values) // 2:])
        change = (second_half - first_half) / first_half if first_half else 0.0
        if change > 0.10:
            return ("tx_rising_strong", 0.4)
        if change > 0.03:
            return ("tx_rising", 0.2)
        if change < -0.10:
            return ("tx_falling_strong", -0.4)
        if change < -0.03:
            return ("tx_falling", -0.2)
        return ("tx_flat", 0.0)
    except Exception:
        return ("tx_unavailable", 0.0)


def _mvrv_z_proxy(symbol: str = "BTCUSDT") -> tuple[str, float]:
    """Synthetic z-score: (price - SMA200) / stdev_200 on daily bars."""
    try:
        klines = _get_json(
            f"https://api.binance.com/api/v3/klines"
            f"?symbol={symbol}&interval=1d&limit=200"
        )
        closes = [float(b[4]) for b in klines]
        if len(closes) < 100:
            return ("mvrv_insufficient_history", 0.0)
        mean = sum(closes) / len(closes)
        var = sum((c - mean) ** 2 for c in closes) / len(closes)
        std = math.sqrt(var) if var > 0 else 1.0
        z = (closes[-1] - mean) / std
        if z > 2.0:
            return ("mvrv_overheated", -0.8)
        if z > 1.0:
            return ("mvrv_warm", -0.3)
        if z < -2.0:
            return ("mvrv_deep_discount", 0.8)
        if z < -1.0:
            return ("mvrv_discount", 0.3)
        return ("mvrv_neutral", 0.0)
    except Exception:
        return ("mvrv_unavailable", 0.0)


def assess(symbol: str = "BTCUSDT") -> dict:
    diff_lbl, diff_s = _difficulty_signal()
    tx_lbl, tx_s = _tx_trend_signal()
    mvrv_lbl, mvrv_s = _mvrv_z_proxy(symbol)

    composite = (diff_s + tx_s + mvrv_s) / 3.0
    if composite >= 0.3:
        bias = "BULL"
    elif composite <= -0.3:
        bias = "BEAR"
    else:
        bias = "NEUTRAL"

    return {
        "symbol": symbol,
        "bias": bias,
        "confidence": round(abs(composite) * 100, 1),
        "components": {
            "difficulty": {"label": diff_lbl, "score": round(diff_s, 2)},
            "tx_trend": {"label": tx_lbl, "score": round(tx_s, 2)},
            "mvrv_z_proxy": {"label": mvrv_lbl, "score": round(mvrv_s, 2)},
        },
        "composite": round(composite, 3),
    }


def assess_cached(symbol: str = "BTCUSDT") -> dict:
    if CACHE_PATH.exists():
        try:
            data = json.loads(CACHE_PATH.read_text())
            ts = float(data.get("_ts", 0))
            if time.time() - ts < CACHE_TTL_SEC and data.get("symbol") == symbol:
                data["freshness_sec"] = int(time.time() - ts)
                return data
        except Exception:
            pass
    result = assess(symbol)
    result["_ts"] = time.time()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(result, indent=2))
    result["freshness_sec"] = 0
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    out = assess(args.symbol) if args.no_cache else assess_cached(args.symbol)
    if args.quick:
        print(f"{out['symbol']}: {out['bias']} (confidence {out['confidence']}%)  "
              f"diff={out['components']['difficulty']['label']} "
              f"tx={out['components']['tx_trend']['label']} "
              f"mvrv={out['components']['mvrv_z_proxy']['label']}")
    else:
        # Don't dump the internal _ts in user-facing JSON
        out_clean = {k: v for k, v in out.items() if not k.startswith("_")}
        print(json.dumps(out_clean, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
