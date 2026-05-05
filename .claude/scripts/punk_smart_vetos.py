#!/usr/bin/env python3
"""punk_smart_vetos — 6 veto functions for /punk-smart v2.

Each veto: (setup, ctx) → VetoResult(passed: bool, reason: str, source: str).
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import punk_smart_state as state

SCRIPTS_DIR = Path(__file__).resolve().parent


@dataclass
class VetoResult:
    name: str
    passed: bool
    reason: str
    source: str = ""


def _macro_check() -> dict:
    """Run macro_gate.py --check-now and return parsed JSON.

    Indirected via a function so tests can monkeypatch.
    """
    venv_py = SCRIPTS_DIR / ".venv" / "bin" / "python"
    py = str(venv_py) if venv_py.exists() else sys.executable
    try:
        out = subprocess.check_output(
            [py, str(SCRIPTS_DIR / "macro_gate.py"), "--check-now"],
            timeout=10, stderr=subprocess.DEVNULL)
        return json.loads(out)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            json.JSONDecodeError):
        return {"blocked": False, "reason": None}


def veto_macro(setup: dict) -> VetoResult:
    chk = _macro_check()
    if chk.get("blocked"):
        return VetoResult("macro", False, chk.get("reason", "macro event"),
                          source="macro_gate")
    return VetoResult("macro", True, "clear", source="macro_gate")


def veto_blacklist(setup: dict, now, memory_dir=None) -> VetoResult:
    asset = setup["asset"]
    if state.is_blacklisted(asset, now, memory_dir=memory_dir):
        return VetoResult("blacklist", False,
                          f"{asset} blacklisted (2 SL streak)",
                          source="asset_sl_streaks.json")
    return VetoResult("blacklist", True, "clean", source="asset_sl_streaks.json")


def veto_correlation(setup: dict, memory_dir=None) -> VetoResult:
    asset = setup["asset"]
    side = setup["side"].upper()
    bucket = state.bucket_of(asset)
    if bucket is None:
        return VetoResult("correlation", True,
                          f"{asset} unbucketed — no correlation check",
                          source="signals_received.csv")
    open_pos = state.open_positions(memory_dir=memory_dir)
    for p in open_pos:
        if p["bucket"] == bucket and p["side"] == side and p["asset"] != asset:
            return VetoResult(
                "correlation", False,
                f"{p['asset']} {side} already open in {bucket} bucket",
                source="signals_received.csv")
    return VetoResult("correlation", True, "no conflict",
                      source="signals_received.csv")
