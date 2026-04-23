"""Tests for mt5_bridge.py — TDD: written before implementation."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# Import target module
from mt5_bridge import (
    load_state,
    load_commands,
    save_commands,
    append_command,
    ea_is_alive,
    next_cmd_id,
    match_pending_to_positions,
    format_state_brief,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: str, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f)


def _now_iso(delta_sec: int = 0) -> str:
    """Return UTC ISO string offset by delta_sec from now."""
    dt = datetime.now(timezone.utc) + timedelta(seconds=delta_sec)
    return dt.isoformat()


# ---------------------------------------------------------------------------
# load_state
# ---------------------------------------------------------------------------

def test_load_state_missing_file(tmp_path):
    result = load_state(str(tmp_path / "nonexistent.json"))
    assert result == {}


def test_load_state_valid(tmp_path):
    data = {"account": {"balance": 10000}, "last_update": "2026-04-22T10:00:00+00:00"}
    p = tmp_path / "state.json"
    _write_json(str(p), data)
    result = load_state(str(p))
    assert result == data


# ---------------------------------------------------------------------------
# load_commands
# ---------------------------------------------------------------------------

def test_load_commands_missing(tmp_path):
    result = load_commands(str(tmp_path / "nonexistent.json"))
    assert result == {"commands": []}


def test_load_commands_valid(tmp_path):
    data = {"commands": [{"id": "cmd_20260422_100000_01", "type": "BUY"}]}
    p = tmp_path / "commands.json"
    _write_json(str(p), data)
    result = load_commands(str(p))
    assert result == data


# ---------------------------------------------------------------------------
# save_commands (atomic)
# ---------------------------------------------------------------------------

def test_save_commands_atomic(tmp_path):
    p = tmp_path / "commands.json"
    data = {"commands": [{"id": "cmd_20260422_100000_01", "type": "BUY"}]}
    save_commands(str(p), data)

    # File must exist and be valid
    assert p.exists()
    with open(p) as f:
        loaded = json.load(f)
    assert loaded == data

    # Temp file must NOT remain (atomic rename)
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0


# ---------------------------------------------------------------------------
# append_command
# ---------------------------------------------------------------------------

def test_append_command_empty(tmp_path):
    p = tmp_path / "commands.json"
    cmd = {"id": "cmd_20260422_100000_01", "type": "BUY", "symbol": "BTCUSD"}
    result = append_command(str(p), cmd)
    assert len(result["commands"]) == 1
    assert result["commands"][0] == cmd


def test_append_command_preserves_existing(tmp_path):
    p = tmp_path / "commands.json"
    cmd1 = {"id": "cmd_20260422_100000_01", "type": "BUY"}
    cmd2 = {"id": "cmd_20260422_100001_01", "type": "SELL"}
    append_command(str(p), cmd1)
    result = append_command(str(p), cmd2)
    assert len(result["commands"]) == 2
    assert result["commands"][0] == cmd1
    assert result["commands"][1] == cmd2


# ---------------------------------------------------------------------------
# ea_is_alive
# ---------------------------------------------------------------------------

def test_ea_is_alive_fresh():
    now = datetime.now(timezone.utc)
    last_update = (now - timedelta(seconds=10)).isoformat()
    state = {"last_update": last_update, "account": {"balance": 10000}}
    assert ea_is_alive(state, max_age_sec=60, now=now) is True


def test_ea_is_alive_stale():
    now = datetime.now(timezone.utc)
    last_update = (now - timedelta(seconds=120)).isoformat()
    state = {"last_update": last_update}
    assert ea_is_alive(state, max_age_sec=60, now=now) is False


def test_ea_is_alive_missing():
    assert ea_is_alive({}) is False


def test_ea_is_alive_no_last_update():
    assert ea_is_alive({"account": {}}) is False


# ---------------------------------------------------------------------------
# next_cmd_id
# ---------------------------------------------------------------------------

def test_next_cmd_id_first():
    now = datetime(2026, 4, 22, 10, 0, 0, tzinfo=timezone.utc)
    commands = {}
    cmd_id = next_cmd_id(commands, now=now)
    assert cmd_id == "cmd_20260422_100000_01"


def test_next_cmd_id_same_second():
    now = datetime(2026, 4, 22, 10, 0, 0, tzinfo=timezone.utc)
    # Simulate existing command at exact same second
    commands = {"commands": [{"id": "cmd_20260422_100000_01"}]}
    cmd_id = next_cmd_id(commands, now=now)
    assert cmd_id == "cmd_20260422_100000_02"


def test_next_cmd_id_different_second():
    now = datetime(2026, 4, 22, 10, 0, 5, tzinfo=timezone.utc)
    # Existing command at a different second
    commands = {"commands": [{"id": "cmd_20260422_100000_01"}]}
    cmd_id = next_cmd_id(commands, now=now)
    assert cmd_id == "cmd_20260422_100005_01"


# ---------------------------------------------------------------------------
# match_pending_to_positions
# ---------------------------------------------------------------------------

def test_match_pending_filled():
    pending = [
        {"id": "cmd_20260422_100000_01", "symbol": "BTCUSD", "magic": 77777, "status": "sent_to_ea"}
    ]
    positions = [
        {"symbol": "BTCUSD", "magic": 77777, "ticket": 12345, "profit": 50.0}
    ]
    matches = match_pending_to_positions(pending, positions)
    assert len(matches) == 1
    assert matches[0] == (pending[0], positions[0])


def test_match_pending_no_match():
    pending = [
        {"id": "cmd_20260422_100000_01", "symbol": "BTCUSD", "magic": 77777, "status": "sent_to_ea"}
    ]
    positions = [
        {"symbol": "BTCUSD", "magic": 12345, "ticket": 99999, "profit": -10.0}
    ]
    matches = match_pending_to_positions(pending, positions)
    assert len(matches) == 0


# ---------------------------------------------------------------------------
# format_state_brief
# ---------------------------------------------------------------------------

def test_format_state_brief_fresh():
    now = datetime.now(timezone.utc)
    last_update = (now - timedelta(seconds=3)).isoformat()
    state = {
        "last_update": last_update,
        "positions": [{"symbol": "BTCUSD", "magic": 77777}],
    }
    result = format_state_brief(state, now=now)
    # "EA ✓ Xs • Pos: 1" pattern
    assert "EA" in result
    assert "Pos: 1" in result
    assert "✓" in result


def test_format_state_brief_stale():
    now = datetime.now(timezone.utc)
    last_update = (now - timedelta(seconds=130)).isoformat()
    state = {"last_update": last_update, "positions": []}
    result = format_state_brief(state, now=now)
    assert "EA" in result
    assert "⚠" in result


def test_format_state_brief_missing():
    result = format_state_brief({})
    assert result == "EA ✗"
