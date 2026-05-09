#!/usr/bin/env python3
"""CLI for L1 — log/update/report system recommendations.

Usage:
  --log --agent AGENT --recommendation REC --rationale "..." [--trade-id ID]
  --update --id ENTRY_ID --action ACTION
  --outcome --id ENTRY_ID --pnl-24h N --pnl-final M
  --report [--days 30]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

# Add wally_core to path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared/wally_core/src"))

from wally_core.learning.recommendation_log import (
    calibration_report,
    log_recommendation,
    update_outcome,
    update_user_action,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Recommendation log CLI (L1)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--log", action="store_true")
    group.add_argument("--update", action="store_true")
    group.add_argument("--outcome", action="store_true")
    group.add_argument("--report", action="store_true")

    parser.add_argument("--agent", help="Agent name (punk-watch-analyst, signal-validator, etc.)")
    parser.add_argument("--recommendation", "--rec", help="System recommendation (CUT, HOLD, GO, etc.)")
    parser.add_argument("--rationale", help="Recommendation rationale text")
    parser.add_argument("--trade-id", dest="trade_id", help="Associated trade ID")
    parser.add_argument("--id", dest="entry_id", help="Entry ID to update")
    parser.add_argument("--action", help="User action for --update")
    parser.add_argument("--pnl-24h", dest="pnl_24h", type=float, help="24h PnL USD")
    parser.add_argument("--pnl-final", dest="pnl_final", type=float, help="Final PnL USD")
    parser.add_argument("--days", type=int, default=30, help="Days window for report")

    args = parser.parse_args()

    if args.log:
        if not all([args.agent, args.recommendation, args.rationale]):
            parser.error("--log requires --agent, --recommendation, --rationale")
        entry_id = log_recommendation(
            args.agent,
            args.recommendation,
            args.rationale,
            trade_id=args.trade_id,
        )
        print(f"Logged entry_id={entry_id}")

    elif args.update:
        if not all([args.entry_id, args.action]):
            parser.error("--update requires --id and --action")
        update_user_action(args.entry_id, args.action)
        print(f"Updated {args.entry_id} user_action={args.action}")

    elif args.outcome:
        if not args.entry_id:
            parser.error("--outcome requires --id")
        update_outcome(args.entry_id, args.pnl_24h, args.pnl_final)
        print(f"Updated {args.entry_id} outcome: 24h={args.pnl_24h} final={args.pnl_final}")

    elif args.report:
        report = calibration_report(days=args.days)
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
