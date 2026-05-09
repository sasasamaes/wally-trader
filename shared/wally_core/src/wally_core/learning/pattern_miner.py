"""L2 — Mine winning/losing patterns from outcomes_v2.csv + signals_received.csv."""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


def _asset_type(symbol: str) -> str:
    """Classify asset by liquidity tier."""
    symbol = symbol.upper().replace(".P", "").replace("USDT", "").replace("USD", "")
    major = {"BTC", "ETH", "SOL", "MSTR"}
    mid = {"AVAX", "ADA", "DOGE", "LINK", "DOT", "UNI", "MATIC", "POL", "XRP", "LTC",
           "ATOM", "XLM", "NEAR", "WIF", "SUI", "TRX", "TON", "INJ", "HBAR", "TIA"}
    if symbol in major:
        return "major"
    if symbol in mid:
        return "mid"
    return "alt"


def _hour_bucket(hour: int) -> str:
    """Bucket CR hour into 4 windows."""
    if hour < 6:
        return "00-06"
    elif hour < 12:
        return "06-12"
    elif hour < 18:
        return "12-18"
    else:
        return "18-24"


def _load_outcomes(profile: str, profiles_dir: str = ".claude/profiles") -> list[dict]:
    """Load outcomes_v2.csv for a profile."""
    path = Path(profiles_dir) / profile / "memory" / "outcomes_v2.csv"
    if not path.exists():
        return []
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def mine_patterns(
    profile: str,
    days: int = 90,
    min_n: int = 5,
    *,
    profiles_dir: str = ".claude/profiles",
) -> dict:
    """For each (regime, asset_type, hour_bucket, day_of_week, side) combo with n>=min_n,
    compute WR + avg_pnl. Return top 10 winning + top 10 losing patterns.

    Returns dict with keys: 'winning', 'losing', 'total_trades', 'combos_analyzed'.
    """
    rows = _load_outcomes(profile, profiles_dir)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Group trades by combo key
    combos: dict[tuple, list[float]] = defaultdict(list)

    for row in rows:
        # Parse close time for date filter
        close_time_raw = row.get("close_time_utc", "")
        if close_time_raw:
            try:
                close_time = datetime.fromisoformat(close_time_raw.replace("Z", "+00:00"))
                if close_time < cutoff:
                    continue
            except ValueError:
                pass

        # Extract open time for hour + day-of-week
        open_time_raw = row.get("open_time_utc", "")
        hour_bucket = "unknown"
        day_of_week = "unknown"
        if open_time_raw:
            try:
                open_time = datetime.fromisoformat(open_time_raw.replace("Z", "+00:00"))
                # Convert UTC → CR (UTC-6)
                cr_time = open_time - timedelta(hours=6)
                hour_bucket = _hour_bucket(cr_time.hour)
                day_of_week = cr_time.strftime("%a")  # Mon, Tue, ...
            except ValueError:
                pass

        symbol = row.get("symbol", "")
        asset_type = _asset_type(symbol)
        regime = row.get("regime_at_entry", "UNKNOWN") or "UNKNOWN"
        side = row.get("side", "UNKNOWN") or "UNKNOWN"

        try:
            pnl = float(row.get("pnl_usd") or 0)
        except (ValueError, TypeError):
            continue

        key = (regime, asset_type, hour_bucket, day_of_week, side)
        combos[key].append(pnl)

    # Build pattern stats
    patterns = []
    for key, pnls in combos.items():
        if len(pnls) < min_n:
            continue
        wins = [p for p in pnls if p > 0]
        wr = round(len(wins) / len(pnls) * 100, 1)
        avg_pnl = round(sum(pnls) / len(pnls), 2)
        regime, asset_type, hour_bucket, day_of_week, side = key
        patterns.append({
            "regime": regime,
            "asset_type": asset_type,
            "hour_bucket": hour_bucket,
            "day_of_week": day_of_week,
            "side": side,
            "n": len(pnls),
            "wr": wr,
            "avg_pnl": avg_pnl,
        })

    patterns_sorted_by_wr = sorted(patterns, key=lambda x: x["wr"])
    losing = patterns_sorted_by_wr[:10]
    winning = patterns_sorted_by_wr[-10:][::-1]  # highest WR first

    return {
        "winning": winning,
        "losing": losing,
        "total_trades": len(rows),
        "combos_analyzed": len(combos),
        "min_n": min_n,
        "days": days,
    }


def pattern_to_recommendation(patterns: dict) -> list[str]:
    """Convert mined patterns to actionable suggestions."""
    suggestions = []

    for p in patterns.get("winning", []):
        suggestions.append(
            f"PREFER: {p['side']} en {p['asset_type']} / {p['regime']} "
            f"hora {p['hour_bucket']} ({p['wr']:.0f}% WR over n={p['n']})"
        )

    for p in patterns.get("losing", []):
        suggestions.append(
            f"AVOID: {p['side']} en {p['asset_type']} / {p['regime']} "
            f"hora {p['hour_bucket']} ({p['wr']:.0f}% WR over n={p['n']})"
        )

    return suggestions
