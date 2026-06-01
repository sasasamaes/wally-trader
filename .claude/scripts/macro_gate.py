#!/usr/bin/env python3
"""macro_gate.py — read-only CLI for the macro events cache.
Delegates cache loading to wally_core.macro (zero behavior change).

Subcommands:
  --check-now           : is "right now" inside ±30 min of a high-impact event?
  --check-day YYYY-MM-DD: list events on that date.
  --next-events --days N: list events in the next N days.

All output is JSON to stdout. Errors to stderr. Exit 0 unless arg parsing fails.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Auto-inject wally_core from worktree (no venv activation required)
_SHARED = Path(__file__).resolve().parent.parent.parent / "shared/wally_core/src"
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from wally_core.macro import _load_cache as _wc_load_cache, CR_OFFSET, STALE_HOURS  # noqa: E402

DEFAULT_CACHE = Path(__file__).parent.parent / "cache" / "macro_events.json"
WINDOW_MINUTES = 30


def load_cache(path: Path) -> dict[str, Any] | None:
    """Load macro events cache from `path`, with stderr diagnostics on error."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"macro_gate: malformed cache: {e}", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        print(f"macro_gate: cache root is {type(data).__name__}, expected dict",
              file=sys.stderr)
        return None
    return data


def parse_now(arg: str | None) -> datetime:
    if arg:
        dt = datetime.fromisoformat(arg)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=CR_OFFSET)
        return dt
    return datetime.now(CR_OFFSET)


def event_datetime(ev: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(f"{ev['date']}T{ev['time_cr']}:00-06:00")


def is_stale(cache: dict[str, Any], now: datetime) -> bool:
    fetched = datetime.fromisoformat(cache["fetched_at"])
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=CR_OFFSET)
    return (now - fetched) > timedelta(hours=STALE_HOURS)


def check_now(cache: dict[str, Any] | None, now: datetime) -> dict[str, Any]:
    if cache is None:
        return {"blocked": False, "reason": "no_cache", "stale": True}
    high_events = [e for e in cache["events"] if e.get("impact") == "high"]
    for ev in high_events:
        ev_dt = event_datetime(ev)
        delta_min = abs((ev_dt - now).total_seconds()) / 60
        if delta_min <= WINDOW_MINUTES:
            return {
                "blocked": True,
                "reason": f"{ev['name']} at {ev['time_cr']} CR ({ev['country']})",
                "event": ev,
                "delta_minutes": int(delta_min),
                "stale": is_stale(cache, now),
            }
    return {"blocked": False, "reason": None, "stale": is_stale(cache, now)}


def check_day(cache: dict[str, Any] | None, day: str, now: datetime | None = None) -> dict[str, Any]:
    if cache is None:
        return {"events": [], "stale": True, "reason": "no_cache"}
    events = [e for e in cache["events"] if e["date"] == day]
    now = now or datetime.now(CR_OFFSET)
    return {"events": events, "stale": is_stale(cache, now)}


def next_events(cache: dict[str, Any] | None, now: datetime, days: int) -> dict[str, Any]:
    if cache is None:
        return {"events": [], "stale": True, "reason": "no_cache"}
    horizon = now + timedelta(days=days)
    upcoming = []
    for ev in cache["events"]:
        ev_dt = event_datetime(ev)
        if now <= ev_dt <= horizon:
            upcoming.append(ev)
    upcoming.sort(key=lambda e: event_datetime(e))
    return {"events": upcoming, "stale": is_stale(cache, now)}


WARN_HOURS = 4


def _event_payload(ev: dict, delta_min: float) -> dict:
    return {
        "name": ev["name"],
        "country": ev.get("country", "?"),
        "datetime_cr": f"{ev['date']}T{ev['time_cr']}:00-06:00",
        "hours_until": round(delta_min / 60.0, 2),
    }


def check_tier(cache: dict | None, now: datetime, soft_hours: int = 48) -> dict:
    """Return tiered macro status: HARD | WARN | SOFT | OK."""
    if cache is None:
        return {"tier": "OK", "reason": "no_cache", "stale": True, "next_event": None}
    high_events = [e for e in cache["events"] if e.get("impact") == "high"]
    upcoming = []
    for ev in high_events:
        ev_dt = event_datetime(ev)
        delta = (ev_dt - now).total_seconds() / 60.0  # minutes
        upcoming.append((delta, ev))
    upcoming.sort(key=lambda x: x[0] if x[0] >= 0 else float("inf"))

    if not upcoming:
        return {"tier": "OK", "reason": "no_high_events", "next_event": None}

    # HARD: within ±30 min of any high-impact event
    for delta, ev in upcoming:
        if abs(delta) <= WINDOW_MINUTES:
            return {"tier": "HARD", "next_event": _event_payload(ev, delta)}

    # WARN: within ±WARN_HOURS hours
    for delta, ev in upcoming:
        if abs(delta) <= WARN_HOURS * 60:
            return {"tier": "WARN", "next_event": _event_payload(ev, delta)}

    # SOFT: within next `soft_hours` (positive direction only)
    for delta, ev in upcoming:
        if 0 < delta <= soft_hours * 60:
            return {"tier": "SOFT", "next_event": _event_payload(ev, delta)}

    nearest_delta, nearest_ev = upcoming[0]
    return {"tier": "OK", "next_event": _event_payload(nearest_ev, nearest_delta)}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    p.add_argument("--now", type=str, default=None,
                   help="Override current time (ISO 8601). For testing.")
    sub = p.add_mutually_exclusive_group(required=True)
    sub.add_argument("--check-now", action="store_true")
    sub.add_argument("--check-day", type=str, metavar="YYYY-MM-DD")
    sub.add_argument("--next-events", action="store_true")
    sub.add_argument("--check-tier", action="store_true",
                     help="Output tier: OK/SOFT/WARN/HARD based on macro proximity")
    p.add_argument("--days", type=int, default=7,
                   help="Used with --next-events.")
    p.add_argument("--soft-hours", type=int, default=48,
                   help="Hours ahead to look for SOFT tier (default 48)")
    args = p.parse_args()

    cache = load_cache(args.cache)
    now = parse_now(args.now)

    if args.check_now:
        result = check_now(cache, now)
    elif args.check_day:
        result = check_day(cache, args.check_day, now)
    elif args.check_tier:
        result = check_tier(cache, now, args.soft_hours)
        print(json.dumps(result, indent=2))
        return 0
    else:  # --next-events
        result = next_events(cache, now, args.days)

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
