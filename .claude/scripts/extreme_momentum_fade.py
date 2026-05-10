#!/usr/bin/env python3
"""extreme_momentum_fade.py — Detect the user's winning pattern.

Documented from 4 override-wins (DYDX 2x, TON, SUI = 100% WR, +$96.12 net):

The pattern signature:
  - 24h chg > +15% (extreme pump) OR < -8% (capitulation)
  - RSI 1H >= 75 (overbought) for SHORT — or RSI <= 25 (oversold) for LONG
  - Vol decay: last 1H vol < 0.5x of pump-peak hour vol (buyers exhausted)
  - Smart Money L/S != extreme contra (1.4-3.65 range OK — only block if >4.0)
  - Retail L/S extreme contra (>1.6 retail long for SHORT, <0.6 retail short for LONG)
  - Distance from peak <5% (entry near top of pump for SHORT, near bottom for LONG)

When this pattern fires, user's visual judgment has 100% WR historically.

The system was previously REJECTING these as "TREND_EXTREMO" — that classification
is now refined: not all extreme trends are non-tradeable, only those without
exhaustion signature.

Usage:
  python3 .claude/scripts/extreme_momentum_fade.py --symbol SUIUSDT
  python3 .claude/scripts/extreme_momentum_fade.py --symbol DYDXUSDT --quick

Exit codes:
  0 = pattern matches (extreme momentum fade tradeable)
  1 = no match
  2 = partial match (warn but allow)
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from typing import Any


def http_get(url: str, timeout: int = 5) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "wally/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def compute_rsi_1h(symbol: str, length: int = 14) -> float:
    """Compute RSI(14) on 1H closes."""
    bars = http_get(
        f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit={length+15}"
    )
    closes = [float(b[4]) for b in bars]
    if len(closes) < length + 1:
        return 50.0

    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))

    avg_gain = sum(gains[:length]) / length
    avg_loss = sum(losses[:length]) / length
    for i in range(length, len(gains)):
        avg_gain = (avg_gain * (length - 1) + gains[i]) / length
        avg_loss = (avg_loss * (length - 1) + losses[i]) / length

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def detect_pattern(symbol: str) -> dict[str, Any]:
    """Detect the extreme momentum fade pattern."""
    s = symbol.upper().replace(".P", "")

    try:
        # Spot 24h
        t24 = http_get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={s}")
        chg_24h = float(t24["priceChangePercent"])
        last = float(t24["lastPrice"])
        high_24h = float(t24["highPrice"])
        low_24h = float(t24["lowPrice"])

        # 1H bars for RSI + vol decay
        bars_1h = http_get(f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=24")
        vols_1h = [float(b[5]) for b in bars_1h]
        peak_vol = max(vols_1h[-12:]) if len(vols_1h) >= 12 else 0
        last_vol = vols_1h[-1]
        vol_decay = (last_vol / peak_vol) if peak_vol else 1.0

        rsi = compute_rsi_1h(s)

        # L/S ratios (Binance Futures, may be unavailable for some pairs)
        try:
            smart = float(http_get(
                f"https://fapi.binance.com/futures/data/topLongShortPositionRatio"
                f"?symbol={s}&period=1h&limit=1"
            )[0]["longShortRatio"])
        except Exception:
            smart = None
        try:
            retail = float(http_get(
                f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
                f"?symbol={s}&period=1h&limit=1"
            )[0]["longShortRatio"])
        except Exception:
            retail = None
    except Exception as e:
        return {"verdict": "ERROR", "reason": str(e), "symbol": symbol}

    # Determine candidate side
    side = None
    side_signal = ""
    if chg_24h >= 15.0 or rsi >= 75:
        side = "SHORT"
        side_signal = f"PUMP_FADE_SHORT (24h {chg_24h:+.2f}%, RSI {rsi:.1f})"
    elif chg_24h <= -8.0 or rsi <= 25:
        side = "LONG"
        side_signal = f"DUMP_BOUNCE_LONG (24h {chg_24h:+.2f}%, RSI {rsi:.1f})"
    else:
        return {
            "verdict": "NO_MATCH",
            "reason": f"Not extreme: 24h {chg_24h:+.2f}%, RSI {rsi:.1f}",
            "symbol": symbol,
            "side": None,
        }

    # Score the pattern signature
    signals: list[str] = []
    score = 0

    # Volume decay (most important — buyer/seller exhaustion)
    if vol_decay < 0.4:
        score += 30
        signals.append(f"VOL_DECAY_STRONG ({vol_decay:.2f}x peak)")
    elif vol_decay < 0.6:
        score += 18
        signals.append(f"VOL_DECAY_MOD ({vol_decay:.2f}x peak)")
    else:
        signals.append(f"vol_decay_weak ({vol_decay:.2f}x peak)")

    # RSI extreme
    if side == "SHORT" and rsi >= 80:
        score += 25
        signals.append(f"RSI_EXTREME_OB ({rsi:.1f})")
    elif side == "SHORT" and rsi >= 75:
        score += 15
        signals.append(f"RSI_OB ({rsi:.1f})")
    elif side == "LONG" and rsi <= 20:
        score += 25
        signals.append(f"RSI_EXTREME_OS ({rsi:.1f})")
    elif side == "LONG" and rsi <= 25:
        score += 15
        signals.append(f"RSI_OS ({rsi:.1f})")

    # Distance from extreme (entry quality)
    if side == "SHORT":
        dist_peak = (high_24h - last) / high_24h * 100
        if dist_peak < 3:
            score += 15
            signals.append(f"NEAR_PEAK ({dist_peak:.2f}% below)")
        elif dist_peak < 5:
            score += 8
            signals.append(f"close_to_peak ({dist_peak:.2f}% below)")
    else:
        dist_low = (last - low_24h) / low_24h * 100
        if dist_low < 3:
            score += 15
            signals.append(f"NEAR_LOW ({dist_low:.2f}% above)")
        elif dist_low < 5:
            score += 8
            signals.append(f"close_to_low ({dist_low:.2f}% above)")

    # Retail vs Smart divergence (contrarian sweet spot)
    if retail is not None and smart is not None:
        if side == "SHORT":
            if retail > 1.6 and smart < 1.5:
                score += 20
                signals.append(f"DIVERGENCE_RETAIL_TRAPPED (retail {retail:.2f} >> smart {smart:.2f})")
            elif retail > 1.4:
                score += 10
                signals.append(f"retail_long ({retail:.2f})")
        else:
            if retail < 0.6 and smart > 0.5:
                score += 20
                signals.append(f"DIVERGENCE_RETAIL_TRAPPED (retail {retail:.2f} << smart {smart:.2f})")
            elif retail < 0.8:
                score += 10
                signals.append(f"retail_short ({retail:.2f})")

    # Hard reject if smart money EXTREME against (>4.0 long for SHORT)
    if smart is not None:
        if side == "SHORT" and smart > 4.0:
            return {
                "verdict": "HARD_REJECT",
                "reason": f"Smart Money L/S {smart:.2f} > 4.0 — extreme bull, even pump-fade fails",
                "symbol": symbol,
                "side": side,
                "data": {"smart_ls": smart, "rsi": rsi, "chg_24h": chg_24h},
            }
        if side == "LONG" and smart < 0.25:
            return {
                "verdict": "HARD_REJECT",
                "reason": f"Smart Money L/S {smart:.2f} < 0.25 — extreme bear, even bounce fails",
                "symbol": symbol,
                "side": side,
                "data": {"smart_ls": smart, "rsi": rsi, "chg_24h": chg_24h},
            }

    # Verdict by total score
    if score >= 70:
        verdict = "STRONG_MATCH"
    elif score >= 50:
        verdict = "MATCH"
    elif score >= 30:
        verdict = "PARTIAL_MATCH"
    else:
        verdict = "NO_MATCH"

    return {
        "verdict": verdict,
        "side": side,
        "side_signal": side_signal,
        "score": score,
        "signals": signals,
        "data": {
            "price_now": last,
            "chg_24h": chg_24h,
            "high_24h": high_24h,
            "low_24h": low_24h,
            "rsi_1h": round(rsi, 1),
            "vol_decay": round(vol_decay, 3),
            "smart_ls": smart,
            "retail_ls": retail,
        },
        "symbol": symbol,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Extreme Momentum Fade pattern detector")
    p.add_argument("--symbol", required=True, help="Asset symbol (e.g. SUIUSDT)")
    p.add_argument("--quick", action="store_true", help="Stderr summary line")
    args = p.parse_args()

    result = detect_pattern(args.symbol)

    if args.quick:
        if "side" in result and result["side"]:
            line = (
                f"[ext-momentum] {result['symbol']}: {result['verdict']} "
                f"side={result['side']} score={result.get('score', 0)} "
                f"| {result.get('side_signal', '')}"
            )
        else:
            line = f"[ext-momentum] {result['symbol']}: {result['verdict']} — {result.get('reason', '')}"
        print(line, file=sys.stderr)

    print(json.dumps(result, indent=2))

    if result["verdict"] in ("STRONG_MATCH", "MATCH"):
        return 0
    if result["verdict"] == "PARTIAL_MATCH":
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
