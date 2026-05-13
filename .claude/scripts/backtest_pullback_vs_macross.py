#!/usr/bin/env python3
"""backtest_pullback_vs_macross.py — Pullback Detector vs MA Crossover in TREND_LEVE.

Bundle 3 deferred question: should /pullback wire into regime_mapping.json
TREND_LEVE slot (currently held by MA Crossover EMA 9/21)?

This script fetches 60d of 15m bars per asset, filters bars where ADX ∈ [25, 30]
(TREND_LEVE), runs both strategies bar-by-bar, simulates SL/TP1 outcomes over
a 96-bar (24h) forward window, and produces a per-asset + aggregate table.

Usage:
    .claude/scripts/.venv/bin/python .claude/scripts/backtest_pullback_vs_macross.py
    .claude/scripts/.venv/bin/python .claude/scripts/backtest_pullback_vs_macross.py \\
        --assets BTCUSDT,ETHUSDT,SOLUSDT,AVAXUSDT,INJUSDT \\
        --days 60 \\
        --output docs/backtest_findings_2026-05-12_pullback_vs_macross_trend_leve.md \\
        [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — import siblings without requiring pip install
# ---------------------------------------------------------------------------
_SCRIPTS = Path(__file__).resolve().parent
_SHARED = _SCRIPTS.parent.parent / "shared" / "wally_core" / "src"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from backtest_split import temporal_split, degradation_flag  # noqa: E402
from pullback_detector import evaluate_setup as pullback_evaluate  # noqa: E402
from macross import detect_cross  # noqa: E402

try:
    from wally_core.regime import compute_adx as _wc_adx
    _HAS_WALLY_CORE = True
except ImportError:
    _HAS_WALLY_CORE = False
    _wc_adx = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "INJUSDT"]
DEFAULT_DAYS = 60
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent.parent.parent
    / "docs"
    / "backtest_findings_2026-05-12_pullback_vs_macross_trend_leve.md"
)

# TREND_LEVE = ADX in [25, 30] per adx_calc.py:51
ADX_TREND_LEVE_LOW = 25.0
ADX_TREND_LEVE_HIGH = 30.0

# How many forward bars to simulate each trade (24h at 15m = 96 bars)
HOLD_BARS = 96

# Window for ADX computation per bar
ADX_WINDOW = 30   # bars lookback for rolling ADX computation

# Minimum bars before we start evaluating (warm-up)
MIN_WARMUP = 50

# ATR window for MA Crossover SL/TP derivation
ATR_WINDOW = 14
ATR_SL_MULT = 1.5
ATR_TP1_MULT = 2.5


# ---------------------------------------------------------------------------
# Public helpers (importable by tests)
# ---------------------------------------------------------------------------

def is_trend_leve(adx_value: float) -> bool:
    """Return True if ADX is in the TREND_LEVE band [25, 30] inclusive."""
    return ADX_TREND_LEVE_LOW <= adx_value <= ADX_TREND_LEVE_HIGH


def simulate_trade_outcome(
    future_bars: list[dict],
    direction: str,   # "long" or "short"
    entry: float,
    sl: float,
    tp1: float,
) -> dict:
    """Simulate a trade over future_bars.

    Iterates bar-by-bar; on each bar checks whether high/low crosses SL or TP1.
    The bar is assumed to open near 'entry' (already entered at last close).

    For a LONG:
      - SL hit if bar.low <= sl
      - TP1 hit if bar.high >= tp1

    For a SHORT (mirror):
      - SL hit if bar.high >= sl
      - TP1 hit if bar.low <= tp1

    Whichever is hit first within the bar ordering wins. If both SL and TP1
    are triggered on the same bar we conservatively call it a loss (SL first).

    Returns dict: {result: "win"|"loss"|"flat", r: float, bars_held: int}
    """
    sl_dist = abs(entry - sl)
    tp1_dist = abs(tp1 - entry)
    if sl_dist == 0:
        # Degenerate case — no risk defined
        return {"result": "flat", "r": 0.0, "bars_held": 0}

    r_per_unit = tp1_dist / sl_dist  # R multiple for a TP1 win

    window = future_bars[:HOLD_BARS]
    for idx, bar in enumerate(window):
        if direction == "long":
            sl_hit = bar["low"] <= sl
            tp_hit = bar["high"] >= tp1
        else:
            sl_hit = bar["high"] >= sl
            tp_hit = bar["low"] <= tp1

        if sl_hit and tp_hit:
            # Both on same bar → conservative: SL first
            return {"result": "loss", "r": -1.0, "bars_held": idx + 1}
        if sl_hit:
            return {"result": "loss", "r": -1.0, "bars_held": idx + 1}
        if tp_hit:
            return {"result": "win", "r": r_per_unit, "bars_held": idx + 1}

    return {"result": "flat", "r": 0.0, "bars_held": len(window)}


def aggregate_metrics(r_values: list[float]) -> dict:
    """Aggregate a list of per-trade R values into summary metrics.

    Returns:
      n, wins, losses, flats, wr_pct, pf, total_r, avg_r
    """
    n = len(r_values)
    if n == 0:
        return {
            "n": 0, "wins": 0, "losses": 0, "flats": 0,
            "wr_pct": 0.0, "pf": 0.0, "total_r": 0.0, "avg_r": 0.0,
        }

    wins = sum(1 for r in r_values if r > 0)
    losses = sum(1 for r in r_values if r < 0)
    flats = sum(1 for r in r_values if r == 0)

    sum_wins = sum(r for r in r_values if r > 0)
    sum_losses = abs(sum(r for r in r_values if r < 0))

    wr_pct = (wins / n) * 100 if n > 0 else 0.0
    pf = (sum_wins / sum_losses) if sum_losses > 0 else 0.0
    total_r = sum(r_values)
    avg_r = total_r / n if n > 0 else 0.0

    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "flats": flats,
        "wr_pct": round(wr_pct, 2),
        "pf": round(pf, 3),
        "total_r": round(total_r, 3),
        "avg_r": round(avg_r, 3),
    }


# ---------------------------------------------------------------------------
# ATR computation (local — avoids importing full toolchain)
# ---------------------------------------------------------------------------

def _true_range(prev: dict, cur: dict) -> float:
    return max(
        cur["high"] - cur["low"],
        abs(cur["high"] - prev["close"]),
        abs(cur["low"] - prev["close"]),
    )


def _atr(bars: list[dict], window: int = ATR_WINDOW) -> float:
    """Compute ATR over the last `window` bars of `bars`."""
    if len(bars) < window + 1:
        # Fallback: simple range average
        ranges = [b["high"] - b["low"] for b in bars[-window:]]
        return sum(ranges) / len(ranges) if ranges else 0.0
    trs = [bars[0]["high"] - bars[0]["low"]]
    for i in range(1, len(bars)):
        trs.append(_true_range(bars[i - 1], bars[i]))
    # RMA (Wilder) over last window
    recent = trs[-window:]
    return sum(recent) / window


# ---------------------------------------------------------------------------
# ADX computation — delegates to wally_core, falls back to local impl
# ---------------------------------------------------------------------------

def _compute_adx_local(bars: list[dict], length: int = 14) -> float | None:
    """Compute ADX(length) on the supplied bars.

    Prefers wally_core.regime.compute_adx (validated implementation).
    Falls back to a local Wilder-smoothed computation if wally_core is
    not available.

    Returns the final ADX value (0–100), or None if data is insufficient.
    """
    min_bars = length * 2 + 2
    if len(bars) < min_bars:
        return None

    # Prefer wally_core — it's the validated canonical implementation
    if _HAS_WALLY_CORE and _wc_adx is not None:
        try:
            res = _wc_adx(bars, length=length)
            return round(res["adx"], 2)
        except Exception:
            pass  # fall through to local impl

    # Local fallback using Wilder smoothing
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    closes = [b["close"] for b in bars]

    trs, pdms, ndms = [], [], []
    for i in range(1, len(bars)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        pdm = up_move if up_move > down_move and up_move > 0 else 0.0
        ndm = down_move if down_move > up_move and down_move > 0 else 0.0
        trs.append(tr)
        pdms.append(pdm)
        ndms.append(ndm)

    def _wilder(values: list[float], n: int) -> list[float]:
        if len(values) < n:
            return []
        s = [sum(values[:n])]
        for v in values[n:]:
            s.append(s[-1] - s[-1] / n + v)
        return s

    atr_s = _wilder(trs, length)
    pdm_s = _wilder(pdms, length)
    ndm_s = _wilder(ndms, length)

    if not atr_s:
        return None

    dx_list = []
    for atr_v, pdm_v, ndm_v in zip(atr_s, pdm_s, ndm_s):
        if atr_v == 0:
            dx_list.append(0.0)
            continue
        pdi = 100.0 * pdm_v / atr_v
        ndi = 100.0 * ndm_v / atr_v
        denom = pdi + ndi
        dx_list.append(100.0 * abs(pdi - ndi) / denom if denom != 0 else 0.0)

    if len(dx_list) < length:
        return None

    adx_s = _wilder(dx_list, length)
    return round(adx_s[-1], 2) if adx_s else None


# ---------------------------------------------------------------------------
# Data fetch (reuse fetch_paginated pattern from backtest_regime_matrix.py)
# ---------------------------------------------------------------------------

def _normalize_bar(raw: dict) -> dict:
    """Normalize h/l/c/o aliased keys to standard long-form."""
    return {
        "open": float(raw.get("open") or raw.get("o") or 0),
        "high": float(raw.get("high") or raw.get("h")),
        "low": float(raw.get("low") or raw.get("l")),
        "close": float(raw.get("close") or raw.get("c")),
        "volume": float(raw.get("volume") or raw.get("v") or 0),
        "t": int(raw.get("t") or raw.get("time") or 0),
    }


def fetch_bars(symbol: str, days: int, interval: str = "15m") -> list[dict]:
    """Fetch `days` worth of bars via Binance Futures public klines.

    Uses the same paginated approach as backtest_regime_matrix.fetch_paginated.
    Falls back to spot API if futures returns empty (for INJUSDT etc.).
    """
    bars_per_day = {"15m": 96, "1h": 24, "4h": 6}.get(interval, 96)
    target = bars_per_day * days
    seen: dict[int, dict] = {}

    base_futures = "https://fapi.binance.com/fapi/v1/klines"
    base_spot = "https://api.binance.com/api/v3/klines"

    def _fetch_page(base: str, end_ts: int | None) -> list:
        url = f"{base}?symbol={symbol}&interval={interval}&limit=1500"
        if end_ts is not None:
            url += f"&endTime={end_ts}"
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            print(f"  WARN {symbol} ({base}): {exc}", file=sys.stderr)
            return []

    def _pages_to_bars(page: list) -> dict[int, dict]:
        out = {}
        for b in page:
            t = int(b[0])
            out[t] = {
                "t": t,
                "open": float(b[1]),
                "high": float(b[2]),
                "low": float(b[3]),
                "close": float(b[4]),
                "volume": float(b[5]),
            }
        return out

    # Try futures first
    end_ts = None
    for base in (base_futures, base_spot):
        seen = {}
        end_ts = None
        for _ in range(40):  # max 40 pages × 1500 bars = 60k bars (way more than needed)
            page = _fetch_page(base, end_ts)
            if not page:
                break
            seen.update(_pages_to_bars(page))
            if len(seen) >= target:
                break
            oldest = min(int(b[0]) for b in page)
            end_ts = oldest - 1
            time.sleep(0.05)
            if len(page) < 1500:
                break  # reached history start

        if seen:
            break  # futures worked, no need for spot fallback

    bars = sorted(seen.values(), key=lambda b: b["t"])
    return bars[-target:] if len(bars) > target else bars


# ---------------------------------------------------------------------------
# Per-bar strategy evaluation
# ---------------------------------------------------------------------------

def _eval_pullback(bars: list[dict], adx_value: float) -> dict | None:
    """Run pullback detector and return signal dict or None."""
    result = pullback_evaluate(bars, adx_proxy=adx_value)
    if result is None:
        return None
    sig = result.get("signal")
    if sig is None:
        return None
    return sig  # has direction, entry, sl, tps


def _eval_macross(bars: list[dict]) -> dict | None:
    """Run MA Crossover and return signal dict with derived SL/TP1 or None."""
    closes = [b["close"] for b in bars]
    result = detect_cross(closes, fast=9, slow=21)
    sig = result.get("signal", "NEUTRAL")
    if sig not in ("LONG", "SHORT"):
        return None

    direction = "long" if sig == "LONG" else "short"
    entry = closes[-1]
    atr_val = _atr(bars, ATR_WINDOW)
    if atr_val == 0:
        return None

    if direction == "long":
        sl = entry - atr_val * ATR_SL_MULT
        tp1 = entry + atr_val * ATR_TP1_MULT
    else:
        sl = entry + atr_val * ATR_SL_MULT
        tp1 = entry - atr_val * ATR_TP1_MULT

    return {
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
    }


# ---------------------------------------------------------------------------
# Main backtest loop
# ---------------------------------------------------------------------------

def run_backtest_asset(
    bars: list[dict],
    asset: str,
) -> dict:
    """Run both strategies bar-by-bar on `bars`.

    Returns per-strategy lists of R outcomes:
      {
        "pullback": {"r_values": [...], "n_adx_bars": int},
        "macross":  {"r_values": [...], "n_adx_bars": int},
      }
    """
    pullback_r: list[float] = []
    macross_r: list[float] = []
    n_adx_bars = 0   # bars that passed TREND_LEVE ADX filter

    for i in range(MIN_WARMUP, len(bars) - HOLD_BARS):
        window = bars[max(0, i - ADX_WINDOW): i + 1]
        adx_val = _compute_adx_local(window, length=14)
        if adx_val is None:
            continue
        if not is_trend_leve(adx_val):
            continue
        n_adx_bars += 1

        future = bars[i + 1: i + 1 + HOLD_BARS]
        if len(future) < 5:
            continue  # need enough forward bars

        eval_window = bars[max(0, i - MIN_WARMUP): i + 1]

        # --- Pullback ---
        pb_sig = _eval_pullback(eval_window, adx_value=adx_val)
        if pb_sig is not None:
            entry = pb_sig["entry"]
            sl = pb_sig["sl"]
            tps = pb_sig.get("tps") or []
            tp1 = tps[0] if tps else None
            if tp1 is not None:
                oc = simulate_trade_outcome(
                    future_bars=future,
                    direction=pb_sig["direction"],
                    entry=entry,
                    sl=sl,
                    tp1=tp1,
                )
                pullback_r.append(oc["r"])

        # --- MA Crossover ---
        mc_sig = _eval_macross(eval_window)
        if mc_sig is not None:
            oc = simulate_trade_outcome(
                future_bars=future,
                direction=mc_sig["direction"],
                entry=mc_sig["entry"],
                sl=mc_sig["sl"],
                tp1=mc_sig["tp1"],
            )
            macross_r.append(oc["r"])

    return {
        "pullback": {"r_values": pullback_r, "n_adx_bars": n_adx_bars},
        "macross": {"r_values": macross_r, "n_adx_bars": n_adx_bars},
    }


def run_oos_split(bars: list[dict], asset: str) -> dict:
    """Run OOS 70/30 split and aggregate per strategy.

    Returns structured result with train/test metrics, degradation flag,
    and raw R lists for cross-asset pooling.
    """
    try:
        train_bars, test_bars = temporal_split(bars, train_ratio=0.7)
    except ValueError as exc:
        return {"error": str(exc)}

    train_res = run_backtest_asset(train_bars, asset)
    test_res = run_backtest_asset(test_bars, asset)

    output = {}
    for strat in ("pullback", "macross"):
        train_r = train_res[strat]["r_values"]
        test_r = test_res[strat]["r_values"]
        all_r = train_r + test_r
        train_m = aggregate_metrics(train_r)
        test_m = aggregate_metrics(test_r)

        # Build metric dicts for degradation_flag (uses wr, pf, ret, dd, n)
        def _to_degradation_dict(m: dict) -> dict:
            return {
                "n": m["n"],
                "wr": m["wr_pct"],
                "pf": m["pf"],
                "ret": m["total_r"],  # total R as proxy for return %
                "dd": 0,  # no per-trade DD tracking here
            }

        status, reasons = degradation_flag(
            _to_degradation_dict(train_m),
            _to_degradation_dict(test_m),
        )

        output[strat] = {
            "train": train_m,
            "test": test_m,
            "all_r": all_r,          # raw R values for cross-asset pooling
            "oos_status": status,
            "oos_reasons": reasons,
            "n_adx_bars_train": train_res[strat]["n_adx_bars"],
            "n_adx_bars_test": test_res[strat]["n_adx_bars"],
        }

    return output


# ---------------------------------------------------------------------------
# Aggregate across assets
# ---------------------------------------------------------------------------

def aggregate_across_assets(per_asset: dict) -> dict:
    """Pool raw R values across assets per strategy.

    Uses the `all_r` list stored in each asset's result dict (train + test combined)
    to accurately pool wins/losses/flats without reconstruction artifacts.
    """
    all_r: dict[str, list[float]] = {"pullback": [], "macross": []}
    for asset_data in per_asset.values():
        if "error" in asset_data:
            continue
        for strat in ("pullback", "macross"):
            strat_data = asset_data.get(strat, {})
            r_list = strat_data.get("all_r", [])
            all_r[strat].extend(r_list)

    return {
        strat: aggregate_metrics(all_r[strat]) for strat in ("pullback", "macross")
    }


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------

def compute_verdict(agg: dict) -> tuple[str, str]:
    """Return (verdict_key, justification) based on aggregate comparison."""
    pb = agg.get("pullback", {})
    mc = agg.get("macross", {})

    pb_wr = pb.get("wr_pct", 0)
    mc_wr = mc.get("wr_pct", 0)
    pb_pf = pb.get("pf", 0)
    mc_pf = mc.get("pf", 0)
    pb_n = pb.get("n", 0)
    mc_n = mc.get("n", 0)

    MIN_TRADES = 30  # per spec honesty contract

    if pb_n < MIN_TRADES or mc_n < MIN_TRADES:
        verdict = "SAMPLE_TOO_SMALL"
        just = (
            f"Insufficient trades for a statistically reliable comparison. "
            f"Pullback: {pb_n} trades, MA Crossover: {mc_n} trades. "
            f"Need ≥{MIN_TRADES} trades per cell before deciding. "
            f"Recommend collecting more TREND_LEVE data (wider asset universe or longer window) "
            f"before wiring /pullback into regime_mapping.json."
        )
        return verdict, just

    wr_diff = pb_wr - mc_wr
    pf_diff = pb_pf - mc_pf

    if pb_pf < 1.0 and mc_pf < 1.0:
        verdict = "BOTH_NO_EDGE"
        just = (
            f"Both strategies show PF < 1.0 in TREND_LEVE conditions "
            f"(Pullback PF={pb_pf:.2f}, MA Crossover PF={mc_pf:.2f}). "
            f"Neither has a demonstrable edge. Keep MA Crossover as default "
            f"(lower complexity) but treat TREND_LEVE as a marginal regime."
        )
        return verdict, just

    if wr_diff >= 10 and pf_diff >= 0.4:
        verdict = "WIRE-IN-RECOMMENDED"
        just = (
            f"Pullback Detector clearly outperforms MA Crossover in TREND_LEVE: "
            f"WR {pb_wr:.1f}% vs {mc_wr:.1f}% (+{wr_diff:.1f}pp), "
            f"PF {pb_pf:.2f} vs {mc_pf:.2f} (+{pf_diff:.2f}). "
            f"Recommend wiring /pullback into regime_mapping.json TREND_LEVE slot. "
            f"Run for 2 more weeks of live signals before full commit."
        )
        return verdict, just

    if wr_diff <= -10 and pf_diff <= -0.4:
        verdict = "KEEP-MACROSS"
        just = (
            f"MA Crossover outperforms Pullback Detector in TREND_LEVE: "
            f"WR {mc_wr:.1f}% vs {pb_wr:.1f}% (+{-wr_diff:.1f}pp), "
            f"PF {mc_pf:.2f} vs {pb_pf:.2f} (+{-pf_diff:.2f}). "
            f"Keep MA Crossover as the TREND_LEVE strategy."
        )
        return verdict, just

    verdict = "NEUTRAL"
    just = (
        f"Strategies are comparable within margin (WR diff={wr_diff:+.1f}pp, PF diff={pf_diff:+.2f}). "
        f"Per honesty contract: WR within 5pp or PF within 0.2 → NEUTRAL/KEEP-MACROSS. "
        f"Retaining MA Crossover (lower complexity, existing wire-in). "
        f"Revisit if Pullback edge improves with more data."
    )
    return verdict, just


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _fmt_oos(status: str) -> str:
    return {"PASS": "✅ PASS", "WARN": "⚠️ WARN", "FAIL": "❌ FAIL"}.get(status, status)


def build_markdown_report(
    per_asset_results: dict,
    agg: dict,
    verdict: str,
    justification: str,
    assets: list[str],
    days: int,
) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Per-asset table
    per_asset_rows = []
    for asset in assets:
        data = per_asset_results.get(asset, {})
        if "error" in data:
            for strat in ("pullback", "macross"):
                per_asset_rows.append(
                    f"| {asset} | {strat} | — | — | — | — | {data['error']} |"
                )
            continue
        for strat in ("pullback", "macross"):
            sd = data.get(strat, {})
            # Use the pre-computed all_r aggregate (train + test combined)
            all_r_list = sd.get("all_r", [])
            full_m = aggregate_metrics(all_r_list)
            oos = _fmt_oos(sd.get("oos_status", "—"))
            per_asset_rows.append(
                f"| {asset} | {strat} | {full_m['n']} | {full_m['wr_pct']:.1f}% "
                f"| {full_m['pf']:.2f} | {full_m['total_r']:+.2f}R | {oos} |"
            )

    per_asset_table = "\n".join(per_asset_rows)

    # Aggregate table
    pb_agg = agg.get("pullback", {})
    mc_agg = agg.get("macross", {})

    # OOS status aggregated (worst across assets)
    def _worst_oos(strat: str) -> str:
        statuses = []
        for asset in assets:
            sd = per_asset_results.get(asset, {}).get(strat, {})
            statuses.append(sd.get("oos_status", "WARN"))
        if "FAIL" in statuses:
            return _fmt_oos("FAIL")
        if "WARN" in statuses:
            return _fmt_oos("WARN")
        return _fmt_oos("PASS")

    agg_table = (
        "| Strategy | N | WR % | PF | Total R | Avg R | OOS verdict |\n"
        "|---|---|---|---|---|---|---|\n"
        f"| Pullback Detector | {pb_agg.get('n', 0)} | {pb_agg.get('wr_pct', 0):.1f}% "
        f"| {pb_agg.get('pf', 0):.2f} | {pb_agg.get('total_r', 0):+.2f}R "
        f"| {pb_agg.get('avg_r', 0):+.3f}R | {_worst_oos('pullback')} |\n"
        f"| MA Crossover EMA9/21 | {mc_agg.get('n', 0)} | {mc_agg.get('wr_pct', 0):.1f}% "
        f"| {mc_agg.get('pf', 0):.2f} | {mc_agg.get('total_r', 0):+.2f}R "
        f"| {mc_agg.get('avg_r', 0):+.3f}R | {_worst_oos('macross')} |"
    )

    verdict_icon = {
        "WIRE-IN-RECOMMENDED": "✅",
        "KEEP-MACROSS": "🔒",
        "NEUTRAL": "↔️",
        "SAMPLE_TOO_SMALL": "⚠️",
        "BOTH_NO_EDGE": "❌",
    }.get(verdict, "ℹ️")

    return f"""# Backtest — Pullback Detector vs MA Crossover (TREND_LEVE)

**Date:** {today}
**Trigger:** Bundle 3 deferred wire-in of /pullback → regime_mapping.json. This compares
it against the existing TREND_LEVE strategy (MA Crossover EMA 9/21).

## Methodology

- **Universe:** {", ".join(assets)}
- **Period:** last {days} days, 15m bars (Binance Futures public klines)
- **Filter:** TREND_LEVE only (ADX 25–30) — no signals evaluated outside this regime
- **ADX computation:** local Wilder-smoothed ADX(14) on rolling {ADX_WINDOW}-bar window per bar
- **SL/TP simulation:** pullback uses helper output (entry/sl/tp1 from evaluate_setup);
  macross derives SL = entry ± ATR(14)×{ATR_SL_MULT}, TP1 = entry ± ATR(14)×{ATR_TP1_MULT}
- **Hold window:** {HOLD_BARS} bars (24h) max; SL/TP1/flat outcomes
- **OOS split:** 70/30 temporal (train = first 70%, test = last 30%)
- **Degradation flag:** PASS/WARN/FAIL per backtest_split.degradation_flag()

## Results — All assets aggregated

{agg_table}

## Results — Per asset

| Asset | Strategy | N | WR % | PF | Total R | OOS |
|---|---|---|---|---|---|---|
{per_asset_table}

## Verdict

{verdict_icon} **{verdict}**

{justification}

## Caveats

- **ADX filter scarcity:** TREND_LEVE [25–30] is a narrow band. In a predominantly
  ranging or strongly trending 60-day window, very few bars qualify, producing
  small N per (asset, strategy). The honesty contract threshold is ≥30 trades per cell.
- **15m bars from Binance Futures:** index assets (NAS100, EURUSD) are not available
  here; universe is crypto-only. Conclusions apply to crypto TREND_LEVE only.
- **Pullback detector sensitivity:** the pattern (3+ impulse candles → fib retrace →
  continuation) is structurally infrequent. Combined with the ADX gate, signal
  frequency is naturally low.
- **MA Crossover bar-by-bar limitation:** only LONG/SHORT cross bars trigger a signal
  (not the following bars in a sustained trend). This underestimates its true edge in
  a real trend-following context where a trader holds through trend.
- **No slippage/fees modeled.** Real execution would reduce metrics by ~0.1% roundtrip.
- **Past 60 days may not represent future TREND_LEVE frequency** — if BTC enters a
  sustained trend, TREND_LEVE bars become more common and sample sizes improve.

## Next steps

- If SAMPLE_TOO_SMALL: extend to 90d or add 3–5 more assets (SOL, LINK, DOGE)
- If WIRE-IN-RECOMMENDED: update `regime_mapping.json` TREND_LEVE entry to `/pullback`
  and run 2 weeks of live paper-trades to confirm
- If KEEP-MACROSS or NEUTRAL: no change to regime_mapping.json; re-evaluate in 30d
"""


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Backtest Pullback Detector vs MA Crossover in TREND_LEVE regime"
    )
    ap.add_argument(
        "--assets",
        default=",".join(DEFAULT_ASSETS),
        help="Comma-separated asset list (default: BTCUSDT,ETHUSDT,SOLUSDT,AVAXUSDT,INJUSDT)",
    )
    ap.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help="Days of history to fetch (default: 60)",
    )
    ap.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Path to write markdown report",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Also print JSON to stdout",
    )
    args = ap.parse_args()

    assets = [a.strip().upper() for a in args.assets.split(",") if a.strip()]

    print(
        f"Backtest: Pullback vs MA Crossover | TREND_LEVE [25–30] | "
        f"{args.days}d | {len(assets)} assets",
        file=sys.stderr,
    )

    per_asset_results: dict = {}

    for asset in assets:
        print(f"  Fetching {asset}...", file=sys.stderr)
        bars = fetch_bars(asset, args.days, interval="15m")
        if not bars:
            print(f"  WARN: no bars returned for {asset}", file=sys.stderr)
            per_asset_results[asset] = {"error": "no data"}
            continue
        print(f"  {asset}: {len(bars)} bars fetched. Running OOS split...", file=sys.stderr)
        result = run_oos_split(bars, asset)
        per_asset_results[asset] = result
        for strat in ("pullback", "macross"):
            sd = result.get(strat, {})
            tn = sd.get("train", {}).get("n", 0)
            te_n = sd.get("test", {}).get("n", 0)
            print(
                f"    {strat}: train={tn} trades, test={te_n} trades | "
                f"ADX-LEVE bars: train={sd.get('n_adx_bars_train', 0)}, "
                f"test={sd.get('n_adx_bars_test', 0)}",
                file=sys.stderr,
            )

    # Aggregate
    agg = aggregate_across_assets(per_asset_results)
    verdict, justification = compute_verdict(agg)

    print(f"\nVerdict: {verdict}", file=sys.stderr)
    print(f"Pullback: n={agg['pullback']['n']} WR={agg['pullback']['wr_pct']}% PF={agg['pullback']['pf']}", file=sys.stderr)
    print(f"MACross:  n={agg['macross']['n']} WR={agg['macross']['wr_pct']}% PF={agg['macross']['pf']}", file=sys.stderr)

    # JSON output
    if args.json:
        payload = {
            "per_asset": per_asset_results,
            "aggregate": agg,
            "verdict": verdict,
            "justification": justification,
        }
        print(json.dumps(payload, indent=2))

    # Markdown report
    report = build_markdown_report(
        per_asset_results=per_asset_results,
        agg=agg,
        verdict=verdict,
        justification=justification,
        assets=assets,
        days=args.days,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"\nReport written to: {out_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
