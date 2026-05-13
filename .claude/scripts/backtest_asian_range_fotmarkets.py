#!/usr/bin/env python3
"""backtest_asian_range_fotmarkets.py — Asian Range strategy backtest for fotmarkets profile.

Validates Bundle 3 secondary strategy (strategy_asian_range.md) before real-money use.

Usage:
    .claude/scripts/.venv/bin/python .claude/scripts/backtest_asian_range_fotmarkets.py
    .claude/scripts/.venv/bin/python .claude/scripts/backtest_asian_range_fotmarkets.py \\
        --symbol EURUSD --days 60 \\
        --output docs/backtest_findings_2026-05-12_asian_range_eurusd.md \\
        [--json] [--no-fetch --bars-file /tmp/eurusd5m.json]

Honesty contract:
  - If yfinance fetch fails or returns empty → report BLOCKED, don't fabricate data.
  - If <10 trades materialize → verdict MUST be NEEDS_MORE_DATA.
  - If max_dd > 12% → explicitly flag rule violation.
  - If WR < 45% AND PF < 1.2 → recommend DISCARD.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from asian_range import asian_session_high_low, detect_break_and_grab


# ---------------------------------------------------------------------------
# Constants (fotmarkets Phase 1 rules)
# ---------------------------------------------------------------------------

FOTMARKETS_WINDOW_START_UTC = (13, 0)   # CR 07:00 = UTC 13:00
FOTMARKETS_WINDOW_END_UTC = (16, 55)    # CR 10:55 = UTC 16:55

RISK_PCT = 0.01          # 1% risk per trade (Phase 1 recalibrated 2026-04-30)
CAPITAL_USD = 30.0       # fotmarkets $30 bonus
RISK_USD = CAPITAL_USD * RISK_PCT  # = $0.30

PIP_VALUE_USD = 10.0     # $10/pip per standard lot (EURUSD)
PIP_SIZE = 0.0001        # 1 pip = 0.0001 for EURUSD

SLIPPAGE_PIPS = 0.5
MIN_RR = 1.5
MAX_TRADES_PER_DAY = 1

MAX_DD_LIMIT_PCT = 12.0  # fotmarkets rule R5

OOS_SPLIT = 0.70         # 70% train / 30% test


# ---------------------------------------------------------------------------
# Data conversion
# ---------------------------------------------------------------------------

def yf_df_to_bars(df) -> list[dict]:
    """Convert yfinance DataFrame to list of bar dicts (asian_range format).

    Bar format: {ts: ISO-with-tz, open, high, low, close, volume}
    All numeric fields are plain float.
    """
    bars = []
    for ts, row in df.iterrows():
        try:
            # ts is pandas Timestamp; convert to UTC ISO string
            if hasattr(ts, "tz_localize"):
                ts_utc = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
            else:
                ts_utc = ts

            ts_iso = ts_utc.strftime("%Y-%m-%dT%H:%M:%S+00:00")

            # Handle both multi-index and flat columns
            def _get(key):
                for k in [key, key.lower(), key.capitalize()]:
                    if k in row.index:
                        v = row[k]
                        if hasattr(v, "item"):
                            return float(v.item())
                        return float(v)
                raise KeyError(key)

            bars.append({
                "ts": ts_iso,
                "open": _get("Open"),
                "high": _get("High"),
                "low": _get("Low"),
                "close": _get("Close"),
                "volume": float(row.get("Volume", 0) or 0),
            })
        except (KeyError, ValueError, TypeError):
            continue
    return bars


def load_bars_from_json(path: str) -> list[dict]:
    """Load bars from a JSON file (list of dicts with ts/open/high/low/close/volume)."""
    data = json.loads(Path(path).read_text())
    if not isinstance(data, list):
        raise ValueError(f"Expected list of bar dicts in {path}")
    # Normalize — support both per_asset_backtest format {t,o,h,l,c,v} and asian_range format
    normalized = []
    for b in data:
        if "ts" in b:
            normalized.append(b)
        elif "t" in b:
            # per_asset_backtest epoch-ms format
            ts_dt = datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc)
            normalized.append({
                "ts": ts_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "open": float(b.get("o", b.get("open", 0))),
                "high": float(b.get("h", b.get("high", 0))),
                "low": float(b.get("l", b.get("low", 0))),
                "close": float(b.get("c", b.get("close", 0))),
                "volume": float(b.get("v", b.get("volume", 0))),
            })
        else:
            raise ValueError(f"Unknown bar format: {b}")
    return normalized


def fetch_yfinance_bars(symbol: str = "EURUSD", days: int = 60) -> list[dict]:
    """Fetch 5m bars from Yahoo Finance. Raises RuntimeError on failure."""
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        raise RuntimeError(
            "yfinance not installed. Run: .claude/scripts/.venv/bin/pip install yfinance"
        )

    yf_map = {
        "EURUSD": "EURUSD=X",
        "GBPUSD": "GBPUSD=X",
    }
    ticker = yf_map.get(symbol, symbol)

    df = yf.download(
        ticker,
        period="60d",
        interval="5m",
        progress=False,
        auto_adjust=False,
        threads=False,
    )

    if df is None or df.empty:
        raise RuntimeError(f"yfinance returned empty data for {ticker}")

    # Flatten multi-index columns if present
    if hasattr(df.columns, "levels"):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    bars = yf_df_to_bars(df)
    if not bars:
        raise RuntimeError(f"No bars parsed from yfinance data for {ticker}")

    return bars


# ---------------------------------------------------------------------------
# Window & filtering helpers
# ---------------------------------------------------------------------------

def _parse_ts(ts_iso: str) -> datetime:
    dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def signal_in_fotmarkets_window(signal: dict) -> bool:
    """Return True if signal entry bar falls inside fotmarkets trading window.

    Window: UTC 13:00 (inclusive) to UTC 16:55 (exclusive).
    signal must have 'entry_bar_ts' key.
    """
    ts_str = signal.get("entry_bar_ts", "")
    if not ts_str:
        return False
    dt = _parse_ts(ts_str)
    h, m = dt.hour, dt.minute
    total_min = h * 60 + m
    window_start = FOTMARKETS_WINDOW_START_UTC[0] * 60 + FOTMARKETS_WINDOW_START_UTC[1]  # 13*60 = 780
    window_end = FOTMARKETS_WINDOW_END_UTC[0] * 60 + FOTMARKETS_WINDOW_END_UTC[1]        # 16*60+55 = 1015
    return window_start <= total_min < window_end


def _bar_after_eod(bar: dict, eod_utc_hour: int = 16, eod_utc_minute: int = 55) -> bool:
    dt = _parse_ts(bar["ts"])
    total_min = dt.hour * 60 + dt.minute
    return total_min >= eod_utc_hour * 60 + eod_utc_minute


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------

def simulate_fill(
    bars: list[dict],
    *,
    direction: str,
    entry_price: float,
    sl_price: float,
    tp_price: float,
    eod_utc_hour: int = 16,
    eod_utc_minute: int = 55,
    risk_usd: float = RISK_USD,
    slippage_pips: float = SLIPPAGE_PIPS,
) -> dict:
    """Walk forward bar-by-bar from entry, find first exit: SL, TP, or EOD.

    Returns dict with keys: outcome, entry_price, exit_price, pnl_usd, exit_ts.
    """
    sl_dist_pips = abs(entry_price - sl_price) / PIP_SIZE
    if sl_dist_pips < 1e-9:
        return {"outcome": "SKIP", "pnl_usd": 0.0, "exit_price": entry_price, "exit_ts": None}

    # Lot size: risk_usd = lot_size × sl_dist_pips × pip_value_per_lot
    # pip_value_per_lot = PIP_VALUE_USD × lot_size (for 1 standard lot)
    # risk_usd = lot_size × sl_dist_pips × PIP_VALUE_USD
    lot_size = risk_usd / (sl_dist_pips * PIP_VALUE_USD)

    # Include entry slippage (adversarial)
    slip_usd_entry = slippage_pips * PIP_VALUE_USD * lot_size

    for bar in bars:
        if _bar_after_eod(bar, eod_utc_hour, eod_utc_minute):
            # Force close at this bar's close
            exit_price = bar["close"]
            raw_pnl = (exit_price - entry_price) * (1 if direction == "long" else -1) * lot_size * 10_000 * PIP_VALUE_USD / 10_000
            # Simpler: pips gain × pip_value × lots
            pips = (exit_price - entry_price) / PIP_SIZE * (1 if direction == "long" else -1)
            pnl = pips * PIP_VALUE_USD * lot_size - slip_usd_entry - slippage_pips * PIP_VALUE_USD * lot_size
            return {
                "outcome": "FORCE_CLOSE_EOD",
                "exit_price": exit_price,
                "exit_ts": bar["ts"],
                "pnl_usd": round(pnl, 4),
                "lot_size": round(lot_size, 6),
            }

        if direction == "long":
            # Check SL first (pessimistic — within bar SL takes priority)
            if bar["low"] <= sl_price:
                exit_price = sl_price - slippage_pips * PIP_SIZE  # adversarial slip
                pips = (exit_price - entry_price) / PIP_SIZE
                pnl = pips * PIP_VALUE_USD * lot_size - slip_usd_entry
                return {
                    "outcome": "SL",
                    "exit_price": exit_price,
                    "exit_ts": bar["ts"],
                    "pnl_usd": round(pnl, 4),
                    "lot_size": round(lot_size, 6),
                }
            if bar["high"] >= tp_price:
                exit_price = tp_price - slippage_pips * PIP_SIZE
                pips = (exit_price - entry_price) / PIP_SIZE
                pnl = pips * PIP_VALUE_USD * lot_size - slip_usd_entry
                return {
                    "outcome": "TP",
                    "exit_price": exit_price,
                    "exit_ts": bar["ts"],
                    "pnl_usd": round(pnl, 4),
                    "lot_size": round(lot_size, 6),
                }
        else:  # short
            if bar["high"] >= sl_price:
                exit_price = sl_price + slippage_pips * PIP_SIZE
                pips = (entry_price - exit_price) / PIP_SIZE
                pnl = pips * PIP_VALUE_USD * lot_size - slip_usd_entry
                return {
                    "outcome": "SL",
                    "exit_price": exit_price,
                    "exit_ts": bar["ts"],
                    "pnl_usd": round(pnl, 4),
                    "lot_size": round(lot_size, 6),
                }
            if bar["low"] <= tp_price:
                exit_price = tp_price + slippage_pips * PIP_SIZE
                pips = (entry_price - exit_price) / PIP_SIZE
                pnl = pips * PIP_VALUE_USD * lot_size - slip_usd_entry
                return {
                    "outcome": "TP",
                    "exit_price": exit_price,
                    "exit_ts": bar["ts"],
                    "pnl_usd": round(pnl, 4),
                    "lot_size": round(lot_size, 6),
                }

    # No bars left — treat as EOD close on last bar
    if bars:
        last = bars[-1]
        exit_price = last["close"]
        pips = (exit_price - entry_price) / PIP_SIZE * (1 if direction == "long" else -1)
        pnl = pips * PIP_VALUE_USD * lot_size - slip_usd_entry - slippage_pips * PIP_VALUE_USD * lot_size
        return {
            "outcome": "FORCE_CLOSE_EOD",
            "exit_price": exit_price,
            "exit_ts": last["ts"],
            "pnl_usd": round(pnl, 4),
            "lot_size": round(lot_size, 6),
        }

    return {"outcome": "NO_BARS", "pnl_usd": 0.0, "exit_price": entry_price, "exit_ts": None}


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------

def compute_max_dd(equity_curve: list[float]) -> float:
    """Return max drawdown as percentage (0-100)."""
    if len(equity_curve) < 2:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100.0 if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return max_dd


def compute_metrics(trades: list[dict]) -> dict:
    """Compute WR, PF, Sharpe, Max DD from a list of trade dicts with pnl_usd."""
    if not trades:
        return {
            "total_trades": 0, "wr_pct": 0.0, "pf": 0.0,
            "sharpe": 0.0, "max_dd_pct": 0.0,
            "total_return_pct": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
        }

    pnls = [t["pnl_usd"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    wr = len(wins) / len(trades) * 100.0
    pf = sum(wins) / abs(sum(losses)) if losses and sum(losses) != 0 else float("inf") if wins else 0.0
    total_pnl = sum(pnls)
    total_return_pct = total_pnl / CAPITAL_USD * 100.0

    # Equity curve
    equity_curve = [CAPITAL_USD]
    for p in pnls:
        equity_curve.append(equity_curve[-1] + p)
    max_dd = compute_max_dd(equity_curve)

    # Sharpe (annualized, assume 252 trading days)
    if len(pnls) >= 2:
        daily_ret = [p / CAPITAL_USD for p in pnls]
        mean_r = statistics.mean(daily_ret)
        std_r = statistics.stdev(daily_ret)
        sharpe = (mean_r / std_r * math.sqrt(252)) if std_r > 0 else 0.0
    else:
        sharpe = 0.0

    return {
        "total_trades": len(trades),
        "wr_pct": round(wr, 2),
        "pf": round(pf, 3),
        "sharpe": round(sharpe, 3),
        "max_dd_pct": round(max_dd, 2),
        "total_return_pct": round(total_return_pct, 2),
        "avg_win": round(sum(wins) / len(wins), 4) if wins else 0.0,
        "avg_loss": round(sum(losses) / len(losses), 4) if losses else 0.0,
        "n_wins": len(wins),
        "n_losses": len(losses),
    }


# ---------------------------------------------------------------------------
# OOS split
# ---------------------------------------------------------------------------

def oos_verdict(train_trades: list[dict], test_trades: list[dict]) -> str:
    """Return PASS / WARN / FAIL based on OOS degradation."""
    if not train_trades or not test_trades:
        return "INSUFFICIENT_DATA"
    train_m = compute_metrics(train_trades)
    test_m = compute_metrics(test_trades)
    wr_delta = train_m["wr_pct"] - test_m["wr_pct"]
    if wr_delta > 20:
        return "FAIL"
    if wr_delta > 10:
        return "WARN"
    return "PASS"


# ---------------------------------------------------------------------------
# Main backtest engine
# ---------------------------------------------------------------------------

def run_backtest(bars: list[dict]) -> dict:
    """Run the full backtest on the given bar list.

    Returns dict with trades, metrics, oos_result, validation_checks.
    """
    if not bars:
        return {
            "status": "BLOCKED",
            "reason": "No bars available",
            "trades": [],
            "metrics": {},
        }

    # ---- Group bars by calendar date (UTC date) ----
    days_map: dict[str, list[dict]] = defaultdict(list)
    for b in bars:
        dt = _parse_ts(b["ts"])
        date_key = dt.strftime("%Y-%m-%d")
        days_map[date_key].append(b)

    sorted_dates = sorted(days_map.keys())
    trades = []
    daily_stats = []

    for date_key in sorted_dates:
        day_bars = sorted(days_map[date_key], key=lambda b: b["ts"])

        # Skip weekends (forex market closed)
        dt_day = datetime.strptime(date_key, "%Y-%m-%d")
        if dt_day.weekday() >= 5:  # Saturday=5, Sunday=6
            continue

        # ---- Build session context ----
        # We need Asian bars (UTC 23:00 prev day through UTC 08:00 this day)
        # plus London open at UTC 08:00 this day.
        # Collect all bars up to and including the current day for the lookback.

        # London open anchor: first bar at or after 08:00 UTC on this date
        london_open = f"{date_key}T08:00:00+00:00"

        # Build a combined bar list: previous day + current day (for Asian session)
        prev_date_idx = sorted_dates.index(date_key) - 1
        all_context_bars = []
        if prev_date_idx >= 0:
            all_context_bars.extend(days_map[sorted_dates[prev_date_idx]])
        all_context_bars.extend(day_bars)
        all_context_bars = sorted(all_context_bars, key=lambda b: b["ts"])

        # ---- Compute Asian session H/L ----
        asian = asian_session_high_low(all_context_bars, anchor=london_open)
        if asian["n_bars"] < 4:
            # Not enough Asian session data
            daily_stats.append({"date": date_key, "result": "NO_ASIAN_DATA"})
            continue

        # ---- Find grab in bars AFTER London open, within fotmarkets window ----
        # fotmarkets window: UTC 13:00-16:55
        window_start = f"{date_key}T13:00:00+00:00"
        window_end = f"{date_key}T16:55:00+00:00"

        window_bars = [
            b for b in all_context_bars
            if b["ts"] >= window_start and b["ts"] < window_end
        ]

        if not window_bars:
            daily_stats.append({"date": date_key, "result": "NO_WINDOW_BARS"})
            continue

        # ---- Rolling scan: look for FIRST grab anywhere in the window ----
        # detect_break_and_grab checks only the first `window` bars of the slice.
        # We roll through the window in steps of 1 bar so we find the first grab
        # that occurs anywhere in the fotmarkets window.
        grab = None
        grab_window_offset = 0
        GRAB_WINDOW = 4  # must match asian_range.GRAB_WINDOW_BARS
        for i in range(len(window_bars)):
            slice_bars = window_bars[i : i + GRAB_WINDOW + 2]  # +2 for close-back bar
            g = detect_break_and_grab(
                slice_bars,
                asian_high=asian["high"],
                asian_low=asian["low"],
                window=GRAB_WINDOW,
            )
            if g is not None:
                grab = g
                grab_window_offset = i
                break

        if grab is None:
            daily_stats.append({"date": date_key, "result": "NO_GRAB"})
            continue

        # ---- Build signal ----
        # grab_bar_idx is relative to the slice; translate back to window_bars index
        actual_grab_idx = grab_window_offset + grab["grab_bar_idx"]
        entry_bar = window_bars[actual_grab_idx]
        if grab["direction"] == "long":
            entry_price = entry_bar["close"]
            sl_price = grab["sweep_extreme"] - 0.0002  # 2 pip buffer
            tp_price = asian["high"]
        else:
            entry_price = entry_bar["close"]
            sl_price = grab["sweep_extreme"] + 0.0002
            tp_price = asian["low"]

        risk = abs(entry_price - sl_price)
        reward = abs(tp_price - entry_price)
        rr = reward / risk if risk > 0 else 0.0

        # ---- Fotmarkets rule: R:R >= 1.5 ----
        if rr < MIN_RR:
            daily_stats.append({
                "date": date_key,
                "result": "SKIP_LOW_RR",
                "rr": round(rr, 2),
            })
            continue

        # ---- Fotmarkets rule: entry inside window ----
        signal_with_ts = {
            "direction": grab["direction"],
            "entry": entry_price,
            "sl": sl_price,
            "tp": tp_price,
            "rr": rr,
            "entry_bar_ts": entry_bar["ts"],
        }
        if not signal_in_fotmarkets_window(signal_with_ts):
            daily_stats.append({
                "date": date_key,
                "result": "SKIP_OUTSIDE_WINDOW",
                "entry_ts": entry_bar["ts"],
            })
            continue

        # ---- Fotmarkets rule: max 1 trade/day ----
        trades_today = sum(1 for t in trades if t["date"] == date_key)
        if trades_today >= MAX_TRADES_PER_DAY:
            daily_stats.append({"date": date_key, "result": "SKIP_MAX_TRADES"})
            continue

        # ---- Simulate fill ----
        # Forward bars from entry bar onward (within window and a bit after for EOD)
        forward_bars = [
            b for b in day_bars
            if b["ts"] > entry_bar["ts"]
        ]

        fill = simulate_fill(
            forward_bars,
            direction=grab["direction"],
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            eod_utc_hour=FOTMARKETS_WINDOW_END_UTC[0],
            eod_utc_minute=FOTMARKETS_WINDOW_END_UTC[1],
            risk_usd=RISK_USD,
            slippage_pips=SLIPPAGE_PIPS,
        )

        trade = {
            "date": date_key,
            "direction": grab["direction"],
            "entry_price": round(entry_price, 5),
            "sl_price": round(sl_price, 5),
            "tp_price": round(tp_price, 5),
            "rr": round(rr, 3),
            "entry_ts": entry_bar["ts"],
            "exit_ts": fill.get("exit_ts"),
            "exit_price": fill.get("exit_price"),
            "outcome": fill["outcome"],
            "pnl_usd": fill["pnl_usd"],
            "asian_high": asian["high"],
            "asian_low": asian["low"],
            "n_asian_bars": asian["n_bars"],
        }
        trades.append(trade)
        daily_stats.append({"date": date_key, "result": fill["outcome"], "pnl": fill["pnl_usd"]})

    # ---- Aggregate metrics ----
    metrics = compute_metrics(trades)

    # ---- OOS split ----
    split_idx = int(len(trades) * OOS_SPLIT)
    train_trades = trades[:split_idx]
    test_trades = trades[split_idx:]
    oos = oos_verdict(train_trades, test_trades)

    # ---- Day-of-week breakdown ----
    dow_map: dict[str, list[float]] = defaultdict(list)
    for t in trades:
        dow = datetime.strptime(t["date"], "%Y-%m-%d").strftime("%a")
        dow_map[dow].append(t["pnl_usd"])

    dow_stats = {}
    for dow in ["Mon", "Tue", "Wed", "Thu", "Fri"]:
        pnls = dow_map.get(dow, [])
        wins = [p for p in pnls if p > 0]
        dow_stats[dow] = {
            "n": len(pnls),
            "wr_pct": round(len(wins) / len(pnls) * 100, 1) if pnls else 0.0,
            "net_pnl": round(sum(pnls), 4),
        }

    # ---- Grabs per day ----
    trading_days = len([d for d in sorted_dates if datetime.strptime(d, "%Y-%m-%d").weekday() < 5])
    grabs_per_day = round(len(trades) / trading_days, 2) if trading_days > 0 else 0.0
    tp_count = sum(1 for t in trades if t["outcome"] == "TP")
    tp_hit_pct = round(tp_count / len(trades) * 100, 1) if trades else 0.0

    # ---- Validation checks ----
    all_in_window = all(signal_in_fotmarkets_window({"entry_bar_ts": t["entry_ts"], **t}) for t in trades)
    all_rr_ok = all(t["rr"] >= MIN_RR for t in trades)
    dd_ok = metrics.get("max_dd_pct", 0) <= MAX_DD_LIMIT_PCT

    validation = {
        "max_dd_le_12pct": dd_ok,
        "all_entries_in_window": all_in_window,
        "no_overnight": True,  # enforced by construction (EOD close)
        "all_rr_ge_1_5": all_rr_ok,
        "oos_verdict": oos,
    }

    # ---- Overall verdict ----
    if len(trades) < 10:
        verdict = "NEEDS_MORE_DATA"
        verdict_reason = (
            f"Only {len(trades)} trades materialized over the backtest period. "
            "Asian Range setup requires a clean grab pattern — low frequency is inherent. "
            "Need ≥10 trades for statistically meaningful conclusions. "
            "Continue manual sandbox mode as specified in strategy_asian_range.md."
        )
    elif metrics["wr_pct"] < 45 and metrics["pf"] < 1.2:
        verdict = "DISCARD"
        verdict_reason = (
            f"WR {metrics['wr_pct']:.1f}% < 45% AND PF {metrics['pf']:.3f} < 1.2. "
            "No statistical edge found. Asian Range ICT setup without consistent grab quality "
            "in this data period. Not worth mental bandwidth without demonstrated edge."
        )
    elif not dd_ok:
        verdict = "KEEP_AS_SECONDARY"
        verdict_reason = (
            f"Max DD {metrics['max_dd_pct']:.1f}% exceeds fotmarkets limit of {MAX_DD_LIMIT_PCT}%. "
            "RULE VIOLATION: do NOT increase to Phase 2 risk (2%) — DD would double. "
            "Keep as secondary ONLY at Phase 1 risk (1%). Monitor DD closely in live trading."
        )
    elif metrics["pf"] >= 1.3 and metrics["wr_pct"] >= 50:
        verdict = "PROMOTE_TO_PRIMARY"
        verdict_reason = (
            f"WR {metrics['wr_pct']:.1f}% ≥ 50% AND PF {metrics['pf']:.3f} ≥ 1.3. "
            "Strong enough edge to consider promotion. However, verify OOS verdict is PASS "
            "and accumulate 20+ live trades before promotion decision."
        )
    else:
        verdict = "KEEP_AS_SECONDARY"
        verdict_reason = (
            f"WR {metrics['wr_pct']:.1f}% / PF {metrics['pf']:.3f} / Max DD {metrics['max_dd_pct']:.1f}% "
            "show marginal edge — acceptable as secondary strategy at Phase 1 risk (1%). "
            f"OOS verdict: {oos}. Continue sandbox until 20+ live trades confirm live edge."
        )

    return {
        "status": "DONE",
        "symbol": "EURUSD",
        "period_days": len(sorted_dates),
        "trading_days": trading_days,
        "trades": trades,
        "metrics": metrics,
        "train_metrics": compute_metrics(train_trades),
        "test_metrics": compute_metrics(test_trades),
        "oos_verdict": oos,
        "dow_stats": dow_stats,
        "grabs_per_day": grabs_per_day,
        "tp_hit_pct": tp_hit_pct,
        "validation": validation,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "daily_stats": daily_stats,
    }


# ---------------------------------------------------------------------------
# Markdown report writer
# ---------------------------------------------------------------------------

def build_markdown_report(result: dict, run_date: str = "2026-05-12") -> str:
    trades = result.get("trades", [])
    metrics = result.get("metrics", {})
    validation = result.get("validation", {})
    dow_stats = result.get("dow_stats", {})
    verdict = result.get("verdict", "NEEDS_MORE_DATA")
    verdict_reason = result.get("verdict_reason", "")
    oos = result.get("oos_verdict", "N/A")

    dd_emoji = "✅" if validation.get("max_dd_le_12pct") else "❌"
    window_emoji = "✅" if validation.get("all_entries_in_window") else "❌"
    overnight_emoji = "✅"
    rr_emoji = "✅" if validation.get("all_rr_ge_1_5") else "❌"

    oos_emoji = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "INSUFFICIENT_DATA": "⚠️"}.get(oos, "⚠️")

    # Last 10 trades table
    last10 = trades[-10:] if len(trades) >= 10 else trades
    trade_rows = ""
    for t in last10:
        trade_rows += (
            f"| {t['date']} | {t['direction'].upper()} | {t['entry_price']:.5f} "
            f"| {t['sl_price']:.5f} | {t['tp_price']:.5f} "
            f"| {t.get('exit_price', 'N/A')} | {t['outcome']} | ${t['pnl_usd']:.4f} |\n"
        )
    if not trade_rows:
        trade_rows = "| — | — | — | — | — | — | — | — |\n"

    # DOW table
    dow_rows = ""
    for dow in ["Mon", "Tue", "Wed", "Thu", "Fri"]:
        s = dow_stats.get(dow, {"n": 0, "wr_pct": 0.0, "net_pnl": 0.0})
        dow_rows += f"| {dow} | {s['n']} | {s['wr_pct']:.1f}% | ${s['net_pnl']:.4f} |\n"

    # Status
    if result.get("status") == "BLOCKED":
        blocked_reason = result.get("reason", "Unknown error")
        return f"""# Backtest — Asian Range Strategy (EURUSD 5m, fotmarkets)

**Date:** {run_date}
**Status:** BLOCKED

## Reason

{blocked_reason}

## Action Required

Fix the data fetch issue and re-run:
```bash
.claude/scripts/.venv/bin/python .claude/scripts/backtest_asian_range_fotmarkets.py --symbol EURUSD --days 60
```
"""

    report = f"""# Backtest — Asian Range Strategy (EURUSD 5m, fotmarkets)

**Date:** {run_date}
**Trigger:** Bundle 3 (2026-05-12) marked Asian Range as secondary strategy "no backtested aún". This is that backtest.

## Methodology

- Symbol: EURUSD
- TF: 5m (Yahoo Finance, `EURUSD=X`)
- Period: last 60 days
- Asian session: UTC 23:00–08:00
- London open anchor: UTC 08:00
- Fotmarkets window: CR 07:00–10:55 = UTC 13:00–16:55
- Risk per trade: 1% ($0.30 on $30 capital — Phase 1 recalibrated 2026-04-30)
- Max trades/day: 1
- Slippage: {SLIPPAGE_PIPS} pips (adversarial, applied at entry and exit)
- Min R:R: {MIN_RR}:1
- Calendar days: {result.get("period_days", "N/A")} | Trading days (Mon-Fri): {result.get("trading_days", "N/A")}

## Trade-by-trade (last {len(last10)}) — sanity check

| Date | Direction | Entry | SL | TP | Exit | Reason | PnL $ |
|---|---|---|---|---|---|---|---|
{trade_rows}

## Aggregate metrics

| Metric | Value |
|---|---|
| Total trades | {metrics.get("total_trades", 0)} |
| Win Rate % | {metrics.get("wr_pct", 0):.1f}% |
| Profit Factor | {metrics.get("pf", 0):.3f} |
| Total return % | {metrics.get("total_return_pct", 0):.2f}% |
| Max DD % | {metrics.get("max_dd_pct", 0):.2f}% (limit: {MAX_DD_LIMIT_PCT}%) |
| Sharpe (annualized) | {metrics.get("sharpe", 0):.3f} |
| Avg win $ | ${metrics.get("avg_win", 0):.4f} |
| Avg loss $ | ${metrics.get("avg_loss", 0):.4f} |
| Grabs/trading day | {result.get("grabs_per_day", 0):.2f} |
| TP hit % | {result.get("tp_hit_pct", 0):.1f}% |

## OOS Split (70/30 temporal)

| Sample | N | WR% | PF | Max DD% |
|---|---|---|---|---|
| Train (first 70%) | {result["train_metrics"].get("total_trades", 0)} | {result["train_metrics"].get("wr_pct", 0):.1f}% | {result["train_metrics"].get("pf", 0):.3f} | {result["train_metrics"].get("max_dd_pct", 0):.2f}% |
| Test (last 30%) | {result["test_metrics"].get("total_trades", 0)} | {result["test_metrics"].get("wr_pct", 0):.1f}% | {result["test_metrics"].get("pf", 0):.3f} | {result["test_metrics"].get("max_dd_pct", 0):.2f}% |
| OOS verdict | {oos_emoji} **{oos}** | | | |

## Performance by day of week

| Day | N | WR % | Net PnL |
|---|---|---|---|
{dow_rows}

## Fotmarkets rule compliance

- Max DD ≤ {MAX_DD_LIMIT_PCT}%: {dd_emoji} ({metrics.get("max_dd_pct", 0):.2f}%)
- All entries in CR 07:00–10:55 window: {window_emoji}
- No overnight positions: {overnight_emoji}
- All trades R:R ≥ {MIN_RR}: {rr_emoji}
- OOS verdict: {oos_emoji} {oos}

## Verdict

**{verdict}**

{verdict_reason}

---
*Generated by `backtest_asian_range_fotmarkets.py` — data from Yahoo Finance (yfinance). Not financial advice.*
"""
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="Asian Range backtest for fotmarkets EURUSD")
    p.add_argument("--symbol", default="EURUSD")
    p.add_argument("--days", type=int, default=60)
    p.add_argument("--output", default="docs/backtest_findings_2026-05-12_asian_range_eurusd.md")
    p.add_argument("--json", action="store_true", help="Print JSON results to stdout")
    p.add_argument("--no-fetch", action="store_true", help="Skip yfinance fetch, use --bars-file")
    p.add_argument("--bars-file", help="Path to JSON bars file (when --no-fetch)")
    args = p.parse_args()

    # ---- Fetch or load bars ----
    if args.no_fetch:
        if not args.bars_file:
            print("ERROR: --no-fetch requires --bars-file", file=sys.stderr)
            return 2
        print(f"Loading bars from {args.bars_file} ...", file=sys.stderr)
        try:
            bars = load_bars_from_json(args.bars_file)
        except Exception as e:
            print(f"BLOCKED: Failed to load bars: {e}", file=sys.stderr)
            result = {"status": "BLOCKED", "reason": str(e), "trades": [], "metrics": {}}
            if args.json:
                print(json.dumps(result, indent=2, default=str))
            return 1
    else:
        print(f"Fetching {args.symbol} 5m bars from Yahoo Finance ...", file=sys.stderr)
        try:
            bars = fetch_yfinance_bars(symbol=args.symbol, days=args.days)
            print(f"Fetched {len(bars)} bars", file=sys.stderr)
        except Exception as e:
            print(f"BLOCKED: yfinance fetch failed: {e}", file=sys.stderr)
            result = {"status": "BLOCKED", "reason": str(e), "trades": [], "metrics": {}}
            if args.json:
                print(json.dumps(result, indent=2, default=str))
            return 1

    # ---- Run backtest ----
    print("Running backtest ...", file=sys.stderr)
    result = run_backtest(bars)

    n = result["metrics"].get("total_trades", 0)
    wr = result["metrics"].get("wr_pct", 0)
    pf = result["metrics"].get("pf", 0)
    dd = result["metrics"].get("max_dd_pct", 0)
    verdict = result.get("verdict", "N/A")
    print(f"Results: {n} trades | WR {wr:.1f}% | PF {pf:.3f} | MaxDD {dd:.2f}% | {verdict}",
          file=sys.stderr)

    # ---- JSON output ----
    if args.json:
        print(json.dumps(result, indent=2, default=str))

    # ---- Markdown report ----
    md = build_markdown_report(result, run_date="2026-05-12")
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"Report written to {out_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
