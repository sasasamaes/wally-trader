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
import csv
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
