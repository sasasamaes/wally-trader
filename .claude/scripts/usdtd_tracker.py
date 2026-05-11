#!/usr/bin/env python3
"""usdtd_tracker.py — Track USDT dominance + BTC dominance for inverse-correlation signal.

USDT.D rising = capital rotating into stables = bearish for BTC
USDT.D falling = capital leaving stables = bullish for BTC

Source: CoinGecko global API (free, no auth).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

CR_OFFSET = timezone(timedelta(hours=-6))
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_FILE = CACHE_DIR / "usdtd.json"
CACHE_TTL_SEC = 600  # 10 minutes
COINGECKO_URL = "https://api.coingecko.com/api/v3/global"
FLAT_THRESHOLD_PCT = 0.5  # ±0.5% 7d = FLAT


def classify_trend(change_7d_pct: float) -> str:
    if change_7d_pct > FLAT_THRESHOLD_PCT:
        return "UP"
    if change_7d_pct < -FLAT_THRESHOLD_PCT:
        return "DOWN"
    return "FLAT"


def btc_bias_from_usdtd(trend: str) -> str:
    return {"UP": "BEARISH", "DOWN": "BULLISH", "FLAT": "NEUTRAL"}.get(trend, "UNKNOWN")


def _fetch_coingecko_global(timeout: int = 10) -> dict:
    req = urllib.request.Request(
        COINGECKO_URL,
        headers={"User-Agent": "wally-trader/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _load_cache() -> dict | None:
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text())
        if time.time() - data.get("cached_at", 0) > CACHE_TTL_SEC:
            return None
        return data["payload"]
    except (json.JSONDecodeError, KeyError):
        return None


def _save_cache(payload: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps({
        "cached_at": time.time(),
        "payload": payload,
    }))


def fetch_dominance(use_cache: bool = True, _fetcher=_fetch_coingecko_global) -> dict:
    """Returns {usdtd: float, btcd: float, ts: str}."""
    if use_cache:
        cached = _load_cache()
        if cached is not None:
            return cached
    data = _fetcher()
    dom = data["data"]["market_cap_percentage"]
    payload = {
        "usdtd": round(dom.get("usdt", 0.0), 3),
        "btcd": round(dom.get("btc", 0.0), 3),
        "ts": datetime.now(CR_OFFSET).isoformat(),
    }
    _save_cache(payload)
    return payload


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument("--quick", action="store_true", help="Single-line status")
    p.add_argument("--no-cache", action="store_true")
    args = p.parse_args()

    try:
        cur = fetch_dominance(use_cache=not args.no_cache)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR fetching dominance: {e}", file=sys.stderr)
        return 2

    # 7d change requires history; v1 sets to 0 (FLAT). Future iteration can use
    # historical cache snapshots to compute real 7d delta.
    change_7d_pct = 0.0
    trend = classify_trend(change_7d_pct)
    bias = btc_bias_from_usdtd(trend)

    payload = {
        "ts": cur["ts"],
        "usdtd": cur["usdtd"],
        "btcd": cur["btcd"],
        "change_24h_pct": None,
        "change_7d_pct": change_7d_pct,
        "trend_label": trend,
        "btc_inverse_bias": bias,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    elif args.quick:
        print(f"USDT.D={payload['usdtd']}%  BTC.D={payload['btcd']}%  "
              f"trend={trend}  bias={bias}")
    else:
        print(f"USDT.D: {payload['usdtd']}%")
        print(f"BTC.D:  {payload['btcd']}%")
        print(f"Trend (7d): {trend}")
        print(f"BTC inverse bias: {bias}")
        print(f"As of: {payload['ts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
