#!/usr/bin/env python3
"""CLI for L7 — online ML retrain trigger.

Usage:
  online_ml_retrain.py --profile bitunix [--force]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared/wally_core/src"))

from wally_core.learning.online_ml_retrain import should_retrain, retrain_and_validate


def main() -> None:
    parser = argparse.ArgumentParser(description="Online ML retrain (L7)")
    parser.add_argument("--profile", default="bitunix")
    parser.add_argument("--force", action="store_true", help="Skip threshold check, always retrain")
    parser.add_argument("--threshold", type=int, default=25, help="New trades required")

    args = parser.parse_args()

    if not args.force:
        needs_retrain = should_retrain(args.profile, new_trade_threshold=args.threshold)
        if not needs_retrain:
            print(f"Not enough new trades (threshold={args.threshold}). Skipping retrain.")
            print("Pass --force to override.")
            sys.exit(0)
        else:
            print(f"Retrain threshold met. Initiating...")
    else:
        print("Forced retrain...")

    result = retrain_and_validate(args.profile)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
