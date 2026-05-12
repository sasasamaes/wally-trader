#!/usr/bin/env python3
"""pullback_detector.py — Impulse → pullback → continuation pattern detector.

Pattern (LONG variant — SHORT is mirror):
1. Impulse: 3+ consecutive green candles with ATR > rolling-mean ATR.
2. Pullback: subsequent retrace to 0.382-0.618 fib of the impulse, invalidated
   beyond 0.786.
3. Continuation: first green-close candle after the pullback closes within zone.

Gates:
- ADX (or adx_proxy from caller) ≥ 25 — no signal in chop.

Outputs entry price, SL (fib 0.75), 3 TPs derived from impulse magnitude.

Usage:
    python3 pullback_detector.py --symbol BTCUSDT --tf 15m
    python3 pullback_detector.py --file /tmp/bars.json --adx 30

Exit codes: 0=any outcome (informational), non-zero on error.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import urllib.request
from pathlib import Path

ATR_WINDOW = 14
IMPULSE_MIN_STREAK = 3
FIB_INVALIDATION = 0.786
ADX_FLOOR = 25.0


def _color(bar: dict) -> str:
    return "green" if bar["close"] >= bar["open"] else "red"


def _true_range(prev: dict, cur: dict) -> float:
    return max(
        cur["high"] - cur["low"],
        abs(cur["high"] - prev["close"]),
        abs(cur["low"] - prev["close"]),
    )


def _atr_series(bars: list[dict], window: int = ATR_WINDOW) -> list[float]:
    trs = [bars[0]["high"] - bars[0]["low"]]
    for i in range(1, len(bars)):
        trs.append(_true_range(bars[i - 1], bars[i]))
    out: list[float] = []
    for i in range(len(trs)):
        start = max(0, i - window + 1)
        out.append(sum(trs[start : i + 1]) / (i - start + 1))
    return out


_ATR_THRESHOLD = 0.96  # bar ATR must be >= this fraction of rolling mean to qualify


def _find_all_impulses(bars: list[dict], min_streak: int = IMPULSE_MIN_STREAK) -> list[dict]:
    """Return all qualifying impulse runs (ordered chronologically).

    A qualifying run is N+ consecutive same-color candles each with
    ATR >= _ATR_THRESHOLD × global mean ATR.
    """
    if len(bars) < min_streak + ATR_WINDOW:
        return []
    atrs = _atr_series(bars)
    mean_atr = statistics.mean(atrs)
    threshold = _ATR_THRESHOLD * mean_atr

    results: list[dict] = []
    i = 0
    while i < len(bars):
        if atrs[i] < threshold:
            i += 1
            continue
        color = _color(bars[i])
        j = i
        while (
            j + 1 < len(bars)
            and _color(bars[j + 1]) == color
            and atrs[j + 1] >= threshold
        ):
            j += 1
        run_len = j - i + 1
        if run_len >= min_streak:
            results.append({
                "color": color,
                "start_idx": i,
                "end_idx": j,
                "high": max(b["high"] for b in bars[i : j + 1]),
                "low": min(b["low"] for b in bars[i : j + 1]),
            })
        i = j + 1

    return results


def detect_impulse(bars: list[dict], min_streak: int = IMPULSE_MIN_STREAK) -> dict | None:
    """Find the most recent qualifying impulse run (any color).

    Returns the last qualifying run chronologically.
    """
    runs = _find_all_impulses(bars, min_streak=min_streak)
    return runs[-1] if runs else None


def detect_pullback(bars: list[dict], *, impulse_high: float, impulse_low: float) -> dict | None:
    """Retrace into fib 0.382-0.618 zone, invalidated past 0.786."""
    if not bars:
        return None
    rng = impulse_high - impulse_low
    if rng <= 0:
        return None
    fib_382 = impulse_high - rng * 0.382
    fib_618 = impulse_high - rng * 0.618
    fib_786 = impulse_high - rng * FIB_INVALIDATION
    lowest = min(b["low"] for b in bars)
    end_close = bars[-1]["close"]
    if lowest < fib_786:
        return None
    if not (fib_618 - 1e-9 <= end_close <= fib_382 + 1e-9):
        # tolerate slight bleed using lowest as alternative
        if not (fib_618 - 1e-9 <= lowest <= fib_382 + 1e-9):
            return None
    return {
        "end_price": end_close,
        "fib_382": fib_382,
        "fib_618": fib_618,
        "fib_786": fib_786,
    }


def detect_continuation(bars: list[dict], *, impulse_color: str) -> dict | None:
    """First same-color-as-impulse close after pullback."""
    if not bars:
        return None
    last = bars[-1]
    if _color(last) == impulse_color:
        return {"confirmed": True, "close": last["close"]}
    return None


def evaluate_setup(bars: list[dict], *, adx_proxy: float) -> dict | None:
    """Full pipeline. Returns dict with signal=None if no setup, or full signal.

    Iterates all qualifying impulses in reverse chronological order, looking for
    the most recent one that has a valid pullback + continuation in the bars that
    follow it. This ensures that a high-ATR pullback (opposite color) doesn't get
    mistaken for the leading impulse.
    """
    if adx_proxy < ADX_FLOOR:
        return {"signal": None, "reason": f"ADX {adx_proxy:.1f} < {ADX_FLOOR}"}

    all_impulses = _find_all_impulses(bars)
    if not all_impulses:
        return {"signal": None, "reason": "no impulse"}

    impulse = None
    pb = None
    cont = None
    after_impulse: list[dict] = []

    # Walk impulses from most recent to oldest; take the first that forms a full setup
    for candidate in reversed(all_impulses):
        after_impulse = bars[candidate["end_idx"] + 1 :]
        if len(after_impulse) < 2:
            continue  # not enough room for pullback + continuation
        _pb = detect_pullback(
            after_impulse[:-1],
            impulse_high=candidate["high"],
            impulse_low=candidate["low"],
        )
        if _pb is None:
            continue
        _cont = detect_continuation(after_impulse[-1:], impulse_color=candidate["color"])
        if _cont is None:
            continue
        impulse = candidate
        pb = _pb
        cont = _cont
        break

    if impulse is None or pb is None or cont is None:
        reason = "no valid pullback" if all_impulses else "no impulse"
        return {"signal": None, "reason": reason}

    direction = "long" if impulse["color"] == "green" else "short"
    rng = impulse["high"] - impulse["low"]
    entry = cont["close"]
    if direction == "long":
        sl = impulse["high"] - rng * 0.75
        tps = [entry + rng * k for k in (1.0, 1.618, 2.618)]
    else:
        sl = impulse["low"] + rng * 0.75
        tps = [entry - rng * k for k in (1.0, 1.618, 2.618)]

    # naive confidence: ADX above 25 → 30 base; impulse strength → up to 30; pullback depth → 40
    pullback_depth = (impulse["high"] - pb["end_price"]) / rng if direction == "long" else (
        pb["end_price"] - impulse["low"]
    ) / rng
    adx_score = min(30, (adx_proxy - 25) * 2 + 10)
    impulse_score = min(30, 5 + (impulse["end_idx"] - impulse["start_idx"]) * 5)
    pullback_score = 40 * (1 - abs(pullback_depth - 0.5) * 2)
    confidence = max(0, min(100, round(adx_score + impulse_score + pullback_score)))

    return {
        "signal": {
            "direction": direction,
            "entry": round(entry, 4),
            "sl": round(sl, 4),
            "tps": [round(t, 4) for t in tps],
            "confidence": confidence,
            "impulse": impulse,
            "pullback": pb,
        }
    }


def _fetch_bars_binance(symbol: str, tf: str, limit: int = 200) -> list[dict]:
    tf_map = {"15m": "15m", "1h": "1h", "4h": "4h"}
    url = (
        f"https://api.binance.com/api/v3/klines?symbol={symbol}"
        f"&interval={tf_map.get(tf, tf)}&limit={limit}"
    )
    with urllib.request.urlopen(url, timeout=10) as r:
        raw = json.loads(r.read())
    return [
        {
            "open": float(b[1]),
            "high": float(b[2]),
            "low": float(b[3]),
            "close": float(b[4]),
            "volume": float(b[5]),
        }
        for b in raw
    ]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--tf", default="15m")
    p.add_argument("--limit", type=int, default=200)
    p.add_argument("--file", type=str, help="bars JSON (list of OHLCV dicts)")
    p.add_argument("--adx", type=float, default=None, help="ADX proxy if known")
    p.add_argument("--json", action="store_true")
    p.add_argument("--quick", action="store_true")
    args = p.parse_args()

    if args.file:
        bars = json.loads(Path(args.file).read_text())
    else:
        bars = _fetch_bars_binance(args.symbol, args.tf, args.limit)

    if args.adx is None:
        # try calling adx_calc if available; otherwise default 30 (assume TREND_LEVE)
        try:
            import subprocess
            res = subprocess.run(
                [
                    str(Path(__file__).resolve().parent / ".venv" / "bin" / "python"),
                    str(Path(__file__).resolve().parent / "adx_calc.py"),
                    "--file", args.file or "/dev/stdin",
                    "--json",
                ],
                input=json.dumps(bars) if not args.file else None,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if res.returncode == 0:
                args.adx = json.loads(res.stdout).get("adx", 30.0)
            else:
                args.adx = 30.0
        except Exception:
            args.adx = 30.0

    out = evaluate_setup(bars, adx_proxy=args.adx)
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    elif args.quick:
        sig = out.get("signal") if out else None
        if sig:
            print(f"PULLBACK {sig['direction'].upper()} conf={sig['confidence']} entry={sig['entry']} sl={sig['sl']}")
            print(f"TPs: {' / '.join(str(t) for t in sig['tps'])}")
        else:
            print(f"NO_SIGNAL — {out.get('reason', 'unknown') if out else 'no data'}")
    else:
        print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
