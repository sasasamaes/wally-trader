#!/usr/bin/env python3
"""macro_gate.py — read-only CLI for the macro events cache.

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

DEFAULT_CACHE = Path(__file__).parent.parent / "cache" / "macro_events.json"
WINDOW_MINUTES = 30
STALE_HOURS = 24
CR_OFFSET = timezone(timedelta(hours=-6))


def load_cache(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"macro_gate: malformed cache: {e}", file=sys.stderr)
        return None


def parse_now(arg: str | None) -> datetime:
    if arg:
        return datetime.fromisoformat(arg)
    return datetime.now(CR_OFFSET)


def event_datetime(ev: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(f"{ev['date']}T{ev['time_cr']}:00-06:00")


def is_stale(cache: dict[str, Any], now: datetime) -> bool:
    fetched = datetime.fromisoformat(cache["fetched_at"])
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
    return {"blocked": False, "stale": is_stale(cache, now)}


def check_day(cache: dict[str, Any] | None, day: str) -> dict[str, Any]:
    if cache is None:
        return {"events": [], "stale": True, "reason": "no_cache"}
    events = [e for e in cache["events"] if e["date"] == day]
    return {"events": events, "stale": False}


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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    p.add_argument("--now", type=str, default=None,
                   help="Override current time (ISO 8601). For testing.")
    sub = p.add_mutually_exclusive_group(required=True)
    sub.add_argument("--check-now", action="store_true")
    sub.add_argument("--check-day", type=str, metavar="YYYY-MM-DD")
    sub.add_argument("--next-events", action="store_true")
    p.add_argument("--days", type=int, default=7,
                   help="Used with --next-events.")
    args = p.parse_args()

    cache = load_cache(args.cache)
    now = parse_now(args.now)

    if args.check_now:
        result = check_now(cache, now)
    elif args.check_day:
        result = check_day(cache, args.check_day)
    else:  # --next-events
        result = next_events(cache, now, args.days)

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
