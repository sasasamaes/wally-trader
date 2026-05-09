#!/usr/bin/env python3
"""CLI for L8 — log user overrides + outcome correlation.

Usage:
  --my-rec REC --user-action ACTION --trade-id ID [--rationale "..."]
  --calibration [--days 90]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared/wally_core/src"))

from wally_core.learning.override_tracker import log_override, override_calibration


def main() -> None:
    parser = argparse.ArgumentParser(description="Override tracker CLI (L8)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--log", action="store_true", help="Log a new override")
    group.add_argument("--calibration", action="store_true", help="Show override calibration report")

    parser.add_argument("--my-rec", dest="my_rec", help="System recommendation")
    parser.add_argument("--user-action", dest="user_action", help="What user actually did")
    parser.add_argument("--trade-id", dest="trade_id", help="Trade ID")
    parser.add_argument("--rationale", default="", help="User rationale for override")
    parser.add_argument("--days", type=int, default=90, help="Days window for calibration")
    parser.add_argument("--profile", default="bitunix", help="Profile name")

    args = parser.parse_args()

    if args.log:
        if not all([args.my_rec, args.user_action, args.trade_id]):
            parser.error("--log requires --my-rec, --user-action, --trade-id")
        entry_id = log_override(
            args.my_rec,
            args.user_action,
            args.trade_id,
            args.rationale,
        )
        print(f"Override logged: entry_id={entry_id} type={args.my_rec}->{args.user_action}")

    elif args.calibration:
        report = override_calibration(days=args.days)
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
