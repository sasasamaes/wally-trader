"""Join Polymarket snapshots with BTC OHLCV for research.

Reads snapshots.jsonl and a BTC OHLCV CSV (ts,open,high,low,close,volume).
Returns aligned tuples of (pm_prob, btc_close_t, btc_close_t+forward).
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from polymarket import config


def _parse_ts(s: str) -> datetime:
    s = s.replace("Z", "+00:00") if s.endswith("Z") else s
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_snapshots_for_market(slug: str, snapshots_path: Path | None = None) -> list[tuple[datetime, float]]:
    """Return [(timestamp, prob_yes)] sorted by ts ascending."""
    p = snapshots_path or config.SNAPSHOTS_PATH
    if not p.exists():
        return []
    out: list[tuple[datetime, float]] = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("slug") != slug:
            continue
        out.append((_parse_ts(row["ts"]), float(row["prob"])))
    return sorted(out, key=lambda t: t[0])


def _load_btc(path: Path) -> list[tuple[datetime, float]]:
    rows: list[tuple[datetime, float]] = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                rows.append((_parse_ts(r["ts"]), float(r["close"])))
            except (KeyError, ValueError):
                continue
    return sorted(rows, key=lambda t: t[0])


def _btc_close_at_or_before(btc: list[tuple[datetime, float]], target: datetime) -> float | None:
    """Find the latest BTC close at or before target (within 1h tolerance)."""
    best = None
    for ts, close in btc:
        if ts > target:
            break
        if (target - ts) <= timedelta(hours=1):
            best = close
    return best


def align_with_btc(
    *,
    slug: str,
    btc_csv: Path,
    forward_window: timedelta,
    snapshots_path: Path | None = None,
) -> list[tuple[float, float, float]]:
    """Align PM probability snapshots with BTC close at the snapshot time and at +forward_window.

    Returns [(pm_prob, btc_t, btc_t+forward)].
    Drops rows where either BTC value cannot be resolved within tolerance.
    """
    pm_series = load_snapshots_for_market(slug, snapshots_path)
    btc = _load_btc(btc_csv)
    if not pm_series or not btc:
        return []

    aligned: list[tuple[float, float, float]] = []
    for ts, prob in pm_series:
        c0 = _btc_close_at_or_before(btc, ts)
        c1 = _btc_close_at_or_before(btc, ts + forward_window)
        if c0 is None or c1 is None:
            continue
        # Require c1's matched timestamp to actually be >= ts + window - tolerance
        # (we approximate by checking strict difference)
        if c1 == c0 and ts + forward_window > btc[-1][0]:
            continue
        aligned.append((prob, c0, c1))
    return aligned
