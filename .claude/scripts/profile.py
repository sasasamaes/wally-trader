#!/usr/bin/env python3
"""Cross-platform port of profile.sh — works on Linux/macOS/Windows.

Usage:
  python profile.py show        — prints current profile (env var WALLY_PROFILE overrides file)
  python profile.py get         — prints just the profile name (no timestamp)
  python profile.py set <name>  — switches to <name>
  python profile.py stale       — exit 0 if stale >12h, exit 1 if fresh
  python profile.py validate    — checks profile exists in profiles/ dir

Multi-terminal mode:
  Set WALLY_PROFILE env var per-terminal to use different profiles in parallel.
  When WALLY_PROFILE is set, 'set' command is blocked.
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FLAG_FILE = SCRIPT_DIR.parent / "active_profile"
PROFILES_DIR = SCRIPT_DIR.parent / "profiles"
STALE_SECONDS = 12 * 3600  # 12 hours


def get_env_profile():
    return os.environ.get("WALLY_PROFILE", "").strip() or None


def cmd_show():
    env = get_env_profile()
    if env:
        print(f"{env} | env:WALLY_PROFILE (session override)")
        return 0
    if FLAG_FILE.exists():
        print(FLAG_FILE.read_text().strip())
        return 0
    print("no profile set")
    return 1


def cmd_get():
    env = get_env_profile()
    if env:
        print(env)
        return 0
    if FLAG_FILE.exists():
        line = FLAG_FILE.read_text().strip()
        # Format is "name | timestamp"
        name = line.split("|", 1)[0].strip()
        print(name)
        return 0
    print("")
    return 1


def cmd_set(name: str):
    if not name:
        print("ERROR: profile name required", file=sys.stderr)
        return 2
    target = PROFILES_DIR / name
    if not target.is_dir():
        print(f"ERROR: profile '{name}' not found in {PROFILES_DIR}", file=sys.stderr)
        return 3
    env = get_env_profile()
    if env:
        msg = (
            f"ERROR: WALLY_PROFILE='{env}' is set in this session (env var override active).\n"
            "       'set' would not affect the current session. To switch:\n"
            "         - Exit this Claude session\n"
            f"         - Run: WALLY_PROFILE={name} claude   (or unset WALLY_PROFILE)\n"
            "       Persistent file is NOT being modified to avoid confusion."
        )
        print(msg, file=sys.stderr)
        return 4
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    FLAG_FILE.write_text(f"{name} | {ts}\n")
    print(f"switched to: {name} | {ts}")
    return 0


def cmd_stale():
    """Exit 0 if stale (>12h or missing), exit 1 if fresh."""
    if get_env_profile():
        return 1  # env override = fresh by definition
    if not FLAG_FILE.exists():
        return 0  # stale = prompt needed
    try:
        line = FLAG_FILE.read_text().strip()
        ts_str = line.split("|", 1)[1].strip() if "|" in line else ""
        flag_dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - flag_dt).total_seconds()
        return 0 if age > STALE_SECONDS else 1
    except (ValueError, IndexError):
        return 0  # parse fail = stale


def cmd_validate():
    rc = cmd_get()
    if rc != 0:
        print("INVALID: no profile set", file=sys.stderr)
        return 1
    # We can't capture our own print easily, redo logic
    env = get_env_profile()
    name = env if env else (
        FLAG_FILE.read_text().strip().split("|", 1)[0].strip()
        if FLAG_FILE.exists() else ""
    )
    if not name or not (PROFILES_DIR / name).is_dir():
        print(f"INVALID: profile '{name}' not in {PROFILES_DIR}", file=sys.stderr)
        return 1
    # cmd_get already printed the name
    return 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "show"
    if cmd == "show":
        return cmd_show()
    elif cmd == "get":
        return cmd_get()
    elif cmd == "set":
        name = argv[2] if len(argv) > 2 else ""
        return cmd_set(name)
    elif cmd == "stale":
        return cmd_stale()
    elif cmd == "validate":
        # validate prints from cmd_get, suppress to handle ourselves
        env = get_env_profile()
        name = env if env else (
            FLAG_FILE.read_text().strip().split("|", 1)[0].strip()
            if FLAG_FILE.exists() else ""
        )
        if not name or not (PROFILES_DIR / name).is_dir():
            print(f"INVALID: profile '{name}' not in {PROFILES_DIR}", file=sys.stderr)
            return 1
        print(f"OK: {name}")
        return 0
    else:
        print("Usage: profile.py {show|get|set <name>|stale|validate}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
