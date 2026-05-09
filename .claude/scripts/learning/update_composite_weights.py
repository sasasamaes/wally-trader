#!/usr/bin/env python3
"""CLI for L3 — update composite weights via logistic regression on outcomes.

Usage:
  update_composite_weights.py --profile bitunix [--min-trades 50] [--apply]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared/wally_core/src"))

from wally_core.learning.adaptive_weights import (
    DEFAULT_WEIGHTS,
    ab_test_weights,
    fit_adaptive_weights,
    load_adaptive_weights,
    update_composite_weights,
)
from wally_core.learning.pattern_miner import _load_outcomes as load_outcomes_raw


def main() -> None:
    parser = argparse.ArgumentParser(description="Adaptive composite weights updater (L3)")
    parser.add_argument("--profile", default="bitunix", help="Profile name")
    parser.add_argument("--min-trades", dest="min_trades", type=int, default=50)
    parser.add_argument("--apply", action="store_true", help="Actually write new weights")
    parser.add_argument("--ab-test", action="store_true", help="Run A/B test before applying")

    args = parser.parse_args()

    result = fit_adaptive_weights(args.profile, n_trades=args.min_trades)
    print(json.dumps(result, indent=2))

    if result["status"] != "ok":
        print(f"Cannot update weights: {result['status']}")
        sys.exit(0)

    new_weights = result["weights"]
    current_weights = load_adaptive_weights(args.profile) or DEFAULT_WEIGHTS

    if args.ab_test:
        outcomes = load_outcomes_raw(args.profile)
        ab = ab_test_weights(current_weights, new_weights, outcomes)
        print("\nA/B test result:")
        print(json.dumps(ab, indent=2))
        if not ab["promote"]:
            print("A/B test: NOT promoting new weights (delta too small)")
            sys.exit(0)

    if args.apply:
        update_composite_weights(args.profile, new_weights)
        print(f"\nWeights updated for profile '{args.profile}'")
    else:
        print("\n[DRY RUN] Pass --apply to write weights")


if __name__ == "__main__":
    main()
