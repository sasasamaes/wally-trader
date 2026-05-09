#!/usr/bin/env python3
"""Capture user's reasoning post-entry to memory/why_log.jsonl."""
import sys
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="Capture trade reasoning to why_log.jsonl")
    p.add_argument("--profile", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--side", choices=["LONG", "SHORT"], required=True)
    p.add_argument("--entry", type=float, required=True)
    p.add_argument("--reason", default="", help="Optional reason as flag (skips prompt)")
    args = p.parse_args()

    if args.reason:
        reason = args.reason
    else:
        print(f"Why are you taking this {args.side} on {args.symbol} @ ${args.entry}?")
        print("(One sentence — what's your edge here?)")
        try:
            reason = input("> ").strip()
        except EOFError:
            reason = ""

    if not reason:
        print("No reason captured — skipping log", file=sys.stderr)
        sys.exit(1)

    profiles_dir = Path(os.environ.get("WALLY_PROFILES_DIR", ".claude/profiles"))
    log_path = profiles_dir / args.profile / "memory" / "why_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "profile": args.profile,
        "symbol": args.symbol,
        "side": args.side,
        "entry": args.entry,
        "reason": reason,
    }

    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"Logged to {log_path}")


if __name__ == "__main__":
    main()
