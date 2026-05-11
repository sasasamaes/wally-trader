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


def _format_dashboard(s: dict) -> str:
    """Format stats dict into a pretty dashboard string."""
    cf = s["counterfactual"]
    lines = [
        "=" * 70,
        f"  DRAGNO AI — TRACKING DASHBOARD",
        "=" * 70,
        f"  Trades: {s['total_trades']}   Days: {s['days_tracked']}   Trades/day: {s['trades_per_day']}",
        f"  WR: {s['win_rate_pct']}%   PF: {s['profit_factor']}",
        f"  Net PnL: ${s['net_pnl']:+.4f}",
        f"  Avg win: ${s['avg_win']:+.4f}   Avg loss: ${s['avg_loss']:+.4f}",
        f"  Best win: ${s['best_win']:+.4f}   Worst loss: ${s['worst_loss']:+.4f}",
        "",
        f"  COUNTERFACTUAL (SL {cf['sl_cap']:.1f}%):",
        f"    New net PnL: ${cf['new_net_pnl']:+.4f}   Delta: ${cf['delta_usd']:+.4f} ({cf['delta_pct']:+.1f}%)",
        f"    SL hits: {cf['sl_hits']}   New PF: {cf['new_profit_factor']}   New worst loss: ${cf['new_worst_loss']:+.4f}",
        "",
        f"  BY SIDE:",
        f"    LONG  — count {s['long']['count']}, wins {s['long']['wins']}, net ${s['long']['net_pnl']:+.4f}",
        f"    SHORT — count {s['short']['count']}, wins {s['short']['wins']}, net ${s['short']['net_pnl']:+.4f}",
        "",
        f"  TOP 3 WINNERS:",
    ]
    for t in s["top_winners"]:
        lines.append(f"    {t['symbol']:<14} {t['pyg_pct']:+7.2f}%   ${t['pyg_usd']:+.4f}")
    lines.append("")
    lines.append(f"  TOP 3 LOSERS:")
    for t in s["top_losers"]:
        lines.append(f"    {t['symbol']:<14} {t['pyg_pct']:+7.2f}%   ${t['pyg_usd']:+.4f}")
    lines.append("")
    lines.append("  CAVEAT: counterfactual assumes one-way moves. Trades that closed")
    lines.append("  positive are assumed to NOT have touched the SL intra-trade.")
    lines.append("=" * 70)
    return "\n".join(lines)


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
    """Read JSON array from stdin, parse, dedup-append to CSV. Then print summary."""
    try:
        raw = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON on stdin: {e}", file=sys.stderr)
        return 1
    if not isinstance(raw, list):
        print("ERROR: stdin must be a JSON array of trade objects", file=sys.stderr)
        return 1
    try:
        parsed = parse_input_rows(raw)
    except (KeyError, ValueError) as e:
        print(f"ERROR: malformed trade row: {e}", file=sys.stderr)
        return 1
    added = append_rows_dedup(parsed)
    total = len(read_rows())
    print(f"Added {added} new trade(s). Total tracked: {total}.")
    print()
    # Print stats after append
    cmd_stats(sl_cap)
    # Regenerate md
    cmd_regenerate_md(sl_cap)
    return 0


def cmd_stats(sl_cap: float) -> int:
    """Compute and print stats dashboard."""
    rows = read_rows()
    if not rows:
        print("No data yet. Run /track-dragno with screenshots to populate the log.")
        return 2
    s = compute_stats(rows, sl_cap=sl_cap)
    print(_format_dashboard(s))
    return 0


def cmd_regenerate_md(sl_cap: float) -> int:
    """Rewrite the human-readable .md summary from the CSV."""
    rows = read_rows()
    path = md_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("# Dragno AI — Tracking\n\nNo data yet.\n")
        return 0
    s = compute_stats(rows, sl_cap=sl_cap)
    cf = s["counterfactual"]
    md = [
        "# Dragno AI — Tracking Summary",
        "",
        f"_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
        "",
        "## Aggregate",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Trades total | {s['total_trades']} |",
        f"| Days tracked | {s['days_tracked']} |",
        f"| Trades / day | {s['trades_per_day']} |",
        f"| Win Rate | {s['win_rate_pct']}% |",
        f"| Profit Factor | {s['profit_factor']} |",
        f"| Net PnL | ${s['net_pnl']:+.4f} |",
        f"| Avg win | ${s['avg_win']:+.4f} |",
        f"| Avg loss | ${s['avg_loss']:+.4f} |",
        f"| Best win | ${s['best_win']:+.4f} |",
        f"| Worst loss | ${s['worst_loss']:+.4f} |",
        "",
        f"## Counterfactual (SL {cf['sl_cap']:.1f}%)",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| New net PnL | ${cf['new_net_pnl']:+.4f} |",
        f"| Delta | ${cf['delta_usd']:+.4f} ({cf['delta_pct']:+.1f}%) |",
        f"| SL hits | {cf['sl_hits']} |",
        f"| New Profit Factor | {cf['new_profit_factor']} |",
        f"| New worst loss | ${cf['new_worst_loss']:+.4f} |",
        "",
        "## By Side",
        "",
        "| Side | Count | Wins | Net PnL |",
        "|---|---|---|---|",
        f"| LONG | {s['long']['count']} | {s['long']['wins']} | ${s['long']['net_pnl']:+.4f} |",
        f"| SHORT | {s['short']['count']} | {s['short']['wins']} | ${s['short']['net_pnl']:+.4f} |",
        "",
        "## Top 3 Winners",
        "",
        "| Symbol | PYG% | USD |",
        "|---|---|---|",
    ]
    for t in s["top_winners"]:
        md.append(f"| {t['symbol']} | {t['pyg_pct']:+.2f}% | ${t['pyg_usd']:+.4f} |")
    md.extend([
        "",
        "## Top 3 Losers",
        "",
        "| Symbol | PYG% | USD |",
        "|---|---|---|",
    ])
    for t in s["top_losers"]:
        md.append(f"| {t['symbol']} | {t['pyg_pct']:+.2f}% | ${t['pyg_usd']:+.4f} |")
    md.extend([
        "",
        "## Caveat",
        "",
        "> Counterfactual assumes one-way price movement: trades that closed worse than the SL cap",
        "> are assumed to have passed through the cap on the way down. Trades that closed positive",
        "> are assumed to have NOT touched the cap intra-trade. Without 1m/5m OHLCV per trade,",
        "> this model overestimates SL benefit for trades with deep drawdowns that later recovered.",
        "",
    ])
    path.write_text("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
