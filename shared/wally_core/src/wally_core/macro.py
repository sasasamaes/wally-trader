"""Read-only interface for macro events cache.

Writer is .claude/scripts/macro_calendar.py (runs via launchd).
This module only reads. Cache path configurable via WALLY_MACRO_CACHE env var.
"""
from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CR_OFFSET = timezone(timedelta(hours=-6))
# parents[4] is the repo root (src/wally_core/macro.py → wally_core → src → wally_core → shared → repo)
_DEFAULT_CACHE = Path(__file__).parents[4] / ".claude" / "cache" / "macro_events.json"


def _cache_path() -> Path:
    env = os.environ.get("WALLY_MACRO_CACHE")
    if env:
        return Path(env)
    return _DEFAULT_CACHE


def _load_cache() -> dict[str, Any] | None:
    path = _cache_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict) or "events" not in data:
        return None
    return data


def _event_dt(ev: dict) -> datetime:
    return datetime.fromisoformat(f"{ev['date']}T{ev['time_cr']}:00-06:00")


def is_within_event_window(now: datetime, window_min: int = 30) -> dict:
    """Check if `now` is within ±window_min minutes of any high-impact event.

    Returns:
        {within_event: bool, event: str | None, time_to_event_min: int | None}
    """
    cache = _load_cache()
    if cache is None:
        return {"within_event": False, "event": None, "time_to_event_min": None}

    if now.tzinfo is None:
        now = now.replace(tzinfo=CR_OFFSET)

    high_events = [e for e in cache.get("events", []) if e.get("impact") == "high"]
    for ev in high_events:
        ev_dt = _event_dt(ev)
        delta_min = abs((ev_dt - now).total_seconds()) / 60
        if delta_min <= window_min:
            return {
                "within_event": True,
                "event": ev["name"],
                "time_to_event_min": int(delta_min),
            }
    return {"within_event": False, "event": None, "time_to_event_min": None}


def next_events(days: int = 7, now: datetime | None = None) -> list[dict]:
    """Return upcoming high-impact events within the next `days` days, sorted by time.

    Args:
        days: horizon in days.
        now: override current time (defaults to datetime.now(CR_OFFSET)).
    """
    cache = _load_cache()
    if cache is None:
        return []

    if now is None:
        now = datetime.now(CR_OFFSET)
    if now.tzinfo is None:
        now = now.replace(tzinfo=CR_OFFSET)

    horizon = now + timedelta(days=days)
    upcoming = []
    for ev in cache.get("events", []):
        try:
            ev_dt = _event_dt(ev)
        except (ValueError, KeyError):
            continue
        if now <= ev_dt <= horizon:
            upcoming.append(ev)
    upcoming.sort(key=_event_dt)
    return upcoming


STALE_HOURS = 24

_COUNTRY_CCY = {
    "united states": "USD",
    "usa": "USD",
    "euro area": "EUR",
    "united kingdom": "GBP",
    "japan": "JPY",
}


def _country_to_currency(country: str) -> str:
    """Normalize a cache `country` field to a 3-letter currency code.

    The FF scraper stores full names for USD/EUR/GBP/JPY ("United States", ...)
    and raw codes for everything else ("AUD", "CAD"). Map the known names;
    pass through unknown values uppercased.
    """
    c = (country or "").strip()
    return _COUNTRY_CCY.get(c.lower(), c.upper())


def upcoming_relevant(currencies: Iterable[str], hours: int = 48,
                      now: datetime | None = None) -> dict:
    """High-impact events in the next `hours`, filtered to `currencies`.

    Read-only over the macro cache. Never fetches. Returns:
        {events: [{name, currency, country, date, time_cr, hours_until}],
         nearest: <first event or None>, stale: bool, source: str | None}
    """
    wanted = {str(c).upper() for c in currencies}
    cache = _load_cache()
    if cache is None:
        return {"events": [], "nearest": None, "stale": True, "source": None}

    if now is None:
        now = datetime.now(CR_OFFSET)
    if now.tzinfo is None:
        now = now.replace(tzinfo=CR_OFFSET)
    horizon = now + timedelta(hours=hours)

    out = []
    for ev in cache.get("events", []):
        if ev.get("impact") != "high":
            continue
        try:
            ev_dt = _event_dt(ev)
        except (ValueError, KeyError):
            continue
        if not (now <= ev_dt <= horizon):
            continue
        ccy = _country_to_currency(ev.get("country", ""))
        if ccy not in wanted:
            continue
        out.append({
            "name": ev.get("name", "?"),
            "currency": ccy,
            "country": ev.get("country", ""),
            "date": ev["date"],
            "time_cr": ev["time_cr"],
            "hours_until": round((ev_dt - now).total_seconds() / 3600.0, 1),
        })
    # string sort matches chronological order for ISO-formatted date/time fields
    out.sort(key=lambda e: (e["date"], e["time_cr"]))

    stale = True
    fetched = cache.get("fetched_at")
    if fetched:
        try:
            f_dt = datetime.fromisoformat(fetched)
            if f_dt.tzinfo is None:
                f_dt = f_dt.replace(tzinfo=CR_OFFSET)
            stale = (now - f_dt) > timedelta(hours=STALE_HOURS)
        except ValueError:
            stale = True

    return {
        "events": out,
        "nearest": dict(out[0]) if out else None,
        "stale": stale,
        "source": cache.get("source"),
    }
