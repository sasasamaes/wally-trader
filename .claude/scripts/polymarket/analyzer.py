"""Polymarket analyzer — load snapshots, compute deltas, composite score, report.

Usage (CLI):
    python -m polymarket.analyzer [--json]

Imports:
    from polymarket.analyzer import load_snapshots, compute_deltas, composite, report
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from polymarket import config

# Required keys every snapshot row must carry.
_REQUIRED_KEYS = {"ts", "id", "slug", "prob", "vol_24h", "last_trade"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_ts(s: str) -> datetime:
    """Parse an ISO-8601 timestamp string to an aware UTC datetime.

    Handles trailing 'Z' and '+00:00' suffixes.
    """
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_snapshots(path: Path | str | None = None) -> list[dict]:
    """Load JSONL snapshots from *path* (defaults to config.SNAPSHOTS_PATH).

    Silently skips:
    - Lines that are not valid JSON
    - JSON objects missing any of the required keys
    """
    if path is None:
        path = config.SNAPSHOTS_PATH
    path = Path(path)

    rows: list[dict] = []
    if not path.exists():
        return rows

    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            if not _REQUIRED_KEYS.issubset(obj.keys()):
                continue
            rows.append(obj)

    return rows


def compute_deltas(
    snapshots_for_market: list[dict],
    *,
    now: datetime,
) -> dict[str, Any]:
    """Compute probability deltas for a single market.

    Parameters
    ----------
    snapshots_for_market:
        All snapshot rows for one market, in any order.
    now:
        Reference timestamp (timezone-aware UTC).

    Returns
    -------
    dict with keys:
        slug        - market slug (from latest snapshot)
        prob_now    - latest probability
        delta_1h    - change vs 1 h ago  (None if no snapshot in window)
        delta_24h   - change vs 24 h ago (None if no snapshot in window)
        delta_7d    - change vs 7 d ago  (None if no snapshot in window)
    """
    if not snapshots_for_market:
        return {"slug": None, "prob_now": None, "delta_1h": None,
                "delta_24h": None, "delta_7d": None}

    # Sort ascending by timestamp
    snaps = sorted(snapshots_for_market, key=lambda s: _parse_ts(s["ts"]))

    # Latest snapshot is the most recent
    latest = snaps[-1]
    prob_now: float = float(latest["prob"])
    slug: str = latest["slug"]

    def at_lookback(delta: timedelta, tolerance: timedelta) -> float | None:
        """Return prob of the snapshot closest to (now - delta), within tolerance."""
        target = now - delta
        best: dict | None = None
        best_diff: float = float("inf")
        for snap in snaps:
            ts = _parse_ts(snap["ts"])
            diff = abs((ts - target).total_seconds())
            if diff <= tolerance.total_seconds() and diff < best_diff:
                best_diff = diff
                best = snap
        if best is None:
            return None
        return float(best["prob"])

    prob_1h = at_lookback(timedelta(hours=1), timedelta(minutes=30))
    prob_24h = at_lookback(timedelta(hours=24), timedelta(hours=2))
    prob_7d = at_lookback(timedelta(days=7), timedelta(hours=24))

    return {
        "slug": slug,
        "prob_now": prob_now,
        "delta_1h": (prob_now - prob_1h) if prob_1h is not None else None,
        "delta_24h": (prob_now - prob_24h) if prob_24h is not None else None,
        "delta_7d": (prob_now - prob_7d) if prob_7d is not None else None,
    }


def composite(per_market: dict[str, dict]) -> float | None:
    """Compute the composite macro sentiment score.

    Formula:
        score = Σ (prob_now - 0.5) × weight(slug)  /  Σ |weight(slug)|  × 200

    Returns None if no market has a recognised weight (total_weight == 0).

    Parameters
    ----------
    per_market:
        Mapping of market_id → result dict from compute_deltas (must have
        keys ``slug`` and ``prob_now``).
    """
    numerator = 0.0
    total_weight = 0.0

    for data in per_market.values():
        slug = data.get("slug")
        prob = data.get("prob_now")
        if slug is None or prob is None:
            continue
        weight = config.match_weight(slug)
        if weight is None:
            continue
        numerator += (float(prob) - 0.5) * weight
        total_weight += abs(weight)

    if total_weight == 0.0:
        return None

    return (numerator / total_weight) * 200.0


def report(
    *,
    snapshots_path: Path | str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a full report dict.

    Returns
    -------
    {
        "status":    "FRESH" | "STALE" | "NO_DATA",
        "composite": float | None,
        "bucket":    str | None,
        "as_of":     ISO string,
        "markets":   list[dict],   # one entry per tracked market
    }
    """
    if now is None:
        now = datetime.now(tz=timezone.utc)

    all_snaps = load_snapshots(snapshots_path)

    if not all_snaps:
        return {
            "status": "NO_DATA",
            "composite": None,
            "bucket": None,
            "as_of": now.isoformat(),
            "markets": [],
        }

    # Determine freshness: check the most recent snapshot timestamp globally
    latest_ts = max(_parse_ts(s["ts"]) for s in all_snaps)
    age_seconds = (now - latest_ts).total_seconds()
    status = "FRESH" if age_seconds <= config.STALE_AFTER_SECONDS else "STALE"

    # Group by market id
    by_id: dict[str, list[dict]] = {}
    for snap in all_snaps:
        by_id.setdefault(snap["id"], []).append(snap)

    per_market: dict[str, dict] = {}
    for market_id, snaps in by_id.items():
        per_market[market_id] = compute_deltas(snaps, now=now)

    comp = composite(per_market)
    bucket = config.bucket_for(comp) if comp is not None else None

    markets_list = [
        {"id": mid, **data} for mid, data in per_market.items()
    ]

    return {
        "status": status,
        "composite": comp,
        "bucket": bucket,
        "as_of": now.isoformat(),
        "markets": markets_list,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Polymarket macro sentiment analyzer."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of human-readable text.",
    )
    args = parser.parse_args(argv)

    result = report()

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    status = result["status"]
    comp = result["composite"]
    bucket = result["bucket"]
    as_of = result["as_of"]

    print(f"[Polymarket Macro Sentiment] status={status}  as_of={as_of}")
    if comp is not None:
        print(f"  Composite: {comp:+.1f}  Bucket: {bucket}")
    else:
        print("  Composite: N/A (no mapped markets)")

    for mkt in result["markets"]:
        slug = mkt.get("slug", mkt["id"])
        p = mkt.get("prob_now")
        d1 = mkt.get("delta_1h")
        d24 = mkt.get("delta_24h")
        d7 = mkt.get("delta_7d")
        parts = [f"  {slug}: prob={p:.2f}" if p is not None else f"  {slug}: prob=N/A"]
        if d1 is not None:
            parts.append(f"Δ1h={d1:+.3f}")
        if d24 is not None:
            parts.append(f"Δ24h={d24:+.3f}")
        if d7 is not None:
            parts.append(f"Δ7d={d7:+.3f}")
        print("  ".join(parts))


if __name__ == "__main__":
    main()
