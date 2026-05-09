"""L6 — Auto-tighten filters when calibration drift sustained."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _state_path(profile: str, profiles_dir: str = ".claude/profiles") -> Path:
    p = Path(profiles_dir) / profile / "memory" / "learning"
    p.mkdir(parents=True, exist_ok=True)
    return p / "tightening_state.json"


def _load_state(profile: str, profiles_dir: str = ".claude/profiles") -> dict:
    path = _state_path(profile, profiles_dir)
    if not path.exists():
        return {
            "level": 0,
            "active": False,
            "alert_streak": 0,
            "last_updated": None,
            "composite_threshold_bump": 0,
            "confluence_requirement_bump": 0,
        }
    try:
        return json.loads(path.read_text())
    except Exception:
        return {
            "level": 0,
            "active": False,
            "alert_streak": 0,
            "last_updated": None,
            "composite_threshold_bump": 0,
            "confluence_requirement_bump": 0,
        }


def _save_state(state: dict, profile: str, profiles_dir: str = ".claude/profiles") -> None:
    path = _state_path(profile, profiles_dir)
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(state, indent=2))


def _load_calibration_history(profile: str, profiles_dir: str = ".claude/profiles") -> list[dict]:
    """Load calibration history from journal or outcomes. Looks for severity field."""
    # Try to read from a calibration_history.jsonl if it exists
    p = Path(profiles_dir) / profile / "memory" / "learning" / "calibration_history.jsonl"
    if not p.exists():
        return []
    entries = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def append_calibration_check(
    profile: str,
    severity: str,
    details: Optional[dict] = None,
    *,
    profiles_dir: str = ".claude/profiles",
) -> None:
    """Append a calibration check result to history log."""
    p = Path(profiles_dir) / profile / "memory" / "learning"
    p.mkdir(parents=True, exist_ok=True)
    log_path = p / "calibration_history.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "severity": severity,
        "details": details or {},
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def check_drift_streak(
    profile: str,
    alert_days_threshold: int = 7,
    *,
    profiles_dir: str = ".claude/profiles",
) -> dict:
    """Check if ALERT severity has persisted for N+ consecutive entries.

    Returns dict with: alert_streak, threshold, should_tighten, current_level.
    """
    history = _load_calibration_history(profile, profiles_dir)

    if not history:
        return {
            "alert_streak": 0,
            "threshold": alert_days_threshold,
            "should_tighten": False,
            "current_level": 0,
            "status": "no_history",
        }

    # Count consecutive ALERT entries from the end
    streak = 0
    for entry in reversed(history):
        if entry.get("severity") == "ALERT":
            streak += 1
        else:
            break

    state = _load_state(profile, profiles_dir)
    current_level = state.get("level", 0)

    return {
        "alert_streak": streak,
        "threshold": alert_days_threshold,
        "should_tighten": streak >= alert_days_threshold,
        "current_level": current_level,
        "status": "ok",
    }


def apply_tightening(
    profile: str,
    level: int,
    *,
    profiles_dir: str = ".claude/profiles",
) -> None:
    """Apply tightening at given level.

    Level 1: composite score threshold +5pts.
    Level 2: require +1 confluence.
    """
    state = _load_state(profile, profiles_dir)

    if level == 1:
        state["composite_threshold_bump"] = 5
        state["confluence_requirement_bump"] = 0
        state["active"] = True
        state["level"] = 1
    elif level == 2:
        state["composite_threshold_bump"] = 5
        state["confluence_requirement_bump"] = 1
        state["active"] = True
        state["level"] = 2
    else:
        # Level 0 = no tightening
        state["composite_threshold_bump"] = 0
        state["confluence_requirement_bump"] = 0
        state["active"] = False
        state["level"] = 0

    _save_state(state, profile, profiles_dir)


def relax_when_resolved(
    profile: str,
    *,
    profiles_dir: str = ".claude/profiles",
) -> dict:
    """When drift returns to OK → relax tightening back to level 0.

    Returns {relaxed: bool, previous_level: int}.
    """
    state = _load_state(profile, profiles_dir)
    history = _load_calibration_history(profile, profiles_dir)

    if not history:
        return {"relaxed": False, "reason": "no_history", "previous_level": state.get("level", 0)}

    # Check if latest entry is OK or WARN (no longer ALERT)
    latest = history[-1] if history else {}
    latest_severity = latest.get("severity", "")

    if latest_severity in ("OK", "WARN") and state.get("active", False):
        previous_level = state.get("level", 0)
        apply_tightening(profile, 0, profiles_dir=profiles_dir)
        return {"relaxed": True, "previous_level": previous_level}

    return {"relaxed": False, "previous_level": state.get("level", 0), "latest_severity": latest_severity}


def get_current_tightening(
    profile: str,
    *,
    profiles_dir: str = ".claude/profiles",
) -> dict:
    """Get current tightening state for use by composite score or signal validator."""
    state = _load_state(profile, profiles_dir)
    return {
        "active": state.get("active", False),
        "level": state.get("level", 0),
        "composite_threshold_bump": state.get("composite_threshold_bump", 0),
        "confluence_requirement_bump": state.get("confluence_requirement_bump", 0),
    }
