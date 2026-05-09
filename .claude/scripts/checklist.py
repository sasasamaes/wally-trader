#!/usr/bin/env python3
"""Pre-trade checklist — interactive prompt before submitting orders."""
import sys
import argparse
from pathlib import Path

_SHARED = Path(__file__).resolve().parent.parent.parent / "shared/wally_core/src"
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from wally_core.discipline import pre_trade_checklist


def main():
    p = argparse.ArgumentParser(description="Pre-trade checklist — 6-question gate before submitting orders")
    p.add_argument("--no-input", action="store_true", help="Just print questions (for non-interactive)")
    p.add_argument("--allow-override", action="store_true", help="Print override flag if blocker fails")
    args = p.parse_args()

    questions = pre_trade_checklist()

    if args.no_input:
        for q in questions:
            mark = "BLOCKER" if q.is_blocker else "advisory"
            print(f"  [{q.key}] {mark} — {q.text}")
        sys.exit(0)

    print("=" * 60)
    print("  PRE-TRADE CHECKLIST — answer YES/NO to each")
    print("=" * 60)

    answers = {}
    for q in questions:
        prefix = "BLOCKER" if q.is_blocker else "advisory"
        ans = ""
        while ans.lower() not in ("y", "n", "yes", "no", "s", "si"):
            try:
                ans = input(f"[{prefix}] {q.text} (y/n): ").strip()
            except EOFError:
                # Non-interactive environment
                ans = "n"
                break
        answers[q.key] = ans.lower() in ("y", "yes", "s", "si")

    blockers_failed = [q.key for q in questions if q.is_blocker and not answers[q.key]]
    if blockers_failed:
        print(f"Blockers failed: {', '.join(blockers_failed)}")
        if args.allow_override:
            try:
                override = input("Override and proceed anyway? (yes/no): ").strip().lower()
            except EOFError:
                override = ""
            if override == "yes":
                print("OVERRIDE_LOGGED — proceed at your own risk")
                # Log to audit (P7 will replace this)
                Path(".claude/cache/checklist_overrides.log").parent.mkdir(parents=True, exist_ok=True)
                from datetime import datetime, timezone
                with open(".claude/cache/checklist_overrides.log", "a") as f:
                    f.write(f"{datetime.now(timezone.utc).isoformat()} | overrode: {','.join(blockers_failed)}\n")
                sys.exit(0)
        sys.exit(1)

    print("All blockers passed — proceed")
    sys.exit(0)


if __name__ == "__main__":
    main()
