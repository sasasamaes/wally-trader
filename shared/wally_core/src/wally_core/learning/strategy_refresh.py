"""L4 — Auto-refresh regime_mapping.json based on recent live outcomes."""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


REGIME_MAPPING_PATH = Path(os.environ.get("WALLY_SCRIPTS_DIR", ".claude/scripts")) / "regime_mapping.json"


def _load_outcomes(profile: str, profiles_dir: str = ".claude/profiles") -> list[dict]:
    path = Path(profiles_dir) / profile / "memory" / "outcomes_v2.csv"
    if not path.exists():
        return []
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _load_regime_mapping(mapping_path: Optional[Path] = None) -> dict:
    path = mapping_path or REGIME_MAPPING_PATH
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def refresh_strategy_mapping(
    profile: str,
    days: int = 60,
    threshold_drift: float = 10.0,
    *,
    profiles_dir: str = ".claude/profiles",
    mapping_path: Optional[Path] = None,
    dry_run: bool = False,
) -> dict:
    """Re-compute (regime, strategy) WR from last N days of actual trades.

    For each (regime, strategy) cell: if WR drifted > threshold_drift pp from
    prior mapping → flag for update.

    Returns: {n_cells_updated, changes: list, regime_stats: dict}.
    """
    outcomes = _load_outcomes(profile, profiles_dir)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Filter to recent trades with outcome
    recent = []
    for row in outcomes:
        close_raw = row.get("close_time_utc", "")
        if close_raw:
            try:
                close_time = datetime.fromisoformat(close_raw.replace("Z", "+00:00"))
                if close_time < cutoff:
                    continue
            except ValueError:
                pass
        try:
            pnl = float(row.get("pnl_usd") or 0)
        except (ValueError, TypeError):
            continue
        recent.append(row)

    if not recent:
        return {"n_cells_updated": 0, "changes": [], "status": "no_recent_trades"}

    # Compute WR per regime
    regime_stats: dict[str, dict] = defaultdict(lambda: {"wins": 0, "total": 0, "avg_pnl": 0.0, "pnls": []})
    for row in recent:
        regime = row.get("regime_at_entry", "UNKNOWN") or "UNKNOWN"
        try:
            pnl = float(row.get("pnl_usd") or 0)
        except (ValueError, TypeError):
            pnl = 0.0
        regime_stats[regime]["total"] += 1
        if pnl > 0:
            regime_stats[regime]["wins"] += 1
        regime_stats[regime]["pnls"].append(pnl)

    for regime, stats in regime_stats.items():
        pnls = stats["pnls"]
        stats["wr"] = round(stats["wins"] / stats["total"] * 100, 1) if stats["total"] else 0
        stats["avg_pnl"] = round(sum(pnls) / len(pnls), 2) if pnls else 0
        del stats["pnls"]  # Remove raw list for cleaner output

    # Compare against current regime_mapping.json
    current_mapping = _load_regime_mapping(mapping_path)
    current_wr_map = {}
    if "regime_strategy_map" in current_mapping:
        for entry in current_mapping.get("regime_strategy_map", []):
            regime_key = entry.get("regime", "")
            current_wr = entry.get("backtest_wr", None)
            if regime_key and current_wr is not None:
                current_wr_map[regime_key] = float(current_wr)

    changes = []
    for regime, stats in regime_stats.items():
        live_wr = stats["wr"]
        prior_wr = current_wr_map.get(regime, None)
        if prior_wr is None:
            changes.append({
                "regime": regime,
                "type": "new_data",
                "live_wr": live_wr,
                "prior_wr": None,
                "drift": None,
                "n": stats["total"],
            })
        elif abs(live_wr - prior_wr) > threshold_drift:
            changes.append({
                "regime": regime,
                "type": "drift_detected",
                "live_wr": live_wr,
                "prior_wr": prior_wr,
                "drift": round(live_wr - prior_wr, 1),
                "n": stats["total"],
            })

    # Optionally apply updates to mapping file
    n_cells_updated = 0
    if not dry_run and changes and mapping_path is not None:
        # Write updated stats to mapping (create learning_stats sub-key)
        if isinstance(current_mapping, dict):
            current_mapping["learning_stats"] = {
                "last_refresh": datetime.now(timezone.utc).isoformat(),
                "profile": profile,
                "days": days,
                "regime_live_wr": {r: s["wr"] for r, s in regime_stats.items()},
            }
            mapping_path.write_text(json.dumps(current_mapping, indent=2))
            n_cells_updated = len(changes)

    return {
        "n_cells_updated": n_cells_updated,
        "changes": changes,
        "regime_stats": dict(regime_stats),
        "status": "ok",
        "n_trades": len(recent),
        "days": days,
        "threshold_drift": threshold_drift,
    }
