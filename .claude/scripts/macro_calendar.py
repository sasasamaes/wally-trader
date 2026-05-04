#!/usr/bin/env python3
"""macro_calendar.py — fetch macro events into the cache.

Tries TradingEconomics first, falls back to Forex Factory HTML scraping.
Writes atomically to .claude/cache/macro_events.json.

Usage:
    python3 macro_calendar.py [--cache PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

DEFAULT_CACHE = Path(__file__).parent.parent / "cache" / "macro_events.json"
ERROR_LOG = Path(__file__).parent.parent / "cache" / "macro_calendar_errors.log"
TE_URL = "https://api.tradingeconomics.com/calendar"
TE_PARAMS = {
    "c": "guest:guest",
    "country": "united states,euro area,united kingdom,japan",
    "importance": "3",  # high only
    "format": "json",
}
TIMEOUT_SECONDS = 10
CR_OFFSET = timezone(timedelta(hours=-6))

# Whitelist patterns (case-insensitive substring match)
WHITELIST = [
    "fomc", "fed interest rate", "fed funds", "powell",
    "inflation rate", "cpi", "core cpi",
    "non farm payrolls", "non-farm payrolls", "nfp",
    "pce price index", "core pce",
    "ppi", "producer price",
    "gdp",
    "retail sales",
    "ecb interest rate", "ecb main refinancing", "lagarde",
    "boe interest rate", "bank of england",
    "boj interest rate", "bank of japan",
]


class FetcherError(Exception):
    """Raised when a fetcher cannot produce a usable response."""


def matches_whitelist(name: str) -> bool:
    n = name.lower()
    return any(p in n for p in WHITELIST)


def parse_te_response(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert TradingEconomics calendar response to internal schema."""
    events = []
    for row in raw:
        name = row.get("Event", "").strip()
        if not matches_whitelist(name):
            continue
        # TE Date is naive UTC ISO; convert to CR
        utc = datetime.fromisoformat(row["Date"]).replace(tzinfo=timezone.utc)
        cr = utc.astimezone(CR_OFFSET)
        events.append({
            "date": cr.strftime("%Y-%m-%d"),
            "time_cr": cr.strftime("%H:%M"),
            "country": row.get("Country", "").strip(),
            "name": name,
            "impact": "high",  # importance=3 in our query → high
        })
    return events


def fetch_te() -> list[dict[str, Any]]:
    """Fetch from TradingEconomics, return parsed events. Raise FetcherError on failure."""
    try:
        resp = httpx.get(TE_URL, params=TE_PARAMS, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        return parse_te_response(resp.json())
    except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
        raise FetcherError(f"TE fetch failed: {e}") from e


def fetch_ff() -> list[dict[str, Any]]:
    """Forex Factory HTML scraper. Implemented in Task 1.4."""
    raise FetcherError("Forex Factory fallback not yet implemented")


def write_cache_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=str(path.parent), delete=False, suffix=".tmp"
    ) as tmp:
        json.dump(payload, tmp, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, path)


def log_error(msg: str) -> None:
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ERROR_LOG.open("a") as f:
        f.write(f"{datetime.now(CR_OFFSET).isoformat()} {msg}\n")


def run(cache_path: Path) -> int:
    """Main fetch routine. Returns 0 on success, 1 on double failure."""
    source = None
    events: list[dict[str, Any]] = []
    try:
        events = fetch_te()
        source = "tradingeconomics"
    except FetcherError as te_err:
        log_error(f"TE failed: {te_err}; trying Forex Factory")
        try:
            events = fetch_ff()
            source = "forexfactory"
        except FetcherError as ff_err:
            log_error(f"FF also failed: {ff_err}; keeping existing cache")
            return 1

    payload = {
        "fetched_at": datetime.now(CR_OFFSET).isoformat(),
        "source": source,
        "events": events,
    }
    write_cache_atomic(cache_path, payload)
    print(f"macro_calendar: wrote {len(events)} events from {source} to {cache_path}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    args = p.parse_args()
    return run(args.cache)


if __name__ == "__main__":
    sys.exit(main())
