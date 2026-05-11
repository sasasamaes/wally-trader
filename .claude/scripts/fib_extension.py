#!/usr/bin/env python3
"""fib_extension.py — Fibonacci extension exhaustion detector.

Master's rule: indices/BTC at 150% or 200% weekly fib extension = profit-taking zone.
We auto-detect the most recent valid swing and classify the current price's extension level.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

CR_OFFSET = timezone(timedelta(hours=-6))
LEVELS = [127.2, 150.0, 161.8, 200.0, 261.8]

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"


def extension_pct(swing_low: float, swing_high: float, current: float) -> float:
    rng = swing_high - swing_low
    if rng == 0:
        return 0.0
    return round((current - swing_low) / rng * 100.0, 2)


def classify_label(pct: float) -> str:
    if pct >= 261.8:
        return "EXHAUSTION_EXTREME"
    if pct >= 200.0:
        return "EXHAUSTION_HIGH"
    if pct >= 150.0:
        return "EXHAUSTION_MILD"
    return "OK"


def detect_swing(bars: list[dict]) -> tuple[float, float, int, int]:
    """Find swing low and swing high. Returns (low, high, low_idx, high_idx)."""
    if not bars:
        return 0.0, 0.0, 0, 0
    lows = [b["low"] for b in bars]
    highs = [b["high"] for b in bars]
    low_idx = lows.index(min(lows))
    high_idx = highs.index(max(highs))
    return min(lows), max(highs), low_idx, high_idx


def fetch_bars(symbol: str, tf: str = "1w", bars: int = 100,
               _fetcher=None) -> list[dict]:
    if _fetcher is not None:
        return _fetcher(symbol, tf, bars)
    interval_map = {"1d": "1d", "4h": "4h", "1w": "1w", "1M": "1M"}
    interval = interval_map.get(tf, "1w")
    url = f"{BINANCE_KLINES_URL}?symbol={symbol}&interval={interval}&limit={bars}"
    req = urllib.request.Request(url, headers={"User-Agent": "wally-trader/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read().decode())
    return [
        {"open": float(b[1]), "high": float(b[2]), "low": float(b[3]),
         "close": float(b[4]), "volume": float(b[5])}
        for b in data
    ]


def analyze(symbol: str, tf: str, bars: int, _fetcher=None) -> dict:
    raw = fetch_bars(symbol, tf, bars, _fetcher=_fetcher)
    if not raw:
        return {"symbol": symbol, "tf": tf, "error": "no_bars"}
    swing_low, swing_high, low_idx, high_idx = detect_swing(raw)
    current = raw[-1]["close"]
    ext = extension_pct(swing_low, swing_high, current)
    label = classify_label(ext)
    next_level = next((lvl for lvl in LEVELS if lvl > ext), None)
    next_price = (
        round(swing_low + (next_level / 100.0) * (swing_high - swing_low), 2)
        if next_level else None
    )
    swing_range_pct = (swing_high - swing_low) / swing_low * 100.0 if swing_low else 0.0
    confidence = "low" if swing_range_pct < 5.0 else "normal"
    return {
        "symbol": symbol,
        "tf": tf,
        "swing_low": round(swing_low, 2),
        "swing_high": round(swing_high, 2),
        "swing_range_pct": round(swing_range_pct, 2),
        "current_price": round(current, 2),
        "current_extension_pct": ext,
        "level_label": label,
        "next_level": {"pct": next_level, "price": next_price} if next_level else None,
        "confidence": confidence,
        "ts": datetime.now(CR_OFFSET).isoformat(),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--tf", default="1w")
    p.add_argument("--bars", type=int, default=100)
    p.add_argument("--json", action="store_true")
    p.add_argument("--quick", action="store_true")
    args = p.parse_args()
    try:
        result = analyze(args.symbol, args.tf, args.bars)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    elif args.quick:
        print(f"{args.symbol} {args.tf} ext={result['current_extension_pct']:.1f}%  "
              f"label={result['level_label']}  conf={result['confidence']}")
    else:
        for k, v in result.items():
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
