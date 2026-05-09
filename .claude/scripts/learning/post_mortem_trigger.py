#!/usr/bin/env python3
"""CLI for L5 — post-mortem trigger.

Usage:
  post_mortem_trigger.py --profile bitunix --watch         # watch mode (poll)
  post_mortem_trigger.py --profile bitunix --trade-id ID   # single trade
  post_mortem_trigger.py --profile bitunix --aggregate     # aggregate report
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared/wally_core/src"))

from wally_core.learning.post_mortem import auto_postmortem, aggregate_postmortems, append_to_postmortem_log

LOSS_THRESHOLD = -5.0   # USD
POLL_INTERVAL = 1800    # 30 minutes


def _already_processed(trade_id: str, seen_path: Path) -> bool:
    if not seen_path.exists():
        return False
    seen = set(seen_path.read_text().splitlines())
    return trade_id in seen


def _mark_processed(trade_id: str, seen_path: Path) -> None:
    with open(seen_path, "a") as f:
        f.write(trade_id + "\n")


def watch_mode(profile: str, loss_threshold: float = LOSS_THRESHOLD) -> None:
    """Poll outcomes_v2.csv for new losing trades and auto-trigger post-mortem."""
    outcomes_path = Path(f".claude/profiles/{profile}/memory/outcomes_v2.csv")
    seen_path = Path(f".claude/profiles/{profile}/memory/learning/.processed_postmortems")
    seen_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[post-mortem-watcher] Watching {outcomes_path} (threshold {loss_threshold:.0f} USD)")
    print(f"Poll interval: {POLL_INTERVAL}s")

    while True:
        if outcomes_path.exists():
            with open(outcomes_path, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Build composite trade_id
                    symbol = row.get("symbol", "")
                    open_time = row.get("open_time_utc", "")
                    trade_id = f"{symbol}:{open_time}"

                    try:
                        pnl = float(row.get("pnl_usd") or 0)
                    except (ValueError, TypeError):
                        continue

                    if pnl >= loss_threshold:
                        continue
                    if _already_processed(trade_id, seen_path):
                        continue

                    # New losing trade!
                    print(f"[post-mortem] New loss: {trade_id} PnL=${pnl:.2f}")
                    try:
                        report = auto_postmortem(trade_id, profile=profile, outcomes_row=row)
                        append_to_postmortem_log(report, profile)
                        _mark_processed(trade_id, seen_path)
                        print(f"  Tags: {', '.join(report.lesson_tags)}")
                        print(f"  Findings: {'; '.join(report.structural_findings)}")
                    except Exception as e:
                        print(f"  ERROR: {e}")

        time.sleep(POLL_INTERVAL)


def main() -> None:
    parser = argparse.ArgumentParser(description="Post-mortem trigger (L5)")
    parser.add_argument("--profile", default="bitunix")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--watch", action="store_true", help="Watch mode: poll every 30min")
    group.add_argument("--trade-id", dest="trade_id", help="Single trade post-mortem")
    group.add_argument("--aggregate", action="store_true", help="Aggregate report")
    parser.add_argument("--days", type=int, default=30, help="Days for aggregate")
    parser.add_argument("--threshold", type=float, default=LOSS_THRESHOLD)

    args = parser.parse_args()

    if args.watch:
        watch_mode(args.profile, args.threshold)
    elif args.trade_id:
        report = auto_postmortem(args.trade_id, profile=args.profile)
        print(json.dumps({
            "trade_id": report.trade_id,
            "lesson_tags": report.lesson_tags,
            "regime_entry": report.regime_entry,
            "regime_exit": report.regime_exit,
            "held_minutes": report.held_minutes,
            "pnl_usd": report.pnl_usd,
            "structural_findings": report.structural_findings,
        }, indent=2))
        append_to_postmortem_log(report, args.profile)
        print(f"Appended to postmortems.md")
    elif args.aggregate:
        result = aggregate_postmortems(args.profile, days=args.days)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
