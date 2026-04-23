"""mt5_bridge.py — Bridge helpers for Claude <-> MT5 EA communication.

Provides pure-Python utilities for reading/writing JSON state and command
files that the ClaudeBridge EA exchanges via the MT5 Files directory.

All time-sensitive functions accept an optional `now` parameter for
deterministic testing.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# JSON I/O helpers
# ---------------------------------------------------------------------------

def load_state(path: str) -> dict:
    """Load mt5_state.json.  Returns empty dict if file missing or invalid."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_commands(path: str) -> dict:
    """Load mt5_commands.json.  Returns ``{"commands": []}`` if missing/invalid."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure the key exists even if file is malformed
            if "commands" not in data:
                data["commands"] = []
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"commands": []}


def save_commands(path: str, data: dict) -> None:
    """Atomically write *data* to *path*.

    Writes to a sibling ``.tmp`` file then renames, so a crash mid-write
    never leaves a truncated JSON file for the EA to read.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = str(p) + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(p))
    except Exception:
        # Clean up tmp on error
        try:
            os.remove(tmp_path)
        except FileNotFoundError:
            pass
        raise


def append_command(path: str, cmd: dict) -> dict:
    """Append *cmd* to the commands array in *path* and save atomically.

    Returns the updated commands dict.
    """
    data = load_commands(path)
    data["commands"].append(cmd)
    save_commands(path, data)
    return data


# ---------------------------------------------------------------------------
# EA liveness
# ---------------------------------------------------------------------------

def ea_is_alive(
    state: dict,
    max_age_sec: int = 60,
    now: Optional[datetime] = None,
) -> bool:
    """Return True if EA's last heartbeat is within *max_age_sec* seconds.

    Args:
        state: Parsed mt5_state.json dict.
        max_age_sec: Maximum acceptable staleness in seconds.
        now: Override for current time (UTC).  Defaults to ``datetime.now(utc)``.
    """
    last_update_str: Optional[str] = state.get("last_update")
    if not last_update_str:
        return False

    try:
        last_update = datetime.fromisoformat(last_update_str)
        # Ensure timezone-aware for comparison
        if last_update.tzinfo is None:
            last_update = last_update.replace(tzinfo=timezone.utc)
    except ValueError:
        return False

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    age_sec = (now - last_update).total_seconds()
    return age_sec <= max_age_sec


# ---------------------------------------------------------------------------
# Command ID generation
# ---------------------------------------------------------------------------

def next_cmd_id(
    commands: dict,
    now: Optional[datetime] = None,
) -> str:
    """Generate next command ID in format ``cmd_YYYYMMDD_HHMMSS_NN``.

    Sequence number starts at 01 and increments if a command with the same
    timestamp already exists in *commands*.

    Args:
        commands: Parsed mt5_commands.json dict (may be empty or ``{}``).
        now: Override for current time (UTC).  Defaults to ``datetime.now(utc)``.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    ts = now.strftime("%Y%m%d_%H%M%S")
    prefix = f"cmd_{ts}_"

    existing_ids: list[str] = [
        c.get("id", "")
        for c in commands.get("commands", [])
        if isinstance(c, dict)
    ]

    # Find the highest sequence number for the current timestamp
    max_seq = 0
    for cmd_id in existing_ids:
        if cmd_id.startswith(prefix):
            try:
                seq = int(cmd_id[len(prefix):])
                max_seq = max(max_seq, seq)
            except ValueError:
                pass

    return f"{prefix}{max_seq + 1:02d}"


# ---------------------------------------------------------------------------
# Pending order matching
# ---------------------------------------------------------------------------

def match_pending_to_positions(
    pending: list,
    positions: list,
) -> list[tuple]:
    """Cross-match pending commands to open positions by (symbol, magic=77777).

    Args:
        pending: List of pending order dicts (from pending_orders.json).
        positions: List of position dicts (from mt5_state.json["positions"]).

    Returns:
        List of ``(pending_order, position)`` tuples for confirmed matches.
    """
    matches: list[tuple] = []
    for order in pending:
        symbol = order.get("symbol")
        magic = order.get("magic")
        if magic != 77777:
            continue
        for pos in positions:
            if pos.get("symbol") == symbol and pos.get("magic") == 77777:
                matches.append((order, pos))
                break
    return matches


# ---------------------------------------------------------------------------
# State summary
# ---------------------------------------------------------------------------

def format_state_brief(
    state: dict,
    now: Optional[datetime] = None,
    max_age_sec: int = 60,
) -> str:
    """One-line status string for statusline display.

    Returns one of:
    - ``"EA ✓ Xs • Pos: N"``    — alive, N positions
    - ``"EA ⚠️ Xm"``             — stale (> max_age_sec)
    - ``"EA ✗"``                 — no state / no last_update
    """
    last_update_str: Optional[str] = state.get("last_update")
    if not last_update_str:
        return "EA ✗"

    try:
        last_update = datetime.fromisoformat(last_update_str)
        if last_update.tzinfo is None:
            last_update = last_update.replace(tzinfo=timezone.utc)
    except ValueError:
        return "EA ✗"

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    age_sec = (now - last_update).total_seconds()

    if age_sec <= max_age_sec:
        positions = state.get("positions", [])
        pos_count = len(positions) if isinstance(positions, list) else 0
        age_int = int(age_sec)
        return f"EA ✓ {age_int}s • Pos: {pos_count}"
    else:
        age_min = int(age_sec / 60)
        return f"EA ⚠️ {age_min}m"


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _cli_ea_status() -> None:
    """Print ea-status one-liner for statusline.sh consumption."""
    # Default state path: .claude/profiles/ftmo/memory/mt5_state.json
    # Resolved relative to this script's location.
    script_dir = Path(__file__).parent
    state_path = script_dir.parent / "profiles" / "ftmo" / "memory" / "mt5_state.json"
    state = load_state(str(state_path))
    print(format_state_brief(state))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ea-status":
        _cli_ea_status()
    elif len(sys.argv) > 1 and sys.argv[1] == "append-command":
        # Usage: python3 mt5_bridge.py append-command <commands_path> <json_cmd>
        if len(sys.argv) < 4:
            print("Usage: mt5_bridge.py append-command <path> '<json>'", file=sys.stderr)
            sys.exit(1)
        commands_path = sys.argv[2]
        cmd_dict = json.loads(sys.argv[3])
        result = append_command(commands_path, cmd_dict)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: mt5_bridge.py <ea-status|append-command>", file=sys.stderr)
        sys.exit(1)
