#!/usr/bin/env python3
"""volume_divergence.py — detect price/OBV divergence pre-entry.

Master's veto: precio sube sin fuerza, oscilador cae → not credible.
OBV (On-Balance Volume) slope vs price slope; if they diverge against
the proposed trade direction, warn.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

CR_OFFSET = timezone(timedelta(hours=-6))
MIN_BARS = 30
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"


def fetch_bars(symbol: str, tf: str = "1h", bars: int = 50,
               _fetcher=None) -> list[dict]:
    """Fetch OHLCV from Binance public API. _fetcher injectable for tests."""
    if _fetcher is not None:
        return _fetcher(symbol, tf, bars)
    interval_map = {"15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
    interval = interval_map.get(tf, "1h")
    url = f"{BINANCE_KLINES_URL}?symbol={symbol}&interval={interval}&limit={bars}"
    req = urllib.request.Request(url, headers={"User-Agent": "wally-trader/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read().decode())
    return [
        {"open": float(b[1]), "high": float(b[2]), "low": float(b[3]),
         "close": float(b[4]), "volume": float(b[5])}
        for b in data
    ]


def compute_obv(bars: list[dict]) -> list[float]:
    """On-Balance Volume cumulative series."""
    if not bars:
        return []
    obv = [0.0]
    for i in range(1, len(bars)):
        prev_close = bars[i - 1]["close"]
        close = bars[i]["close"]
        vol = bars[i]["volume"]
        if close > prev_close:
            obv.append(obv[-1] + vol)
        elif close < prev_close:
            obv.append(obv[-1] - vol)
        else:
            obv.append(obv[-1])
    return obv


def linear_slope(series: list[float]) -> float:
    """Least-squares slope."""
    n = len(series)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(series) / n
    num = sum((i - x_mean) * (series[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den else 0.0


def detect_divergence(bars: list[dict], direction: str = "LONG") -> dict:
    """Detect price-OBV divergence relative to proposed trade direction.

    Divergence is detected when price direction and volume momentum disagree:
    - BEARISH: price rising but volume declining (weakening buying pressure), OR
               price rising but OBV slope negative
    - BULLISH: price falling but volume rising (accumulation), OR
               price falling but OBV slope positive
    """
    if len(bars) < MIN_BARS:
        return {"divergence": "INSUFFICIENT_DATA", "n_bars": len(bars), "verdict": "OK"}

    closes = [b["close"] for b in bars]
    volumes = [b["volume"] for b in bars]
    obv = compute_obv(bars)
    price_slope = linear_slope(closes)
    obv_slope = linear_slope(obv)
    vol_slope = linear_slope(volumes)
    price_change_pct = (closes[-1] - closes[0]) / closes[0] * 100.0 if closes[0] else 0.0
    volume_change_pct = ((bars[-1]["volume"] - bars[0]["volume"]) / bars[0]["volume"] * 100.0
                        if bars[0]["volume"] else 0.0)

    divergence = "NONE"
    verdict = "OK"

    # Bearish divergence: price up but volume momentum down (OBV or raw vol)
    bearish_div = price_slope > 0 and (obv_slope < 0 or vol_slope < 0)
    # Bullish divergence: price down but volume momentum up (OBV or raw vol)
    bullish_div = price_slope < 0 and (obv_slope > 0 or vol_slope > 0)

    if bearish_div:
        divergence = "BEARISH"
        if direction.upper() == "LONG":
            verdict = "WARN_DIVERGENCE_AGAINST_LONG"
    elif bullish_div:
        divergence = "BULLISH"
        if direction.upper() == "SHORT":
            verdict = "WARN_DIVERGENCE_AGAINST_SHORT"

    return {
        "n_bars": len(bars),
        "price_change_pct": round(price_change_pct, 3),
        "volume_change_pct": round(volume_change_pct, 3),
        "price_slope": round(price_slope, 6),
        "obv_slope": round(obv_slope, 2),
        "vol_slope": round(vol_slope, 4),
        "divergence": divergence,
        "verdict": verdict,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--tf", default="1h")
    p.add_argument("--bars", type=int, default=50)
    p.add_argument("--direction", default="LONG", choices=["LONG", "SHORT"])
    p.add_argument("--json", action="store_true")
    p.add_argument("--quick", action="store_true")
    args = p.parse_args()

    try:
        bars = fetch_bars(args.symbol, args.tf, args.bars)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR fetching bars: {e}", file=sys.stderr)
        return 2

    result = detect_divergence(bars, direction=args.direction)
    result["symbol"] = args.symbol
    result["tf"] = args.tf
    result["direction"] = args.direction.upper()
    result["ts"] = datetime.now(CR_OFFSET).isoformat()

    if args.json:
        print(json.dumps(result, indent=2))
    elif args.quick:
        print(f"{args.symbol} {args.tf} {args.direction.upper()}: "
              f"div={result['divergence']}  verdict={result['verdict']}  "
              f"price={result['price_change_pct']:+.2f}%  "
              f"vol={result['volume_change_pct']:+.2f}%")
    else:
        for k, v in result.items():
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
