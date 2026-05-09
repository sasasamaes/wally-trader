#!/usr/bin/env python3
"""CLI for L4 — monthly strategy refresh.

Usage:
  monthly_strategy_refresh.py --profile bitunix [--apply] [--days 60]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared/wally_core/src"))

from wally_core.learning.strategy_refresh import refresh_strategy_mapping, REGIME_MAPPING_PATH


def main() -> None:
    parser = argparse.ArgumentParser(description="Monthly strategy refresh (L4)")
    parser.add_argument("--profile", default="bitunix", help="Profile to analyze")
    parser.add_argument("--days", type=int, default=60, help="Days lookback")
    parser.add_argument("--threshold", type=float, default=10.0, help="Drift threshold pp")
    parser.add_argument("--apply", action="store_true", help="Write changes to regime_mapping.json")

    args = parser.parse_args()

    mapping_path = REGIME_MAPPING_PATH if args.apply else None

    result = refresh_strategy_mapping(
        args.profile,
        days=args.days,
        threshold_drift=args.threshold,
        mapping_path=mapping_path,
        dry_run=(not args.apply),
    )

    print(json.dumps(result, indent=2))

    if result["changes"]:
        print(f"\n{len(result['changes'])} regime(s) with drift detected:")
        for c in result["changes"]:
            if c["drift"] is not None:
                print(f"  {c['regime']}: prior WR {c['prior_wr']}% → live WR {c['live_wr']}% (drift {c['drift']:+.1f}pp)")
            else:
                print(f"  {c['regime']}: NEW data — live WR {c['live_wr']}% (n={c['n']})")
    else:
        print("\nNo significant regime drift detected.")

    if args.apply:
        print(f"\nLearning stats written to regime_mapping.json")
    else:
        print("\n[DRY RUN] Pass --apply to write changes")


if __name__ == "__main__":
    main()
