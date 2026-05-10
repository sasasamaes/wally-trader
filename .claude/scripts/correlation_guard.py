#!/usr/bin/env python3
"""correlation_guard.py — Pre-entry correlation risk check.

Reads existing open positions for the active profile (from signals_received.csv
filtered to outcome=pendiente) and computes correlation between them and a
proposed new entry. If correlation > threshold AND same direction, BLOCK
the new entry to prevent concentrated risk.

Usage:
  python3 .claude/scripts/correlation_guard.py --symbol TONUSDT --side SHORT
  python3 .claude/scripts/correlation_guard.py --symbol BTCUSDT --side LONG --threshold 0.7

Exit codes:
  0 = OK to enter (no concentrated risk)
  1 = BLOCK (correlation breach)
  2 = WARN (close to threshold but allowed)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Auto-inject wally_core
ROOT = Path(__file__).resolve().parent.parent.parent
SHARED = ROOT / "shared/wally_core/src"
if SHARED.exists() and str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from wally_core.portfolio import correlation_matrix  # noqa: E402

DEFAULT_THRESHOLD = 0.75


def get_active_profile() -> str:
    """Read active profile from .claude/active_profile."""
    profile_file = ROOT / ".claude" / "active_profile"
    if not profile_file.exists():
        return "retail"
    return profile_file.read_text().strip().split()[0]


def get_open_positions(profile: str, max_age_hours: int = 24) -> list[dict[str, Any]]:
    """Read open positions from signals_received.csv.

    Treats a row as OPEN if (a) no exit_price AND no outcome AND
    (b) the entry timestamp is within max_age_hours. Older rows without
    exit data are treated as stale (likely missed log close).
    """
    csv_path = ROOT / ".claude" / "profiles" / profile / "memory" / "signals_received.csv"
    if not csv_path.exists():
        return []

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    now = datetime.now(timezone.utc)
    cutoff_seconds = max_age_hours * 3600

    open_positions = []
    for row in rows:
        outcome = (row.get("hypothetical_outcome") or "").strip()
        exit_price = (row.get("exit_price") or "").strip()
        if exit_price or outcome:
            continue

        # Parse date+time to filter stale rows
        date_str = (row.get("date") or "").strip()
        time_str = (row.get("time") or "").strip()
        if date_str and time_str:
            try:
                ts = datetime.fromisoformat(f"{date_str}T{time_str}:00").replace(tzinfo=timezone(__import__('datetime').timedelta(hours=-6)))
                age = (now - ts.astimezone(timezone.utc)).total_seconds()
                if age > cutoff_seconds:
                    continue  # Stale
            except Exception:
                pass  # Date unparseable; include conservatively

        symbol = (row.get("symbol") or "").strip()
        side = (row.get("side") or "").strip().upper()
        if symbol and side:
            clean_symbol = symbol.replace(".P", "")
            open_positions.append({
                "symbol": clean_symbol,
                "side": side,
                "entry": row.get("entry"),
                "raw_symbol": symbol,
                "date": date_str,
                "time": time_str,
            })
    return open_positions


def assess_correlation(
    new_symbol: str,
    new_side: str,
    profile: str,
    threshold: float = DEFAULT_THRESHOLD,
    lookback_days: int = 30,
) -> dict[str, Any]:
    """Assess if new position would create concentrated correlated risk."""
    new_symbol = new_symbol.replace(".P", "").upper()
    new_side = new_side.upper()

    open_positions = get_open_positions(profile)

    if not open_positions:
        return {
            "verdict": "OK",
            "reason": "No existing open positions — no correlation risk.",
            "open_count": 0,
            "checks": [],
        }

    # Build symbol list for correlation matrix
    all_symbols = list({p["symbol"] for p in open_positions} | {new_symbol})

    if len(all_symbols) < 2:
        # Same symbol → not really correlation, would be averaging
        return {
            "verdict": "WARN",
            "reason": f"Already have open position in {new_symbol} — this would be averaging up/down.",
            "open_count": len(open_positions),
            "checks": [{"existing": new_symbol, "new": new_symbol, "issue": "same_symbol"}],
        }

    try:
        matrix = correlation_matrix(all_symbols, lookback_days=lookback_days)
    except Exception as e:
        return {
            "verdict": "WARN",
            "reason": f"Could not compute correlations: {e}. Allowing entry but advise caution.",
            "open_count": len(open_positions),
            "checks": [],
        }

    checks = []
    blocked = False
    warned = False

    for pos in open_positions:
        if pos["symbol"] == new_symbol:
            continue
        # Try both orderings of the tuple key
        corr = matrix.get((pos["symbol"], new_symbol))
        if corr is None:
            corr = matrix.get((new_symbol, pos["symbol"]))
        if corr is None:
            checks.append({
                "existing": pos["symbol"],
                "new": new_symbol,
                "correlation": None,
                "issue": "no_data",
            })
            continue

        same_direction = pos["side"] == new_side
        check = {
            "existing": pos["symbol"],
            "new": new_symbol,
            "correlation": round(corr, 3),
            "existing_side": pos["side"],
            "new_side": new_side,
            "same_direction": same_direction,
        }

        if abs(corr) > threshold and same_direction:
            check["issue"] = "high_correlation_same_direction"
            blocked = True
        elif abs(corr) > threshold * 0.85 and same_direction:
            check["issue"] = "moderate_correlation_same_direction"
            warned = True

        checks.append(check)

    if blocked:
        return {
            "verdict": "BLOCK",
            "reason": (
                f"Concentrated correlated risk: existing position(s) move together "
                f"with proposed {new_symbol} {new_side}. "
                f"Correlation > {threshold} + same direction = "
                f"effectively a doubled bet, not diversification."
            ),
            "open_count": len(open_positions),
            "threshold": threshold,
            "checks": checks,
        }
    if warned:
        return {
            "verdict": "WARN",
            "reason": (
                f"Moderate correlation with existing position. Proceeding allowed but "
                f"reduce size 30% to manage concentration."
            ),
            "open_count": len(open_positions),
            "threshold": threshold,
            "checks": checks,
        }
    return {
        "verdict": "OK",
        "reason": "Correlations within tolerance — diversified entry allowed.",
        "open_count": len(open_positions),
        "threshold": threshold,
        "checks": checks,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Pre-entry correlation risk guard")
    p.add_argument("--symbol", required=True, help="New entry symbol (e.g. BTCUSDT)")
    p.add_argument("--side", required=True, choices=["LONG", "SHORT", "long", "short"])
    p.add_argument("--profile", help="Profile name (default: active)")
    p.add_argument(
        "--threshold", type=float, default=DEFAULT_THRESHOLD,
        help=f"Correlation threshold for block (default {DEFAULT_THRESHOLD})",
    )
    p.add_argument("--lookback", type=int, default=30, help="Lookback days (default 30)")
    p.add_argument("--quick", action="store_true", help="One-line stderr summary")
    args = p.parse_args()

    profile = args.profile or get_active_profile()

    result = assess_correlation(
        new_symbol=args.symbol,
        new_side=args.side.upper(),
        profile=profile,
        threshold=args.threshold,
        lookback_days=args.lookback,
    )
    result["profile"] = profile
    result["checked_at"] = datetime.now(timezone.utc).isoformat()

    if args.quick:
        print(
            f"[corr-guard] {profile}/{args.symbol} {args.side.upper()}: "
            f"{result['verdict']} | {result['reason']}",
            file=sys.stderr,
        )

    print(json.dumps(result, indent=2))

    if result["verdict"] == "BLOCK":
        return 1
    if result["verdict"] == "WARN":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
