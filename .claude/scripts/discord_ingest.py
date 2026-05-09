#!/usr/bin/env python3
"""Discord signal ingestion scaffold.

Multi-server / multi-channel polling. Auto-grade source + auto-validate via /signal.
This v1: scaffold + stub. Real Discord bot integration deferred to v2 when bot token available.
"""
import sys
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def load_config(config_path: Path) -> dict:
    """Load Discord ingestion config."""
    if not config_path.exists():
        return {"servers": [], "default_profile": "bitunix"}
    return json.loads(config_path.read_text())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true", help="Run once instead of polling")
    p.add_argument("--config", default=".claude/cache/discord_ingest.json")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path)

    if not config.get("servers"):
        print("No Discord servers configured.")
        print(f"   Edit {config_path} with: {{\"servers\": [{{\"id\": \"...\", \"channels\": [...], \"source_id\": \"...\"}}]}}")
        print(f"   Set DISCORD_BOT_TOKEN env var.")
        sys.exit(0)

    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token and not args.dry_run:
        print("DISCORD_BOT_TOKEN not set — skipping.")
        sys.exit(0)

    # Real implementation would use discord.py here.
    # For now: scaffold acknowledges configured servers and exits.
    print(f"Discord ingest scaffold: {len(config['servers'])} server(s) configured")
    for server in config["servers"]:
        print(f"  * {server.get('name', server.get('id'))} -> source_id={server.get('source_id')}")

    if args.dry_run:
        print("(dry-run -- no actual polling)")
    else:
        print("(v1 scaffold -- actual Discord polling requires discord.py SDK + bot token; see TODO)")


if __name__ == "__main__":
    main()
