#!/usr/bin/env python3
"""Capture TV screenshot at trade entry. Calls TV MCP server if running."""
import sys
import argparse
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--profile", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--side", default="?")
    args = p.parse_args()

    profiles_dir = Path(os.environ.get("WALLY_PROFILES_DIR", ".claude/profiles"))
    screenshots_dir = profiles_dir / args.profile / "memory" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = screenshots_dir / f"{args.symbol}_{args.side}_{ts}.png"

    # Use macOS screencapture as fallback (no MCP dependency)
    try:
        subprocess.run(
            ["screencapture", "-x", str(out_path)],
            check=True, timeout=10,
        )
        print(f"Screenshot saved: {out_path}")
    except Exception as e:
        print(f"Screenshot failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
