"""L7 — Retrain XGBoost when 25+ new closed trades are available.

If scripts/ml_system/supervised/train.py doesn't exist or has a different interface,
this module scaffolds the orchestration and logs the attempt.
TODO: wire to ml_system pipeline once train.py interface is confirmed.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


ML_TRAIN_SCRIPT = Path(os.environ.get("WALLY_ROOT", ".")) / "scripts" / "ml_system" / "supervised" / "train.py"
VENV_PYTHON = Path(os.environ.get("WALLY_ROOT", ".")) / "shared" / "wally_core" / ".venv" / "bin" / "python"


def _retrain_log_path(profile: str, profiles_dir: str = ".claude/profiles") -> Path:
    p = Path(profiles_dir) / profile / "memory" / "learning"
    p.mkdir(parents=True, exist_ok=True)
    return p / "ml_retrain_log.jsonl"


def _load_outcomes_count(profile: str, profiles_dir: str = ".claude/profiles") -> int:
    """Count closed outcomes in outcomes_v2.csv."""
    path = Path(profiles_dir) / profile / "memory" / "outcomes_v2.csv"
    if not path.exists():
        return 0
    import csv
    n = 0
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("pnl_usd") not in (None, "", "0"):
                n += 1
    return n


def _log_retrain_event(
    profile: str,
    event: str,
    details: dict,
    *,
    profiles_dir: str = ".claude/profiles",
) -> None:
    path = _retrain_log_path(profile, profiles_dir)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "profile": profile,
        **details,
    }
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _get_last_train_n(profile: str, profiles_dir: str = ".claude/profiles") -> int:
    """Get the trade count at last successful retrain."""
    path = _retrain_log_path(profile, profiles_dir)
    if not path.exists():
        return 0
    last_n = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("event") == "retrain_promoted":
                    last_n = entry.get("n_trades", last_n)
            except json.JSONDecodeError:
                pass
    return last_n


def should_retrain(
    profile: str,
    new_trade_threshold: int = 25,
    *,
    profiles_dir: str = ".claude/profiles",
    last_train_n: Optional[int] = None,
) -> bool:
    """Return True if enough new closed trades have accumulated since last retrain."""
    current_n = _load_outcomes_count(profile, profiles_dir)
    if last_train_n is None:
        last_train_n = _get_last_train_n(profile, profiles_dir)
    new_trades = current_n - last_train_n
    return new_trades >= new_trade_threshold


def retrain_and_validate(
    profile: str,
    *,
    profiles_dir: str = ".claude/profiles",
    force: bool = False,
    train_script: Optional[Path] = None,
    python_bin: Optional[Path] = None,
) -> dict:
    """Run train.py with cumulative data; cross-validate; promote if AUC improves by >=0.02.

    Returns dict with: status, promoted, old_auc, new_auc, n_trades, message.

    TODO: Full wire-in requires train.py to accept --profile arg and output JSON metrics.
    Current implementation: scaffold that invokes the script if it exists, else logs TODO.
    """
    n_trades = _load_outcomes_count(profile, profiles_dir)
    script = train_script or ML_TRAIN_SCRIPT
    py = python_bin or VENV_PYTHON

    if not script.exists():
        # Scaffold mode — train.py not yet available
        message = (
            f"TODO: {script} not found. "
            "Wire retrain_and_validate() to ml_system pipeline when train.py is ready. "
            f"Current closed trades: {n_trades}."
        )
        _log_retrain_event(
            profile,
            "retrain_skipped_no_script",
            {"n_trades": n_trades, "message": message},
            profiles_dir=profiles_dir,
        )
        return {
            "status": "scaffold_no_script",
            "promoted": False,
            "n_trades": n_trades,
            "message": message,
        }

    # Invoke train.py
    try:
        result = subprocess.run(
            [str(py), str(script), "--profile", profile, "--output-json"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            msg = f"train.py failed: {result.stderr[:500]}"
            _log_retrain_event(
                profile, "retrain_failed",
                {"n_trades": n_trades, "error": msg},
                profiles_dir=profiles_dir,
            )
            return {"status": "train_failed", "promoted": False, "n_trades": n_trades, "message": msg}

        # Parse JSON output from train.py
        try:
            metrics = json.loads(result.stdout)
        except json.JSONDecodeError:
            # Non-JSON output — treat as scaffold
            _log_retrain_event(
                profile, "retrain_no_json_output",
                {"n_trades": n_trades, "stdout": result.stdout[:200]},
                profiles_dir=profiles_dir,
            )
            return {
                "status": "scaffold_no_json",
                "promoted": False,
                "n_trades": n_trades,
                "message": "train.py ran but did not return JSON metrics. TODO: add --output-json flag.",
            }

        new_auc = metrics.get("auc", 0)
        old_auc = metrics.get("baseline_auc", 0)
        promoted = new_auc >= old_auc + 0.02

        event = "retrain_promoted" if promoted else "retrain_rejected"
        _log_retrain_event(
            profile, event,
            {"n_trades": n_trades, "old_auc": old_auc, "new_auc": new_auc, "promoted": promoted},
            profiles_dir=profiles_dir,
        )

        return {
            "status": "ok",
            "promoted": promoted,
            "old_auc": old_auc,
            "new_auc": new_auc,
            "n_trades": n_trades,
            "message": f"{'Promoted' if promoted else 'Rejected'}: new_auc={new_auc:.3f} vs old_auc={old_auc:.3f}",
        }

    except subprocess.TimeoutExpired:
        msg = "train.py timed out after 300s"
        _log_retrain_event(profile, "retrain_timeout", {"n_trades": n_trades}, profiles_dir=profiles_dir)
        return {"status": "timeout", "promoted": False, "n_trades": n_trades, "message": msg}
    except Exception as e:
        msg = f"Unexpected error: {e}"
        _log_retrain_event(profile, "retrain_error", {"n_trades": n_trades, "error": str(e)}, profiles_dir=profiles_dir)
        return {"status": "error", "promoted": False, "n_trades": n_trades, "message": msg}
