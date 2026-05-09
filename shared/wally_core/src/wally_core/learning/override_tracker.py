"""L8 — Track when user overrides system + outcome correlation."""
from __future__ import annotations

import json
import os
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


def _overrides_path(profiles_dir: str = ".claude/profiles") -> Path:
    p = Path(profiles_dir) / "_learning"
    p.mkdir(parents=True, exist_ok=True)
    return p / "overrides.jsonl"


def log_override(
    my_rec: str,
    user_action: str,
    trade_id: str,
    rationale: str = "",
    *,
    timestamp: Optional[str] = None,
    log_path: Optional[Path] = None,
    profiles_dir: str = ".claude/profiles",
) -> str:
    """Log an override event. Returns entry_id.

    This integrates with L1 — called when user_action != recommendation.
    """
    entry_id = str(uuid.uuid4())[:8]
    entry = {
        "entry_id": entry_id,
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "my_rec": my_rec,
        "user_action": user_action,
        "override_type": f"{my_rec}->{user_action}",
        "trade_id": trade_id,
        "rationale": rationale,
        "outcome_pnl": None,
        "outcome_resolved": False,
    }
    path = log_path or _overrides_path(profiles_dir)
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry_id


def update_override_outcome(
    entry_id: str,
    pnl: float,
    *,
    log_path: Optional[Path] = None,
    profiles_dir: str = ".claude/profiles",
) -> None:
    """Attach outcome PnL to an override entry."""
    path = log_path or _overrides_path(profiles_dir)
    if not path.exists():
        raise FileNotFoundError(f"Overrides log not found: {path}")

    entries = []
    found = False
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                if e.get("entry_id") == entry_id:
                    e["outcome_pnl"] = pnl
                    e["outcome_resolved"] = True
                    found = True
                entries.append(e)
            except json.JSONDecodeError:
                pass

    if not found:
        raise KeyError(f"entry_id {entry_id!r} not found in overrides log")

    with open(path, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def override_calibration(
    profile: str = "_learning",
    days: int = 90,
    *,
    log_path: Optional[Path] = None,
    profiles_dir: str = ".claude/profiles",
) -> dict:
    """Compute: when user overrode system, was outcome better?

    Bucket by override type: cut→hold, hold→cut, etc.
    Returns: 'user better than system in X scenarios'.
    """
    path = log_path or _overrides_path(profiles_dir)
    if not path.exists():
        return {"status": "no_data", "total_overrides": 0, "buckets": {}}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                # Date filter
                try:
                    ts = datetime.fromisoformat(e["timestamp"])
                    if ts < cutoff:
                        continue
                except (KeyError, ValueError):
                    pass
                if e.get("outcome_resolved"):
                    entries.append(e)
            except json.JSONDecodeError:
                pass

    if not entries:
        return {"status": "no_resolved_overrides", "total_overrides": 0, "buckets": {}}

    # Bucket by override_type
    buckets: dict[str, dict] = defaultdict(lambda: {"n": 0, "wins": 0, "total_pnl": 0.0})
    for e in entries:
        otype = e.get("override_type", "unknown")
        pnl = e.get("outcome_pnl") or 0
        buckets[otype]["n"] += 1
        if pnl > 0:
            buckets[otype]["wins"] += 1
        buckets[otype]["total_pnl"] += pnl

    # Compute per-bucket WR + avg
    bucket_summary = {}
    for otype, stats in buckets.items():
        n = stats["n"]
        wr = round(stats["wins"] / n * 100, 1) if n else 0
        avg_pnl = round(stats["total_pnl"] / n, 2) if n else 0
        bucket_summary[otype] = {
            "n": n,
            "wr": wr,
            "avg_pnl": avg_pnl,
        }

    # Overall user override performance
    all_pnls = [e.get("outcome_pnl") or 0 for e in entries]
    overall_win_pct = round(sum(1 for p in all_pnls if p > 0) / len(all_pnls) * 100, 1) if all_pnls else 0
    overall_avg = round(sum(all_pnls) / len(all_pnls), 2) if all_pnls else 0

    # Narrative
    best_buckets = [k for k, v in bucket_summary.items() if v["wr"] >= 60]
    worst_buckets = [k for k, v in bucket_summary.items() if v["wr"] < 40]

    narrative = []
    if best_buckets:
        narrative.append(f"User better than system in: {', '.join(best_buckets)}")
    if worst_buckets:
        narrative.append(f"User underperforms in overrides: {', '.join(worst_buckets)}")

    return {
        "status": "ok",
        "total_overrides": len(entries),
        "days": days,
        "overall_win_pct": overall_win_pct,
        "overall_avg_pnl": overall_avg,
        "buckets": bucket_summary,
        "narrative": narrative,
    }
