"""L1 — Log every system recommendation + user action + outcome correlation."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


@dataclass
class RecommendationEntry:
    entry_id: str
    timestamp: str
    agent: str                          # punk-watch-analyst, signal-validator, etc.
    recommendation: str                 # CUT, HOLD, GO, NO-GO, etc.
    rationale: str
    user_action: str = "pending"        # CUT, HOLD, OVERRIDE, etc.
    trade_id: Optional[str] = None
    outcome_24h_pnl: Optional[float] = None
    outcome_final_pnl: Optional[float] = None


def _log_path(profile: Optional[str] = None) -> Path:
    base = Path(os.environ.get("WALLY_PROFILES_DIR", ".claude/profiles"))
    folder = base / "_learning"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "recommendations.jsonl"


def log_recommendation(
    agent: str,
    recommendation: str,
    rationale: str,
    *,
    trade_id: Optional[str] = None,
    log_path: Optional[Path] = None,
) -> str:
    """Log a new recommendation. Returns entry_id."""
    entry_id = str(uuid.uuid4())[:8]
    entry = RecommendationEntry(
        entry_id=entry_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent=agent,
        recommendation=recommendation,
        rationale=rationale,
        user_action="pending",
        trade_id=trade_id,
    )
    path = log_path or _log_path()
    with open(path, "a") as f:
        f.write(json.dumps(asdict(entry)) + "\n")
    return entry_id


def _load_entries(log_path: Optional[Path] = None) -> list[dict]:
    path = log_path or _log_path()
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def _rewrite_entries(entries: list[dict], log_path: Optional[Path] = None) -> None:
    path = log_path or _log_path()
    with open(path, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def update_user_action(
    entry_id: str,
    action: str,
    *,
    log_path: Optional[Path] = None,
) -> None:
    """Update user_action on an existing entry."""
    entries = _load_entries(log_path)
    found = False
    for e in entries:
        if e.get("entry_id") == entry_id:
            e["user_action"] = action
            found = True
            break
    if not found:
        raise KeyError(f"entry_id {entry_id!r} not found")
    _rewrite_entries(entries, log_path)


def update_outcome(
    entry_id: str,
    pnl_24h: Optional[float],
    pnl_final: Optional[float],
    *,
    log_path: Optional[Path] = None,
) -> None:
    """Close out an entry with actual PnL numbers."""
    entries = _load_entries(log_path)
    found = False
    for e in entries:
        if e.get("entry_id") == entry_id:
            e["outcome_24h_pnl"] = pnl_24h
            e["outcome_final_pnl"] = pnl_final
            found = True
            break
    if not found:
        raise KeyError(f"entry_id {entry_id!r} not found")
    _rewrite_entries(entries, log_path)


def calibration_report(
    min_entries: int = 10,
    days: int = 30,
    *,
    log_path: Optional[Path] = None,
) -> dict:
    """Return calibration statistics for system recommendations vs user actions.

    Returns:
        n, system_correct_pct, user_override_correct_pct,
        avg_pnl_when_followed, avg_pnl_when_overridden
    """
    entries = _load_entries(log_path)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Filter by date and having outcome
    relevant = []
    for e in entries:
        try:
            ts = datetime.fromisoformat(e["timestamp"])
            if ts < cutoff:
                continue
        except (KeyError, ValueError):
            continue
        if e.get("outcome_final_pnl") is not None and e.get("user_action") not in ("pending", None):
            relevant.append(e)

    if len(relevant) < min_entries:
        return {
            "n": len(relevant),
            "min_entries_required": min_entries,
            "status": "insufficient_data",
        }

    followed = [e for e in relevant if e["user_action"] == e["recommendation"]]
    overridden = [e for e in relevant if e["user_action"] != e["recommendation"]]

    def _avg_pnl(lst: list[dict]) -> Optional[float]:
        pnls = [e["outcome_final_pnl"] for e in lst if e.get("outcome_final_pnl") is not None]
        return round(sum(pnls) / len(pnls), 2) if pnls else None

    def _correct_pct(lst: list[dict]) -> float:
        """'Correct' = positive PnL when recommendation was followed."""
        if not lst:
            return 0.0
        wins = [e for e in lst if (e.get("outcome_final_pnl") or 0) > 0]
        return round(len(wins) / len(lst) * 100, 1)

    return {
        "n": len(relevant),
        "days": days,
        "status": "ok",
        "system_correct_pct": _correct_pct(followed),
        "user_override_correct_pct": _correct_pct(overridden),
        "avg_pnl_when_followed": _avg_pnl(followed),
        "avg_pnl_when_overridden": _avg_pnl(overridden),
        "n_followed": len(followed),
        "n_overridden": len(overridden),
    }
