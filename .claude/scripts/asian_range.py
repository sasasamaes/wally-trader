#!/usr/bin/env python3
"""asian_range.py — Asian session range + grab/fakeout detector.

Asian session bars: UTC 23:00-08:00 (CR 17:00-02:00). At London open, price often sweeps
one side of the Asian range then closes back inside within a few bars — a classic ICT
liquidity grab. Entry = market on grab confirmation, SL = beyond sweep + small buffer,
TP = opposite range bound.

Usage:
    python3 asian_range.py --symbol EURUSD --check-grab
    python3 asian_range.py --file /tmp/bars5m.json --check-grab --json

Exit codes: 0=any outcome (informational), non-zero on error.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ASIAN_START_HOUR_UTC = 23
ASIAN_END_HOUR_UTC = 8
GRAB_WINDOW_BARS = 4
SL_BUFFER_PIPS = 0.0002  # 2 pips for EURUSD; override via --buffer


def _parse_ts(ts_iso: str) -> datetime:
    dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        # No tz info → assume UTC (project convention; data sources are TV MCP / Binance)
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _in_asian_session(ts: datetime) -> bool:
    h = ts.astimezone(timezone.utc).hour
    if ASIAN_START_HOUR_UTC > ASIAN_END_HOUR_UTC:
        return h >= ASIAN_START_HOUR_UTC or h < ASIAN_END_HOUR_UTC
    return ASIAN_START_HOUR_UTC <= h < ASIAN_END_HOUR_UTC


def asian_session_high_low(bars: list[dict], *, anchor: str) -> dict:
    """Compute high/low of the Asian session ending at the bar before `anchor`."""
    anchor_dt = _parse_ts(anchor)
    asian_bars = [b for b in bars if _in_asian_session(_parse_ts(b["ts"])) and _parse_ts(b["ts"]) < anchor_dt]
    if not asian_bars:
        return {"high": None, "low": None, "n_bars": 0}
    return {
        "high": max(b["high"] for b in asian_bars),
        "low": min(b["low"] for b in asian_bars),
        "n_bars": len(asian_bars),
    }


def detect_break_and_grab(
    london_bars: list[dict],
    *,
    asian_high: float,
    asian_low: float,
    window: int = GRAB_WINDOW_BARS,
) -> dict | None:
    """Find a break of asian_high or asian_low followed by a close back inside within window."""
    if not london_bars or asian_high is None or asian_low is None:
        return None
    break_idx = None
    side = None
    for i, b in enumerate(london_bars[:window]):
        if b["high"] > asian_high and b["close"] > asian_high:
            break_idx, side = i, "high"
            break
        if b["low"] < asian_low and b["close"] < asian_low:
            break_idx, side = i, "low"
            break
    if break_idx is None:
        return None
    # search next (window - break_idx) bars for close back inside
    for j in range(break_idx + 1, min(window, len(london_bars))):
        b = london_bars[j]
        if side == "high" and b["close"] < asian_high:
            return {
                "side": "high",
                "direction": "short",
                "break_bar_idx": break_idx,
                "grab_bar_idx": j,
                "sweep_extreme": max(x["high"] for x in london_bars[break_idx : j + 1]),
            }
        if side == "low" and b["close"] > asian_low:
            return {
                "side": "low",
                "direction": "long",
                "break_bar_idx": break_idx,
                "grab_bar_idx": j,
                "sweep_extreme": min(x["low"] for x in london_bars[break_idx : j + 1]),
            }
    return None


def evaluate_setup(bars: list[dict], *, anchor: str | None = None) -> dict:
    """Full pipeline: compute Asian H/L, look for grab in bars after anchor."""
    if anchor is None:
        # use the latest bar as anchor — caller is responsible for anchoring to London open
        anchor = bars[-1]["ts"]
    anchor_dt = _parse_ts(anchor)
    asian = asian_session_high_low(bars, anchor=anchor)
    london_bars = [b for b in bars if _parse_ts(b["ts"]) >= anchor_dt]
    grab = detect_break_and_grab(london_bars, asian_high=asian["high"], asian_low=asian["low"])
    if grab is None:
        return {"signal": None, "asian": asian, "reason": "no grab"}

    if grab["direction"] == "long":
        entry = london_bars[grab["grab_bar_idx"]]["close"]
        sl = grab["sweep_extreme"] - SL_BUFFER_PIPS
        tp = asian["high"]
    else:
        entry = london_bars[grab["grab_bar_idx"]]["close"]
        sl = grab["sweep_extreme"] + SL_BUFFER_PIPS
        tp = asian["low"]

    risk = abs(entry - sl)
    reward = abs(tp - entry)
    rr = round(reward / risk, 3) if risk > 0 else 0.0
    confidence = 50 + min(40, int(rr * 10))

    return {
        "signal": {
            "direction": grab["direction"],
            "entry": round(entry, 5),
            "sl": round(sl, 5),
            "tp": round(tp, 5),
            "rr": rr,
            "confidence": confidence,
            "asian_range": {"high": asian["high"], "low": asian["low"]},
            "grab": grab,
        }
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="EURUSD")
    p.add_argument("--file", help="bars JSON")
    p.add_argument("--anchor", help="ISO UTC timestamp of London open candle")
    p.add_argument("--check-grab", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--quick", action="store_true")
    args = p.parse_args()

    if not args.file:
        print("ERROR: --file required (live forex fetch out of scope here)", file=sys.stderr)
        return 3
    bars = json.loads(Path(args.file).read_text())
    out = evaluate_setup(bars, anchor=args.anchor)

    if args.json:
        print(json.dumps(out, indent=2, default=str))
    elif args.quick:
        sig = out.get("signal")
        if sig:
            print(f"ASIAN_GRAB {sig['direction'].upper()} conf={sig['confidence']} entry={sig['entry']} sl={sig['sl']} tp={sig['tp']} rr={sig['rr']}")
        else:
            print(f"NO_SIGNAL — {out.get('reason', 'unknown')}")
    else:
        print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
