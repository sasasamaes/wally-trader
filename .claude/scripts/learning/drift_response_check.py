#!/usr/bin/env python3
"""CLI for L6 — drift response check.

Usage:
  drift_response_check.py --profile bitunix [--apply]
  drift_response_check.py --profile bitunix --append-check OK|WARN|ALERT
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared/wally_core/src"))

from wally_core.learning.drift_response import (
    append_calibration_check,
    apply_tightening,
    check_drift_streak,
    get_current_tightening,
    relax_when_resolved,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Drift response check (L6)")
    parser.add_argument("--profile", default="bitunix")
    parser.add_argument("--apply", action="store_true", help="Apply tightening/relaxing")
    parser.add_argument("--append-check", dest="append_check", metavar="SEVERITY",
                        help="Append a calibration check result (OK|WARN|ALERT)")
    parser.add_argument("--threshold", type=int, default=7, help="Alert streak days to trigger tighten")

    args = parser.parse_args()

    if args.append_check:
        sev = args.append_check.upper()
        if sev not in ("OK", "WARN", "ALERT"):
            print(f"Invalid severity: {sev}. Use OK, WARN, or ALERT")
            sys.exit(1)
        append_calibration_check(args.profile, sev)
        print(f"Appended check: severity={sev}")

    # Check current drift streak
    result = check_drift_streak(args.profile, alert_days_threshold=args.threshold)
    print(json.dumps(result, indent=2))

    current = get_current_tightening(args.profile)
    print(f"\nCurrent tightening: level={current['level']} active={current['active']}")
    if current["active"]:
        print(f"  composite_threshold_bump: +{current['composite_threshold_bump']}pts")
        print(f"  confluence_requirement_bump: +{current['confluence_requirement_bump']}")

    if args.apply:
        if result["should_tighten"]:
            current_level = result["current_level"]
            new_level = min(current_level + 1, 2)
            apply_tightening(args.profile, new_level)
            print(f"\nTightening applied: level {current_level} → {new_level}")
        else:
            # Try to relax
            relax_result = relax_when_resolved(args.profile)
            if relax_result["relaxed"]:
                print(f"\nTightening relaxed: was level {relax_result['previous_level']} → 0")
            else:
                print("\nNo tightening change needed")
    else:
        if result["should_tighten"]:
            print(f"\n[DRY RUN] Would tighten to level {min(result['current_level']+1, 2)} — pass --apply")


if __name__ == "__main__":
    main()
