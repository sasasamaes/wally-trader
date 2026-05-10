#!/usr/bin/env python3
"""backtest_punk_filters.py — Validate 3 new filters for /punk-hunt.

Lesson from TONUSDT.P SHORT (2026-05-09 BE close):
The setup scored 75/100 but failed because:
  1. Smart Money L/S 1.62 (longs cargados arriba) — opposite to thesis
  2. Entry within 2% of 24h low — bounce risk
  3. Liq magnet at $2.36 was -4.5% away — required big move to reach

This script backtests whether adding these as filters would have improved
outcomes on historical setups.

Methodology:
  1. For each asset in universe over LOOKBACK_DAYS:
     - For every 1h candle, simulate /punk-hunt scoring (LH+LL count, ATR%, vol)
     - If score >= MIN_SCORE → candidate setup
  2. For each candidate, compute the 3 new filter values at entry time
  3. Forward-simulate 6h to determine outcome:
     - TP1 hit (-2.0% from entry for SHORT) → +1R
     - SL hit (+2.0%) → -1R
     - Time-out → BE
  4. Aggregate WR + PnL by filter combination

Run:
  python3 .claude/scripts/backtest_punk_filters.py
  python3 .claude/scripts/backtest_punk_filters.py --asset TONUSDT --days 14

No API keys required — uses Binance public futures data.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any

# Default universe — top 10 liquid bitunix tradeables
DEFAULT_UNIVERSE = [
    "TONUSDT", "INJUSDT", "SUIUSDT", "AVAXUSDT", "LINKUSDT",
    "DOGEUSDT", "ADAUSDT", "TRXUSDT", "SEIUSDT", "TIAUSDT",
]

LOOKBACK_DAYS = 14
MIN_SCORE = 70  # Match /punk-hunt threshold
TP_PCT_SHORT = -2.0  # -2% from entry
SL_PCT_SHORT = +2.0  # +2% from entry
HOLD_BARS = 24       # 6h max hold (24 × 15m)


def http_get(url: str, timeout: int = 8) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "wally-bt/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_klines(symbol: str, interval: str, limit: int, end_ms: int | None = None) -> list[list]:
    """Fetch OHLCV from Binance Futures."""
    url = (
        f"https://fapi.binance.com/fapi/v1/klines"
        f"?symbol={symbol}&interval={interval}&limit={limit}"
    )
    if end_ms is not None:
        url += f"&endTime={end_ms}"
    return http_get(url)


def fetch_ls_pos(symbol: str, end_ms: int) -> list[dict]:
    """Fetch top traders position L/S ratio history."""
    url = (
        f"https://fapi.binance.com/futures/data/topLongShortPositionRatio"
        f"?symbol={symbol}&period=1h&limit=500&endTime={end_ms}"
    )
    return http_get(url)


def score_setup(bars_15m: list[list], idx: int) -> tuple[int, str]:
    """Compute punk-hunt-style score for SHORT continuation at bar idx.

    Score components:
      - LH+LL on last 5 bars (40 pts max)
      - ATR% in normal range (20 pts max)
      - Vol vs avg (20 pts max)
      - 24h continuation context (20 pts max)

    Returns (score, side). For now we only score SHORT continuation.
    """
    if idx < 30:
        return 0, "NONE"

    recent = bars_15m[max(0, idx - 5):idx + 1]
    closes = [float(b[4]) for b in recent]
    highs = [float(b[2]) for b in recent]
    lows = [float(b[3]) for b in recent]

    # Score LH+LL pattern (each lh and ll worth 4 pts, max 40 across 5 bars)
    lh = sum(1 for i in range(1, len(highs)) if highs[i] < highs[i - 1])
    ll = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i - 1])
    if lh + ll < 4:
        return 0, "NONE"
    score_pattern = min(40, (lh + ll) * 5)

    # ATR% (over last 14 bars)
    atr_window = bars_15m[max(0, idx - 14):idx + 1]
    trs = []
    for i in range(1, len(atr_window)):
        h, l = float(atr_window[i][2]), float(atr_window[i][3])
        prev_c = float(atr_window[i - 1][4])
        trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    atr = sum(trs) / len(trs) if trs else 0
    last_close = float(bars_15m[idx][4])
    atr_pct = (atr / last_close) * 100 if last_close else 0
    # Sweet spot 0.8% to 1.5%
    if 0.8 <= atr_pct <= 1.5:
        score_atr = 20
    elif 0.5 <= atr_pct < 0.8 or 1.5 < atr_pct <= 2.0:
        score_atr = 12
    else:
        score_atr = 5

    # Vol vs 12-bar avg
    vols = [float(b[5]) for b in bars_15m[max(0, idx - 12):idx + 1]]
    vol_avg = sum(vols) / len(vols) if vols else 1
    vol_now = vols[-1] if vols else 0
    vol_ratio = vol_now / vol_avg if vol_avg else 0
    if vol_ratio >= 1.2:
        score_vol = 20
    elif vol_ratio >= 0.8:
        score_vol = 12
    else:
        score_vol = 5

    # 24h continuation: did price drop -3%+ in last 24h (96 × 15m bars)?
    if idx >= 96:
        close_24h_ago = float(bars_15m[idx - 96][4])
        chg_24h = (last_close - close_24h_ago) / close_24h_ago * 100
        if chg_24h <= -5:
            score_24h = 20
        elif chg_24h <= -3:
            score_24h = 12
        else:
            score_24h = 5
    else:
        score_24h = 0

    total = score_pattern + score_atr + score_vol + score_24h
    return total, "SHORT"


def compute_filters(
    bars_15m: list[list],
    idx: int,
    ls_pos_history: list[dict],
    bar_time_ms: int,
) -> dict[str, Any]:
    """Compute filter values for a candidate setup.

    Returns:
      - smart_ls: top traders L/S at entry hour
      - dist_24h_low_pct: distance from 24h low (positive)
      - liq_magnet_distance_pct: estimated nearest liq cluster distance (negative for SHORT)
    """
    last_close = float(bars_15m[idx][4])

    # 24h range (96 × 15m bars)
    window = bars_15m[max(0, idx - 96):idx + 1]
    h24 = max(float(b[2]) for b in window)
    l24 = min(float(b[3]) for b in window)
    dist_low = (last_close - l24) / l24 * 100

    # Smart Money L/S — find closest historical entry
    ls_at_entry = None
    for entry in reversed(ls_pos_history):
        if int(entry["timestamp"]) <= bar_time_ms:
            ls_at_entry = float(entry["longShortRatio"])
            break

    # Liq magnet estimate (simplified):
    # Closest cluster below entry assuming longs anchored at recent local high
    # would be at high * (1 - 1/leverage) for popular leverage 20x = -4.5%
    recent_high = max(float(b[2]) for b in bars_15m[max(0, idx - 24):idx + 1])
    magnet_estimate = recent_high * (1 - 0.045)  # 20x leverage liq
    magnet_dist = (magnet_estimate - last_close) / last_close * 100

    return {
        "smart_ls": ls_at_entry,
        "dist_24h_low_pct": round(dist_low, 3),
        "magnet_distance_pct": round(magnet_dist, 3),
    }


def simulate_outcome(
    bars_15m: list[list],
    entry_idx: int,
    side: str = "SHORT",
) -> dict[str, Any]:
    """Forward-simulate the outcome over HOLD_BARS bars."""
    if entry_idx + HOLD_BARS >= len(bars_15m):
        return {"outcome": "INSUFFICIENT_DATA"}

    entry = float(bars_15m[entry_idx][4])
    tp_price = entry * (1 + TP_PCT_SHORT / 100)  # for SHORT this is below
    sl_price = entry * (1 + SL_PCT_SHORT / 100)  # above

    for j in range(1, HOLD_BARS + 1):
        bar = bars_15m[entry_idx + j]
        h, l = float(bar[2]), float(bar[3])
        if side == "SHORT":
            if l <= tp_price:
                return {"outcome": "TP", "exit_idx": entry_idx + j, "pnl_R": 1.0}
            if h >= sl_price:
                return {"outcome": "SL", "exit_idx": entry_idx + j, "pnl_R": -1.0}

    # Timeout — close at last close
    last = float(bars_15m[entry_idx + HOLD_BARS][4])
    pnl_R = (entry - last) / abs(entry - sl_price) if side == "SHORT" else 0
    return {"outcome": "TIMEOUT", "exit_idx": entry_idx + HOLD_BARS, "pnl_R": round(pnl_R, 3)}


def backtest_asset(symbol: str, days: int = LOOKBACK_DAYS) -> dict[str, Any]:
    """Run backtest for a single asset."""
    bars_needed = days * 96 + 100  # buffer for warm-up
    # Binance limit is 1500 per request; chunk if needed
    end_ms = int(time.time() * 1000)
    all_bars: list[list] = []
    while len(all_bars) < bars_needed:
        chunk = fetch_klines(symbol, "15m", min(1500, bars_needed - len(all_bars)), end_ms)
        if not chunk:
            break
        all_bars = chunk + all_bars
        end_ms = int(chunk[0][0]) - 1
        if len(chunk) < 1500:
            break
        time.sleep(0.1)
    bars_15m = sorted(all_bars, key=lambda x: x[0])

    if len(bars_15m) < 200:
        return {"symbol": symbol, "error": "insufficient_bars", "got": len(bars_15m)}

    # Fetch L/S history (1h period, max 500 hours = ~20 days)
    end_ms = int(bars_15m[-1][0])
    try:
        ls_pos = fetch_ls_pos(symbol, end_ms)
    except Exception as e:
        ls_pos = []

    # Find candidate setups
    candidates = []
    # Skip first 100 bars for warm-up; skip last HOLD_BARS for outcome computation
    for idx in range(100, len(bars_15m) - HOLD_BARS):
        score, side = score_setup(bars_15m, idx)
        if score >= MIN_SCORE and side == "SHORT":
            bar_time = int(bars_15m[idx][0])
            filters = compute_filters(bars_15m, idx, ls_pos, bar_time)
            outcome = simulate_outcome(bars_15m, idx, side)
            candidates.append({
                "idx": idx,
                "time": bar_time,
                "entry": float(bars_15m[idx][4]),
                "score": score,
                "side": side,
                **filters,
                **outcome,
            })

    return {"symbol": symbol, "candidates": candidates, "total_bars": len(bars_15m)}


def aggregate_results(results: list[dict]) -> dict[str, Any]:
    """Apply filter combinations and aggregate WR/PnL."""
    all_setups = []
    for r in results:
        if "candidates" not in r:
            continue
        for c in r["candidates"]:
            c["asset"] = r["symbol"]
            if c.get("outcome") in ("TP", "SL", "TIMEOUT"):
                all_setups.append(c)

    if not all_setups:
        return {"error": "no_setups_found"}

    def _stats(setups: list[dict]) -> dict[str, Any]:
        n = len(setups)
        if n == 0:
            return {"n": 0, "wr": 0.0, "avg_R": 0.0, "total_R": 0.0}
        wins = sum(1 for s in setups if s["pnl_R"] > 0)
        total_R = sum(s["pnl_R"] for s in setups)
        return {
            "n": n,
            "wr": round(wins / n * 100, 1),
            "avg_R": round(total_R / n, 3),
            "total_R": round(total_R, 2),
            "tp": sum(1 for s in setups if s["outcome"] == "TP"),
            "sl": sum(1 for s in setups if s["outcome"] == "SL"),
            "timeout": sum(1 for s in setups if s["outcome"] == "TIMEOUT"),
        }

    # Filter variants
    filters = {
        "ALL_NO_FILTER": all_setups,
        "F1_smart_ls_veto_1.4": [s for s in all_setups if s.get("smart_ls") is None or s["smart_ls"] <= 1.4],
        "F2_dist_24h_low>2pct": [s for s in all_setups if s["dist_24h_low_pct"] > 2.0],
        "F3_magnet_within_5pct": [s for s in all_setups if abs(s["magnet_distance_pct"]) <= 5.0],
        "F1+F2": [s for s in all_setups if (s.get("smart_ls") is None or s["smart_ls"] <= 1.4) and s["dist_24h_low_pct"] > 2.0],
        "F1+F3": [s for s in all_setups if (s.get("smart_ls") is None or s["smart_ls"] <= 1.4) and abs(s["magnet_distance_pct"]) <= 5.0],
        "F2+F3": [s for s in all_setups if s["dist_24h_low_pct"] > 2.0 and abs(s["magnet_distance_pct"]) <= 5.0],
        "F1+F2+F3 ALL": [
            s for s in all_setups
            if (s.get("smart_ls") is None or s["smart_ls"] <= 1.4)
            and s["dist_24h_low_pct"] > 2.0
            and abs(s["magnet_distance_pct"]) <= 5.0
        ],
    }

    return {
        "total_setups_candidates": len(all_setups),
        "by_filter": {name: _stats(setups) for name, setups in filters.items()},
        "raw_setups_sample": all_setups[:5],
    }


def format_report(result: dict[str, Any], by_asset: list[dict]) -> str:
    """Pretty-print backtest results."""
    lines = ["=== PUNK-HUNT FILTER BACKTEST ===\n"]
    lines.append(f"Universe: {len(by_asset)} assets")
    lines.append(f"Lookback: {LOOKBACK_DAYS} days (15m bars)")
    lines.append(f"Min score: {MIN_SCORE}, Side: SHORT continuation")
    lines.append(f"TP: {TP_PCT_SHORT}%, SL: +{SL_PCT_SHORT}%, Hold max: 6h\n")

    lines.append("--- Per-asset summary ---")
    for r in by_asset:
        if "error" in r:
            lines.append(f"  {r['symbol']}: ERROR ({r['error']})")
        else:
            n = len(r.get("candidates", []))
            lines.append(f"  {r['symbol']}: {n} setups identified")

    if "error" in result:
        lines.append(f"\nERROR: {result['error']}")
        return "\n".join(lines)

    lines.append(f"\nTotal setups across universe: {result['total_setups_candidates']}\n")
    lines.append("--- Filter performance ---")
    lines.append(f"{'Filter':<28} {'N':>5} {'WR%':>6} {'Avg R':>8} {'Total R':>9} {'TP/SL/TO':>11}")
    lines.append("-" * 75)

    for name, stats in result["by_filter"].items():
        if stats["n"] == 0:
            lines.append(f"{name:<28} {'0':>5}  (no setups passed)")
            continue
        tp_sl_to = f"{stats['tp']}/{stats['sl']}/{stats['timeout']}"
        lines.append(
            f"{name:<28} {stats['n']:>5} {stats['wr']:>5.1f}% {stats['avg_R']:>+7.3f} "
            f"{stats['total_R']:>+8.2f} {tp_sl_to:>11}"
        )

    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="Backtest punk-hunt filter improvements")
    p.add_argument("--asset", help="Single asset (default: full universe)")
    p.add_argument("--days", type=int, default=LOOKBACK_DAYS, help=f"Lookback days (default {LOOKBACK_DAYS})")
    p.add_argument("--min-score", type=int, default=MIN_SCORE, help=f"Min punk-hunt score (default {MIN_SCORE})")
    p.add_argument("--json", action="store_true", help="Output raw JSON")
    args = p.parse_args()

    universe = [args.asset] if args.asset else DEFAULT_UNIVERSE

    by_asset = []
    for sym in universe:
        try:
            print(f"[bt] Backtesting {sym}...", file=sys.stderr)
            r = backtest_asset(sym, days=args.days)
            by_asset.append(r)
            time.sleep(0.5)  # Rate limit guard
        except Exception as e:
            by_asset.append({"symbol": sym, "error": str(e)})

    aggregated = aggregate_results(by_asset)

    if args.json:
        print(json.dumps({"by_asset": by_asset, "aggregated": aggregated}, indent=2, default=str))
    else:
        print(format_report(aggregated, by_asset))

    return 0


if __name__ == "__main__":
    sys.exit(main())
