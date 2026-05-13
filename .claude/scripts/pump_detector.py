#!/usr/bin/env python3
"""pump_detector.py — Direction-agnostic pump-in-progress detector.

Combines four free signals from Binance public endpoints into a 0-100 score:

  vol_spike_ratio = last_1h_vol / avg_24h_vol           (weight 30)
  oi_surge_pct    = (oi_1h - oi_24h_ago) / oi_24h_ago    (weight 30)
  funding_extreme = abs(funding_8h) capped at 0.1        (weight 25)
  chg_24h_abs     = abs(24h price change %)              (weight 15)

side_bias:
  LONG  if 24h_chg > 0 AND retail_ls < 1.0 (retail still short → squeeze fuel)
  SHORT if 24h_chg > 15% AND vol_spike > 2.5 (climax-buying — fade material)
  NONE  otherwise

Output JSON:
  {symbol, score, side_bias, vol_spike, oi_surge_pct, funding_8h, chg_24h, retail_ls, components}

This is a SEPARATE concept from extreme_momentum_fade.py — that helper
specifically picks reversal-biased fade entries. pump_detector just answers
"is this asset moving violently right now?" without committing to a side.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from typing import Any

CACHE: dict[str, dict] = {}
CACHE_TTL_SEC = 60


def _get(url: str) -> Any:
    cached = CACHE.get(url)
    if cached and time.time() - cached["ts"] < CACHE_TTL_SEC:
        return cached["data"]
    req = urllib.request.Request(url, headers={"User-Agent": "wally-trader/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    CACHE[url] = {"ts": time.time(), "data": data}
    return data


def detect(symbol: str) -> dict:
    """Compute pump score + side bias for `symbol`. Never raises."""
    sym = symbol.replace(".P", "").upper()
    try:
        t24 = _get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={sym}")
        chg_24h = float(t24["priceChangePercent"])
        avg_vol_24h = float(t24["volume"]) / 24.0
    except Exception as e:
        return {"symbol": sym, "score": 0, "side_bias": "NONE",
                "error": f"24h ticker: {e}"}

    # 1h vol from latest 1h kline
    try:
        klines_1h = _get(
            f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1h&limit=1")
        vol_1h = float(klines_1h[-1][5])
    except Exception:
        vol_1h = avg_vol_24h
    vol_spike = (vol_1h / avg_vol_24h) if avg_vol_24h > 0 else 1.0

    # OI surge (futures only — falls back to 0 if unavailable)
    oi_surge = 0.0
    try:
        oi_hist = _get(
            f"https://fapi.binance.com/futures/data/openInterestHist"
            f"?symbol={sym}&period=1h&limit=24")
        if len(oi_hist) >= 24:
            oi_now = float(oi_hist[-1]["sumOpenInterestValue"])
            oi_24h_ago = float(oi_hist[0]["sumOpenInterestValue"])
            if oi_24h_ago > 0:
                oi_surge = (oi_now - oi_24h_ago) / oi_24h_ago * 100
    except Exception:
        pass

    # Funding (Binance premium index)
    funding = 0.0
    try:
        prem = _get(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={sym}")
        if isinstance(prem, dict):
            funding = float(prem.get("lastFundingRate") or 0.0)
    except Exception:
        pass

    # Retail L/S (for side bias)
    retail_ls = None
    try:
        ls = _get(
            f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
            f"?symbol={sym}&period=1h&limit=1")
        retail_ls = float(ls[0]["longShortRatio"])
    except Exception:
        pass

    # Score components (each capped at its weight)
    s_vol = min(vol_spike / 3.0, 1.0) * 30          # 3x = full
    s_oi = min(abs(oi_surge) / 20.0, 1.0) * 30      # 20% = full
    s_funding = min(abs(funding) / 0.001, 1.0) * 25  # 0.10% = full
    s_chg = min(abs(chg_24h) / 15.0, 1.0) * 15       # 15% = full
    score = s_vol + s_oi + s_funding + s_chg

    # Side bias logic
    side_bias = "NONE"
    if chg_24h >= 15.0 and vol_spike >= 2.5:
        side_bias = "SHORT"  # climax-buying → fade
    elif chg_24h > 0 and retail_ls is not None and retail_ls < 1.0:
        side_bias = "LONG"   # rally with retail still short = squeeze fuel
    elif chg_24h <= -8.0 and vol_spike >= 2.0:
        side_bias = "LONG"   # capitulation = bounce setup
    elif chg_24h < 0 and retail_ls is not None and retail_ls > 1.5:
        side_bias = "SHORT"  # decline with retail still long = long squeeze setup

    return {
        "symbol": sym,
        "score": round(score, 1),
        "side_bias": side_bias,
        "vol_spike": round(vol_spike, 2),
        "oi_surge_pct": round(oi_surge, 2),
        "funding_8h_pct": round(funding * 100, 4),
        "chg_24h_pct": round(chg_24h, 2),
        "retail_ls": retail_ls,
        "components": {
            "vol": round(s_vol, 2),
            "oi": round(s_oi, 2),
            "funding": round(s_funding, 2),
            "chg": round(s_chg, 2),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--symbol", required=True, help="e.g. BTCUSDT")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quick", action="store_true",
                    help="Human-readable one-liner")
    args = ap.parse_args()

    out = detect(args.symbol)
    if args.quick:
        print(f"{out['symbol']}: pump_score={out['score']}/100 "
              f"side_bias={out['side_bias']}  "
              f"vol×{out['vol_spike']} OI{out['oi_surge_pct']:+}% "
              f"funding{out['funding_8h_pct']:+}% chg{out['chg_24h_pct']:+}%")
    else:
        print(json.dumps(out, indent=2 if not args.json else None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
