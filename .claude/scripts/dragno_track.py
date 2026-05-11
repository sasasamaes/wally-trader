#!/usr/bin/env python3
"""dragno_track.py — Track Dragno AI bot trades from Bitunix.

Subcommands:
  --append-from-stdin       Read JSON array of trades from stdin, dedup, append to CSV
  --stats                   Compute and print stats dashboard
  --regenerate-md           Rewrite memory/external_traders/dragno_ai.md from CSV

Options:
  --sl-cap FLOAT            SL percentage cap for counterfactual (default -8.0)
"""
from __future__ import annotations

import argparse
import csv as _csv
import json
import sys
from datetime import datetime
from pathlib import Path


CSV_FIELDS = [
    "date", "time_open", "time_close", "symbol", "side", "leverage",
    "entry", "exit", "pyg_pct", "pyg_usd", "margin_est", "duration_min", "source",
]

DEFAULT_SL_CAP = -8.0


def repo_root() -> Path:
    """Walk up from this file to find repo root (contains .claude/)."""
    cur = Path(__file__).resolve()
    while cur != cur.parent:
        if (cur / ".claude").is_dir() and (cur / "memory").is_dir():
            return cur
        cur = cur.parent
    return Path.cwd()


def csv_path() -> Path:
    return repo_root() / "memory" / "external_traders" / "dragno_ai.csv"


def md_path() -> Path:
    return repo_root() / "memory" / "external_traders" / "dragno_ai.md"


def derive_margin(pyg_pct: float, pyg_usd: float) -> float:
    """Derive position margin from PYG% and PYG USD.

    Bitunix shows PYG% on margin (leverage-adjusted). Margin = |pyg_usd| / (|pyg_pct|/100).
    Returns 0.0 if pyg_pct is zero (avoid divide-by-zero).
    """
    if pyg_pct == 0.0:
        return 0.0
    return abs(pyg_usd) / (abs(pyg_pct) / 100.0)


SIDE_MAP = {"largo": "LONG", "long": "LONG", "corto": "SHORT", "short": "SHORT"}


def _parse_signed_float(s) -> float:
    """Parse a possibly-prefixed numeric string. Python's float() handles '-15.28'
    and '15.48' natively but rejects '+15.48' in some legacy locales — strip '+' first."""
    return float(str(s).replace("+", "").strip())


def _duration_minutes(time_open: str, time_close: str) -> int:
    """Minutes between two HH:MM:SS strings. Negative or cross-midnight returns 0."""
    fmt = "%H:%M:%S"
    try:
        t0 = datetime.strptime(time_open, fmt)
        t1 = datetime.strptime(time_close, fmt)
    except ValueError:
        return 0
    delta = (t1 - t0).total_seconds() / 60.0
    return max(0, int(round(delta)))


def parse_input_rows(raw: list[dict]) -> list[dict]:
    """Normalize Claude-parsed screenshot rows into CSV-ready dicts.

    Required input fields per row: date, time_open, time_close, symbol, side,
    leverage, entry, exit, pyg_pct, pyg_usd.
    """
    out = []
    for r in raw:
        side_key = str(r["side"]).strip().lower()
        if side_key not in SIDE_MAP:
            raise ValueError(f"Unknown side: {r['side']!r}")
        leverage_str = str(r["leverage"]).strip().lower().rstrip("x")
        normalized = {
            "date": r["date"],
            "time_open": r["time_open"],
            "time_close": r["time_close"],
            "symbol": str(r["symbol"]).upper(),
            "side": SIDE_MAP[side_key],
            "leverage": int(leverage_str),
            "entry": float(r["entry"]),
            "exit": float(r["exit"]),
            "pyg_pct": _parse_signed_float(r["pyg_pct"]),
            "pyg_usd": _parse_signed_float(r["pyg_usd"]),
            "duration_min": _duration_minutes(r["time_open"], r["time_close"]),
            "source": "manual_screenshot",
        }
        normalized["margin_est"] = round(derive_margin(normalized["pyg_pct"], normalized["pyg_usd"]), 4)
        out.append(normalized)
    return out


NUMERIC_FIELDS = ("leverage", "entry", "exit", "pyg_pct", "pyg_usd", "margin_est", "duration_min")


def read_rows() -> list[dict]:
    """Read CSV into list of dicts with numeric fields coerced. Returns [] if missing/empty."""
    path = csv_path()
    if not path.exists():
        return []
    with path.open(newline="") as f:
        reader = _csv.DictReader(f)
        rows = []
        for raw in reader:
            row = dict(raw)
            for k in NUMERIC_FIELDS:
                if k in row and row[k] != "":
                    try:
                        row[k] = int(row[k]) if k in ("leverage", "duration_min") else float(row[k])
                    except ValueError:
                        pass
            rows.append(row)
        return rows


def write_rows(rows: list[dict]) -> None:
    """Overwrite the CSV with the given rows (creates parent dirs)."""
    path = csv_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = _csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})


def _dedup_key(row: dict) -> tuple[str, str, str]:
    return (str(row["date"]), str(row["time_open"]), str(row["symbol"]).upper())


def append_rows_dedup(new_rows: list[dict]) -> int:
    """Append rows to CSV, skipping any whose dedup key already exists. Returns count added."""
    existing = read_rows()
    seen = {_dedup_key(r) for r in existing}
    added = 0
    for r in new_rows:
        if _dedup_key(r) in seen:
            continue
        existing.append(r)
        seen.add(_dedup_key(r))
        added += 1
    if added > 0:
        write_rows(existing)
    return added


def compute_stats(rows: list[dict], sl_cap: float = DEFAULT_SL_CAP) -> dict:
    """Compute aggregate + counterfactual + side breakdown + top winners/losers."""
    if not rows:
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate_pct": 0.0,
            "net_pnl": 0.0, "profit_factor": 0.0,
            "avg_win": 0.0, "avg_loss": 0.0, "best_win": 0.0, "worst_loss": 0.0,
            "days_tracked": 0, "trades_per_day": 0.0,
            "counterfactual": {
                "sl_cap": sl_cap, "sl_hits": 0,
                "new_net_pnl": 0.0, "delta_usd": 0.0, "delta_pct": 0.0,
                "new_profit_factor": 0.0, "new_worst_loss": 0.0,
            },
            "long": {"count": 0, "wins": 0, "net_pnl": 0.0},
            "short": {"count": 0, "wins": 0, "net_pnl": 0.0},
            "top_winners": [], "top_losers": [],
        }

    pnls = [float(r["pyg_usd"]) for r in rows]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = 100.0 * len(wins) / len(pnls)
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else 0.0

    # Counterfactual: cap losses worse than sl_cap at sl_cap
    new_pnls = []
    sl_hits = 0
    for r in rows:
        pct = float(r["pyg_pct"])
        usd = float(r["pyg_usd"])
        if pct < sl_cap:
            margin = derive_margin(pct, usd)
            new_pnls.append((sl_cap / 100.0) * margin)
            sl_hits += 1
        else:
            new_pnls.append(usd)
    new_net = sum(new_pnls)
    delta_usd = new_net - sum(pnls)
    delta_pct = (delta_usd / sum(pnls) * 100.0) if sum(pnls) != 0 else 0.0
    new_losses = [p for p in new_pnls if p <= 0]
    new_pf = (sum(wins) / abs(sum(new_losses))) if new_losses and sum(new_losses) != 0 else 0.0

    longs = [r for r in rows if r["side"] == "LONG"]
    shorts = [r for r in rows if r["side"] == "SHORT"]
    long_pnls = [float(r["pyg_usd"]) for r in longs]
    short_pnls = [float(r["pyg_usd"]) for r in shorts]

    sorted_rows = sorted(rows, key=lambda r: float(r["pyg_usd"]), reverse=True)
    top_winners = [{"symbol": r["symbol"], "pyg_pct": float(r["pyg_pct"]), "pyg_usd": float(r["pyg_usd"])} for r in sorted_rows[:3]]
    top_losers = [{"symbol": r["symbol"], "pyg_pct": float(r["pyg_pct"]), "pyg_usd": float(r["pyg_usd"])} for r in sorted_rows[-3:][::-1]]

    days = {r["date"] for r in rows}

    return {
        "total_trades": len(rows),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(win_rate, 2),
        "net_pnl": round(sum(pnls), 4),
        "profit_factor": round(pf, 3),
        "avg_win": round(sum(wins) / len(wins), 4) if wins else 0.0,
        "avg_loss": round(sum(losses) / len(losses), 4) if losses else 0.0,
        "best_win": round(max(pnls), 4),
        "worst_loss": round(min(pnls), 4),
        "days_tracked": len(days),
        "trades_per_day": round(len(rows) / len(days), 2) if days else 0.0,
        "counterfactual": {
            "sl_cap": sl_cap,
            "sl_hits": sl_hits,
            "new_net_pnl": round(new_net, 4),
            "delta_usd": round(delta_usd, 4),
            "delta_pct": round(delta_pct, 2),
            "new_profit_factor": round(new_pf, 3),
            "new_worst_loss": round(min(new_pnls), 4) if new_pnls else 0.0,
        },
        "long": {
            "count": len(longs),
            "wins": sum(1 for p in long_pnls if p > 0),
            "net_pnl": round(sum(long_pnls), 4),
        },
        "short": {
            "count": len(shorts),
            "wins": sum(1 for p in short_pnls if p > 0),
            "net_pnl": round(sum(short_pnls), 4),
        },
        "top_winners": top_winners,
        "top_losers": top_losers,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Track Dragno AI bot trades")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--append-from-stdin", action="store_true")
    group.add_argument("--stats", action="store_true")
    group.add_argument("--regenerate-md", action="store_true")
    p.add_argument("--sl-cap", type=float, default=DEFAULT_SL_CAP)
    args = p.parse_args()

    if args.append_from_stdin:
        return cmd_append_from_stdin(args.sl_cap)
    if args.stats:
        return cmd_stats(args.sl_cap)
    if args.regenerate_md:
        return cmd_regenerate_md(args.sl_cap)
    return 1


def cmd_append_from_stdin(sl_cap: float) -> int:
    raise NotImplementedError


def cmd_stats(sl_cap: float) -> int:
    raise NotImplementedError


def cmd_regenerate_md(sl_cap: float) -> int:
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
