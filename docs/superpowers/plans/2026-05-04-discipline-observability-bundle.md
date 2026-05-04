# Discipline & Observability Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement three independent observability/discipline features as specified in `docs/superpowers/specs/2026-05-04-discipline-observability-bundle-design.md` — macro events gate (#7), bitunix signal log capture (#3), and weekly cross-profile digest (#8).

**Architecture:** Four new Python helper scripts in `.claude/scripts/`, two launchd plists for scheduled jobs, one new slash command (`/log-outcome`), and wire-in modifications to four existing agents. Each feature is independently testable; recommended sequence is #7 → #3 → #8 because #8 reads #7's cache.

**Tech Stack:** Python 3.9, httpx, beautifulsoup4 (new), pytest + pytest-mock (existing), bash, launchd (macOS).

---

## File Structure

### New scripts (`.claude/scripts/`)
- `macro_calendar.py` — Fetcher for TradingEconomics + Forex Factory fallback. Atomic write to cache.
- `macro_gate.py` — Read-only CLI: `--check-now`, `--check-day`, `--next-events`. Pure cache reads.
- `bitunix_log.py` — Two subcommands: `append-signal --stdin`, `append-outcome SYMBOL OUTCOME EXIT_PRICE [--id N] [--pnl USD]`.
- `weekly_digest.py` — Cross-profile digest generator with profile parser registry.

### New launchd plists (`.claude/launchd/`)
- `com.wally.macro-calendar.plist` — Daily refresh at CR 04:00.
- `com.wally.weekly-digest.plist` — Sunday 18:00 CR.

### New slash command
- `system/commands/log-outcome.md` (+ `.opencode/commands/log-outcome.md`, `.hermes/skills/wally-commands/log-outcome/SKILL.md`).

### New cache + output dirs
- `.claude/cache/macro_events.json` — created on first fetch.
- `memory/weekly_digests/` — created on first digest run.

### New tests (`.claude/scripts/tests/`)
- `test_macro_calendar.py`, `test_macro_gate.py`, `test_bitunix_log.py`, `test_weekly_digest.py`
- `fixtures/macro/te_response.json`, `fixtures/macro/ff_response.html`, `fixtures/macro/cache_today_event.json`
- `fixtures/bitunix/signal_report_canonical.md`, `fixtures/bitunix/signals_received_with_open.md`
- `fixtures/digest/profiles/<profile>/{config.md,memory/trading_log.md}`

### Modified
- `system/commands/signal.md` (+ mirrors): pipe output to `bitunix_log.py append-signal` if profile is bitunix.
- `system/agents/morning-analyst.md`, `morning-analyst-ftmo.md` (+ mirrors): macro check at start, prepend warning.
- `system/agents/trade-validator.md`, `signal-validator.md` (+ mirrors): macro gate as FASE 1 prerequisite.
- `.claude/scripts/test_pdf_helpers.py`: 2 new sanity tests.
- `.claude/scripts/requirements-helpers.txt`: add `beautifulsoup4>=4.12`.
- `CLAUDE.md`: brief reference to new commands.

---

# Phase 1 — Macro Events Gate (#7)

## Task 1.1: Add beautifulsoup4 dependency

**Files:**
- Modify: `.claude/scripts/requirements-helpers.txt`

- [ ] **Step 1: Add bs4 to requirements**

Append to `.claude/scripts/requirements-helpers.txt`:
```
# Macro events gate — Forex Factory HTML fallback parsing
beautifulsoup4>=4.12
```

- [ ] **Step 2: Install in venv**

Run:
```bash
.claude/scripts/.venv/bin/pip install -r .claude/scripts/requirements-helpers.txt
```
Expected: `Successfully installed beautifulsoup4-4.x` (or "already satisfied").

- [ ] **Step 3: Commit**

```bash
git add .claude/scripts/requirements-helpers.txt
git commit -m "chore(macro): add beautifulsoup4 for Forex Factory fallback parsing"
```

---

## Task 1.2: macro_gate.py — cache schema + check-now logic (TDD)

**Files:**
- Create: `.claude/scripts/macro_gate.py`
- Test: `.claude/scripts/tests/test_macro_gate.py`
- Test: `.claude/scripts/tests/fixtures/macro/cache_today_event.json`

- [ ] **Step 1: Write the cache fixture**

Create `.claude/scripts/tests/fixtures/macro/cache_today_event.json` with content:
```json
{
  "fetched_at": "2026-05-04T04:00:00-06:00",
  "source": "tradingeconomics",
  "events": [
    {
      "date": "2026-05-04",
      "time_cr": "06:30",
      "country": "United States",
      "name": "CPI",
      "impact": "high"
    },
    {
      "date": "2026-05-06",
      "time_cr": "13:00",
      "country": "United States",
      "name": "FOMC Statement",
      "impact": "high"
    },
    {
      "date": "2026-05-07",
      "time_cr": "06:30",
      "country": "United States",
      "name": "Jobless Claims",
      "impact": "medium"
    }
  ]
}
```

- [ ] **Step 2: Write failing tests**

Create `.claude/scripts/tests/test_macro_gate.py`:
```python
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "macro"
SCRIPT = Path(__file__).parent.parent / "macro_gate.py"


def run_gate(args, cache_path, fake_now=None):
    """Run macro_gate.py with a custom cache path and fake clock."""
    env_args = ["--cache", str(cache_path)] + args
    if fake_now:
        env_args = ["--now", fake_now] + env_args
    result = subprocess.run(
        ["python3", str(SCRIPT), *env_args],
        capture_output=True, text=True
    )
    return result


def test_check_now_blocks_within_30min_before(tmp_path):
    cache = tmp_path / "cache.json"
    cache.write_text((FIXTURES / "cache_today_event.json").read_text())
    # CPI at 06:30 CR; we are at 06:18 → 12 min before → BLOCKED
    r = run_gate(["--check-now"], cache, fake_now="2026-05-04T06:18:00-06:00")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["blocked"] is True
    assert "CPI" in payload["reason"]


def test_check_now_does_not_block_31min_before(tmp_path):
    cache = tmp_path / "cache.json"
    cache.write_text((FIXTURES / "cache_today_event.json").read_text())
    # 05:59 → 31 min before → NOT blocked
    r = run_gate(["--check-now"], cache, fake_now="2026-05-04T05:59:00-06:00")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["blocked"] is False


def test_check_now_does_not_block_31min_after(tmp_path):
    cache = tmp_path / "cache.json"
    cache.write_text((FIXTURES / "cache_today_event.json").read_text())
    # 07:01 → 31 min after CPI → NOT blocked
    r = run_gate(["--check-now"], cache, fake_now="2026-05-04T07:01:00-06:00")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["blocked"] is False


def test_check_now_stale_cache_flag(tmp_path):
    cache = tmp_path / "cache.json"
    data = json.loads((FIXTURES / "cache_today_event.json").read_text())
    # Set fetched_at to 25 hours ago
    data["fetched_at"] = "2026-05-03T03:00:00-06:00"
    cache.write_text(json.dumps(data))
    r = run_gate(["--check-now"], cache, fake_now="2026-05-04T08:00:00-06:00")
    payload = json.loads(r.stdout)
    assert payload["stale"] is True


def test_check_now_missing_cache(tmp_path):
    cache = tmp_path / "does_not_exist.json"
    r = run_gate(["--check-now"], cache, fake_now="2026-05-04T08:00:00-06:00")
    assert r.returncode == 0  # don't break consumer
    payload = json.loads(r.stdout)
    assert payload["blocked"] is False
    assert payload["reason"] == "no_cache"


def test_check_day_lists_events_for_date(tmp_path):
    cache = tmp_path / "cache.json"
    cache.write_text((FIXTURES / "cache_today_event.json").read_text())
    r = run_gate(["--check-day", "2026-05-04"], cache)
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert len(payload["events"]) == 1
    assert payload["events"][0]["name"] == "CPI"


def test_next_events_within_n_days(tmp_path):
    cache = tmp_path / "cache.json"
    cache.write_text((FIXTURES / "cache_today_event.json").read_text())
    r = run_gate(["--next-events", "--days", "7"], cache, fake_now="2026-05-04T00:00:00-06:00")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    # CPI today, FOMC May 6, Jobless May 7 — all within 7 days
    assert len(payload["events"]) == 3


def test_only_high_impact_blocks_check_now(tmp_path):
    """Medium-impact events should NOT trigger --check-now block."""
    cache = tmp_path / "cache.json"
    cache.write_text((FIXTURES / "cache_today_event.json").read_text())
    # Jobless Claims (medium) on 2026-05-07 06:30 CR; check at 06:18 → not blocked
    r = run_gate(["--check-now"], cache, fake_now="2026-05-07T06:18:00-06:00")
    payload = json.loads(r.stdout)
    assert payload["blocked"] is False
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_macro_gate.py -v
```
Expected: all tests FAIL (script doesn't exist yet).

- [ ] **Step 4: Implement macro_gate.py**

Create `.claude/scripts/macro_gate.py`:
```python
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
```

- [ ] **Step 5: Run tests to verify pass**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_macro_gate.py -v
```
Expected: all 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add .claude/scripts/macro_gate.py .claude/scripts/tests/test_macro_gate.py .claude/scripts/tests/fixtures/macro/cache_today_event.json
git commit -m "feat(macro): macro_gate.py CLI with check-now, check-day, next-events"
```

---

## Task 1.3: macro_calendar.py — TradingEconomics fetcher (TDD)

**Files:**
- Create: `.claude/scripts/macro_calendar.py`
- Test: `.claude/scripts/tests/test_macro_calendar.py`
- Test: `.claude/scripts/tests/fixtures/macro/te_response.json`

- [ ] **Step 1: Write the TE response fixture**

Create `.claude/scripts/tests/fixtures/macro/te_response.json`:
```json
[
  {
    "Date": "2026-05-04T12:30:00",
    "Country": "United States",
    "Event": "Inflation Rate YoY",
    "Importance": 3,
    "Reference": "Apr"
  },
  {
    "Date": "2026-05-06T19:00:00",
    "Country": "United States",
    "Event": "Fed Interest Rate Decision",
    "Importance": 3,
    "Reference": "May"
  },
  {
    "Date": "2026-05-08T08:30:00",
    "Country": "Euro Area",
    "Event": "ECB Interest Rate Decision",
    "Importance": 3,
    "Reference": "May"
  },
  {
    "Date": "2026-05-09T15:00:00",
    "Country": "United States",
    "Event": "Some Random PMI",
    "Importance": 3,
    "Reference": "May"
  }
]
```

NOTE: TE returns dates in UTC. Times above translate to CR (UTC-6) as: 06:30, 13:00, 02:30, 09:00.

- [ ] **Step 2: Write failing tests**

Create `.claude/scripts/tests/test_macro_calendar.py`:
```python
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import httpx

FIXTURES = Path(__file__).parent / "fixtures" / "macro"


def test_parse_te_response_filters_whitelist():
    from macro_calendar import parse_te_response
    raw = json.loads((FIXTURES / "te_response.json").read_text())
    events = parse_te_response(raw)
    names = [e["name"] for e in events]
    # CPI (Inflation Rate YoY), Fed Rate Decision, ECB Rate Decision should pass
    assert "Inflation Rate YoY" in names
    assert "Fed Interest Rate Decision" in names
    assert "ECB Interest Rate Decision" in names
    # Random PMI should NOT pass whitelist
    assert "Some Random PMI" not in names


def test_parse_te_response_converts_to_cr_time():
    from macro_calendar import parse_te_response
    raw = json.loads((FIXTURES / "te_response.json").read_text())
    events = parse_te_response(raw)
    cpi = next(e for e in events if "Inflation" in e["name"])
    # 12:30 UTC → 06:30 CR
    assert cpi["time_cr"] == "06:30"
    assert cpi["date"] == "2026-05-04"


def test_fetch_te_success(tmp_path):
    """When TE returns 200, parse and write cache."""
    from macro_calendar import fetch_te
    raw = (FIXTURES / "te_response.json").read_text()
    with patch("httpx.get") as mock_get:
        resp = MagicMock(status_code=200, text=raw)
        resp.raise_for_status.return_value = None
        resp.json.return_value = json.loads(raw)
        mock_get.return_value = resp
        events = fetch_te()
    assert len(events) >= 3
    assert all(e["impact"] == "high" for e in events)


def test_fetch_te_429_raises(tmp_path):
    from macro_calendar import fetch_te, FetcherError
    with patch("httpx.get") as mock_get:
        resp = MagicMock(status_code=429)
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "rate limit", request=MagicMock(), response=resp
        )
        mock_get.return_value = resp
        with pytest.raises(FetcherError):
            fetch_te()


def test_main_writes_atomic_cache(tmp_path):
    """End-to-end: main writes a valid cache file via tmp+rename pattern."""
    from macro_calendar import run
    raw = json.loads((FIXTURES / "te_response.json").read_text())
    cache_path = tmp_path / "cache.json"
    with patch("macro_calendar.fetch_te", return_value=[
        {"date": "2026-05-04", "time_cr": "06:30", "country": "United States",
         "name": "CPI", "impact": "high"}
    ]):
        rc = run(cache_path)
    assert rc == 0
    assert cache_path.exists()
    cached = json.loads(cache_path.read_text())
    assert cached["source"] == "tradingeconomics"
    assert "fetched_at" in cached
    assert len(cached["events"]) == 1


def test_main_falls_back_to_ff_on_te_failure(tmp_path):
    from macro_calendar import run, FetcherError
    cache_path = tmp_path / "cache.json"
    with patch("macro_calendar.fetch_te", side_effect=FetcherError("rate limited")), \
         patch("macro_calendar.fetch_ff", return_value=[
             {"date": "2026-05-04", "time_cr": "06:30", "country": "United States",
              "name": "CPI", "impact": "high"}
         ]):
        rc = run(cache_path)
    assert rc == 0
    cached = json.loads(cache_path.read_text())
    assert cached["source"] == "forexfactory"


def test_main_keeps_existing_cache_on_double_failure(tmp_path):
    from macro_calendar import run, FetcherError
    cache_path = tmp_path / "cache.json"
    cache_path.write_text(json.dumps({
        "fetched_at": "2026-05-03T04:00:00-06:00",
        "source": "tradingeconomics",
        "events": []
    }))
    with patch("macro_calendar.fetch_te", side_effect=FetcherError("ratelimit")), \
         patch("macro_calendar.fetch_ff", side_effect=FetcherError("dom changed")):
        rc = run(cache_path)
    assert rc == 1  # signals failure
    # Old cache untouched
    cached = json.loads(cache_path.read_text())
    assert cached["fetched_at"] == "2026-05-03T04:00:00-06:00"
```

- [ ] **Step 3: Run tests to confirm fail**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_macro_calendar.py -v
```
Expected: ImportError on `from macro_calendar import ...`.

- [ ] **Step 4: Implement macro_calendar.py (TE primary path)**

Create `.claude/scripts/macro_calendar.py`:
```python
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
```

- [ ] **Step 5: Run tests — all should pass**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_macro_calendar.py -v
```
Expected: all 7 tests PASS. Note: the fallback tests (`test_main_falls_back_to_ff_on_te_failure`, `test_main_keeps_existing_cache_on_double_failure`) work because they patch `fetch_ff` directly; the real FF implementation comes in Task 1.4.

- [ ] **Step 6: Commit**

```bash
git add .claude/scripts/macro_calendar.py .claude/scripts/tests/test_macro_calendar.py .claude/scripts/tests/fixtures/macro/te_response.json
git commit -m "feat(macro): TE primary fetcher, atomic cache write, error logging"
```

---

## Task 1.4: macro_calendar.py — Forex Factory fallback (TDD)

**Files:**
- Modify: `.claude/scripts/macro_calendar.py:fetch_ff`
- Create: `.claude/scripts/tests/fixtures/macro/ff_response.html`

- [ ] **Step 1: Capture an FF page snapshot**

Run once in a sandbox to grab the live structure (do NOT skip — the fixture must reflect actual FF DOM):
```bash
.claude/scripts/.venv/bin/python -c "
import httpx
r = httpx.get('https://www.forexfactory.com/calendar', timeout=15,
              headers={'User-Agent': 'Mozilla/5.0'})
print(r.status_code)
open('.claude/scripts/tests/fixtures/macro/ff_response.html', 'w').write(r.text)
"
```
Expected: prints `200`, file size >50KB.

If FF blocks the request, document in a comment and write a manually-trimmed fixture from a copy-pasted HTML row.

- [ ] **Step 2: Write FF parser test**

Append to `.claude/scripts/tests/test_macro_calendar.py`:
```python
def test_parse_ff_response_extracts_high_impact():
    from macro_calendar import parse_ff_response
    html = (FIXTURES / "ff_response.html").read_text()
    events = parse_ff_response(html)
    # Should find at least 1 high-impact event matching whitelist
    assert len(events) >= 1
    for e in events:
        assert e["impact"] == "high"
        assert e["date"]  # YYYY-MM-DD
        assert e["time_cr"]  # HH:MM


def test_parse_ff_response_filters_whitelist():
    from macro_calendar import parse_ff_response
    html = (FIXTURES / "ff_response.html").read_text()
    events = parse_ff_response(html)
    # Whatever events come out, all must match whitelist
    from macro_calendar import matches_whitelist
    for e in events:
        assert matches_whitelist(e["name"]), f"{e['name']} not in whitelist"
```

- [ ] **Step 3: Run tests, see them fail**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_macro_calendar.py::test_parse_ff_response_extracts_high_impact -v
```
Expected: FAIL — `parse_ff_response` doesn't exist.

- [ ] **Step 4: Implement FF parser**

Replace the `fetch_ff` stub in `.claude/scripts/macro_calendar.py` with this block (add `parse_ff_response` next to `parse_te_response`):

```python
from bs4 import BeautifulSoup

FF_URL = "https://www.forexfactory.com/calendar"
FF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def parse_ff_response(html: str) -> list[dict[str, Any]]:
    """Parse Forex Factory calendar HTML.

    Selectors are based on the FF DOM at fixture-capture time; if FF redesigns
    their markup this needs updating. The structure we look for: rows
    <tr class="calendar__row"> with cells for date, time, currency, impact, event.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("tr.calendar__row")
    events: list[dict[str, Any]] = []
    current_date_iso = None  # FF rolls date in spans; track across rows

    for row in rows:
        # Date span (only on rows that start a new day)
        date_cell = row.select_one(".calendar__date")
        if date_cell and date_cell.get_text(strip=True):
            try:
                current_date_iso = _parse_ff_date(date_cell.get_text(strip=True))
            except ValueError:
                pass

        impact_cell = row.select_one(".calendar__impact")
        if not impact_cell:
            continue
        # FF marks high-impact via title attribute on a span
        impact_marker = impact_cell.select_one("[title*='High Impact']") \
            or impact_cell.select_one(".impact--high")
        if not impact_marker:
            continue

        time_text = (row.select_one(".calendar__time") or "").get_text(strip=True) if row.select_one(".calendar__time") else ""
        currency = (row.select_one(".calendar__currency") or "").get_text(strip=True) if row.select_one(".calendar__currency") else ""
        event_name_cell = row.select_one(".calendar__event-title") or row.select_one(".calendar__event")
        if not event_name_cell:
            continue
        name = event_name_cell.get_text(strip=True)
        if not matches_whitelist(name):
            continue
        if not current_date_iso:
            continue

        # FF time is in EST/EDT; convert to CR (CR is UTC-6 always, EST is UTC-5, EDT is UTC-4)
        # Conservative: assume EDT (UTC-4) → CR is 2h behind EDT
        # If time is "All Day" / "Tentative" / "" — skip
        time_cr = _convert_ff_time_to_cr(time_text)
        if not time_cr:
            continue

        events.append({
            "date": current_date_iso,
            "time_cr": time_cr,
            "country": _ff_currency_to_country(currency),
            "name": name,
            "impact": "high",
        })
    return events


def _parse_ff_date(s: str) -> str:
    """FF dates look like 'MonMay4' or 'Mon May 4'. Normalize to YYYY-MM-DD."""
    # Defensive parse — try a few formats
    s = s.replace("\n", " ").strip()
    for fmt in ("%a %b %d", "%a%b%d", "%b %d"):
        try:
            dt = datetime.strptime(s, fmt)
            year = datetime.now(CR_OFFSET).year
            return dt.replace(year=year).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"unparseable FF date: {s!r}")


def _convert_ff_time_to_cr(time_text: str) -> str | None:
    """FF time like '8:30am' (EST/EDT). Convert to CR HH:MM. Return None if unparseable."""
    if not time_text or time_text.lower() in ("all day", "tentative", ""):
        return None
    # Try '8:30am' / '8:30pm'
    try:
        dt = datetime.strptime(time_text.lower(), "%I:%M%p")
    except ValueError:
        return None
    # Assume EDT (UTC-4) for safety; CR is UTC-6 → CR = EDT - 2h
    cr_hour = (dt.hour - 2) % 24
    return f"{cr_hour:02d}:{dt.minute:02d}"


def _ff_currency_to_country(curr: str) -> str:
    return {
        "USD": "United States",
        "EUR": "Euro Area",
        "GBP": "United Kingdom",
        "JPY": "Japan",
    }.get(curr.upper(), curr)


def fetch_ff() -> list[dict[str, Any]]:
    try:
        resp = httpx.get(FF_URL, headers=FF_HEADERS, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        events = parse_ff_response(resp.text)
        if not events:
            raise FetcherError("FF parse returned 0 events — DOM may have changed")
        return events
    except (httpx.HTTPError, ValueError) as e:
        raise FetcherError(f"FF fetch failed: {e}") from e
```

Make sure to remove the old stub `def fetch_ff(): raise FetcherError(...)`.

- [ ] **Step 5: Run all macro_calendar tests**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_macro_calendar.py -v
```
Expected: all PASS.

- [ ] **Step 6: Manual smoke test fetch from real network**

```bash
.claude/scripts/.venv/bin/python .claude/scripts/macro_calendar.py
```
Expected: writes `.claude/cache/macro_events.json` with `source: tradingeconomics` and ≥3 events for current/next week.

If TE failed and FF was used, that's still success — note which source was used in commit message.

- [ ] **Step 7: Commit**

```bash
git add .claude/scripts/macro_calendar.py .claude/scripts/tests/test_macro_calendar.py .claude/scripts/tests/fixtures/macro/ff_response.html
git commit -m "feat(macro): Forex Factory fallback parser with whitelist filter"
```

---

## Task 1.5: Wire macro gate into trade-validator agent

**Files:**
- Modify: `system/agents/trade-validator.md` (and mirrors at `.opencode/agents/trade-validator.md`, `.hermes/skills/wally-agents/trade-validator/SKILL.md`)

- [ ] **Step 1: Read current trade-validator structure**

```bash
cat system/agents/trade-validator.md | head -80
```

Identify where "FASE 1" or the equivalent first validation phase begins.

- [ ] **Step 2: Insert macro gate as first check**

At the beginning of the validation flow (BEFORE the 4-filter evaluation), add a new section. Use Edit tool to insert this block right before the existing "FASE 1" or the first validation step:

```markdown
## FASE 0 — Macro events gate (defensivo)

Antes de evaluar los 4 filtros, ejecutar:

```bash
bash .claude/scripts/macro_gate.py --check-now
```

Decisión:
- Si `blocked: true` → respuesta inmediata `NO-GO: macro event window — <reason>`. NO seguir con los filtros.
- Si `stale: true` y `blocked: false` → continuar pero agregar warning al output: `⚠️ macro cache stale (>24h) — refresh con bash .claude/scripts/macro_calendar.py`.
- Si `blocked: false` y `stale: false` → continuar con FASE 1.
- Si script falla (exit code != 0) → continuar pero loggear warning. No bloquear por fallo de feed.
```

Then increment any other phase numbers if the agent uses them sequentially.

- [ ] **Step 3: Apply same change to mirrors**

Repeat the insertion for:
- `.opencode/agents/trade-validator.md`
- `.hermes/skills/wally-agents/trade-validator/SKILL.md`

(The wording can be identical; the multi-CLI portability pattern keeps these in sync.)

- [ ] **Step 4: Smoke test the agent invocation**

In a session, simulate the agent running its check by executing the same command directly:
```bash
bash .claude/scripts/macro_gate.py --check-now
```
Confirm the JSON has `blocked` field. If you get an empty cache, run `bash .claude/scripts/macro_calendar.py` first.

- [ ] **Step 5: Commit**

```bash
git add system/agents/trade-validator.md .opencode/agents/trade-validator.md .hermes/skills/wally-agents/trade-validator/SKILL.md
git commit -m "feat(macro): wire macro gate as FASE 0 in trade-validator"
```

---

## Task 1.6: Wire macro gate into signal-validator agent

**Files:**
- Modify: `system/agents/signal-validator.md` and mirrors

- [ ] **Step 1: Apply identical FASE 0 block as Task 1.5**

Same insertion as 1.5, in `system/agents/signal-validator.md` and the two mirrors. Place before the 4-filter evaluation.

- [ ] **Step 2: Commit**

```bash
git add system/agents/signal-validator.md .opencode/agents/signal-validator.md .hermes/skills/wally-agents/signal-validator/SKILL.md
git commit -m "feat(macro): wire macro gate as FASE 0 in signal-validator"
```

---

## Task 1.7: Wire macro gate into morning-analyst agents (warn-only)

**Files:**
- Modify: `system/agents/morning-analyst.md` and mirrors
- Modify: `system/agents/morning-analyst-ftmo.md` and mirrors

- [ ] **Step 1: Insert warn block at start of morning analysis**

In `system/agents/morning-analyst.md`, locate the start of the analysis flow (e.g., FASE 1 or the first action). Insert BEFORE it:

```markdown
## FASE 0 — Macro events del día (informativo)

Al inicio del análisis, ejecutar:

```bash
bash .claude/scripts/macro_gate.py --check-day "$(date +%Y-%m-%d)"
```

Si la respuesta tiene events listados:
- Prepend al output del análisis: `🔴 MACRO ALERT: <name> a las <time_cr> CR (<country>) — NO TRADE en ventana ±30 min`
- Recomendar al final del análisis: "Día con eventos high-impact. Concentrar entries fuera de las ventanas marcadas o saltar el día si hay >2 eventos."

Si no hay events: continuar normal sin agregar nada.

Si script falla: continuar normal, loggear warning interno.
```

- [ ] **Step 2: Apply to morning-analyst-ftmo.md**

Same block, in `system/agents/morning-analyst-ftmo.md`. The FTMO multi-asset analyst especially benefits because it also trades EURUSD/GBPUSD/USDJPY which react to ECB/BoE/BoJ.

- [ ] **Step 3: Apply to mirrors**

`.opencode/agents/morning-analyst.md`, `.opencode/agents/morning-analyst-ftmo.md`, `.hermes/skills/wally-agents/morning-analyst/SKILL.md`, `.hermes/skills/wally-agents/morning-analyst-ftmo/SKILL.md`.

- [ ] **Step 4: Commit**

```bash
git add system/agents/morning-analyst.md system/agents/morning-analyst-ftmo.md .opencode/agents/morning-analyst.md .opencode/agents/morning-analyst-ftmo.md .hermes/skills/wally-agents/morning-analyst/SKILL.md .hermes/skills/wally-agents/morning-analyst-ftmo/SKILL.md
git commit -m "feat(macro): warn-only macro check at start of morning-analyst (both profiles)"
```

---

## Task 1.8: launchd plist for daily macro fetch

**Files:**
- Create: `.claude/launchd/com.wally.macro-calendar.plist`

- [ ] **Step 1: Write plist matching project convention**

Create `.claude/launchd/com.wally.macro-calendar.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wally.macro-calendar</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/josecampos/Documents/wally-trader/.claude/scripts/.venv/bin/python</string>
        <string>/Users/josecampos/Documents/wally-trader/.claude/scripts/macro_calendar.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/josecampos/Documents/wally-trader/.claude/scripts</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>4</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>RunAtLoad</key>
    <false/>

    <key>StandardOutPath</key>
    <string>/Users/josecampos/Library/Logs/wally-trader/macro-calendar.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/josecampos/Library/Logs/wally-trader/macro-calendar.err</string>

    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
```

- [ ] **Step 2: Verify plist syntax**

```bash
plutil -lint .claude/launchd/com.wally.macro-calendar.plist
```
Expected: `OK`.

- [ ] **Step 3: Document install command**

The plist lives in the repo. To activate, the user runs:
```bash
cp .claude/launchd/com.wally.macro-calendar.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.wally.macro-calendar.plist
launchctl start com.wally.macro-calendar  # one-shot test
launchctl list | grep com.wally.macro
```
Add a note to `CLAUDE.md` in Task 4.1 referencing this.

- [ ] **Step 4: Commit**

```bash
git add .claude/launchd/com.wally.macro-calendar.plist
git commit -m "ops(macro): launchd plist daily refresh CR 04:00"
```

---

## Task 1.9: Sanity tests in test_pdf_helpers.py

**Files:**
- Modify: `.claude/scripts/test_pdf_helpers.py`

- [ ] **Step 1: Read current sanity tests file**

```bash
head -40 .claude/scripts/test_pdf_helpers.py
```
Identify the test pattern and append in the same style.

- [ ] **Step 2: Append macro_gate sanity tests**

Append two tests:
```python
def test_macro_gate_handles_missing_cache():
    """macro_gate.py --check-now exits 0 even with empty cache."""
    import subprocess, json, tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        empty = Path(d) / "nope.json"
        r = subprocess.run(
            ["python3", str(Path(__file__).parent / "macro_gate.py"),
             "--cache", str(empty), "--check-now"],
            capture_output=True, text=True
        )
        assert r.returncode == 0
        payload = json.loads(r.stdout)
        assert payload["blocked"] is False
        assert payload["reason"] == "no_cache"


def test_macro_gate_check_day_smoke():
    """macro_gate.py --check-day with empty cache returns empty events."""
    import subprocess, json, tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        empty = Path(d) / "nope.json"
        r = subprocess.run(
            ["python3", str(Path(__file__).parent / "macro_gate.py"),
             "--cache", str(empty), "--check-day", "2026-05-04"],
            capture_output=True, text=True
        )
        assert r.returncode == 0
        payload = json.loads(r.stdout)
        assert payload["events"] == []
```

- [ ] **Step 3: Run the helper file end-to-end**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/test_pdf_helpers.py -v
```
Expected: all original tests + 2 new ones PASS.

- [ ] **Step 4: Commit**

```bash
git add .claude/scripts/test_pdf_helpers.py
git commit -m "test(macro): add macro_gate sanity tests to hourly preprompt check"
```

---

# Phase 2 — Bitunix Log Capture (#3)

## Task 2.1: bitunix_log.py — append-signal subcommand (TDD)

**Files:**
- Create: `.claude/scripts/bitunix_log.py`
- Test: `.claude/scripts/tests/test_bitunix_log.py`
- Test: `.claude/scripts/tests/fixtures/bitunix/signal_report_canonical.md`

- [ ] **Step 1: Build the canonical /signal report fixture**

Create `.claude/scripts/tests/fixtures/bitunix/signal_report_canonical.md`:
```markdown
# /signal validation — BTCUSDT LONG

**Symbol:** BTCUSDT
**Side:** LONG
**Entry:** 67000
**SL:** 66500
**TP:** 68000
**Leverage signal:** 20x
**Source:** punkchainer Discord
**Day-of-week:** Mon

## Pipeline validación (8 steps)

1. **Parse OK** — entry/SL/TP válidos
2. **4 filtros técnicos:** 4/4 ✅
3. **Multi-Factor:** +62 (LONG) | **ML:** 71
4. **Chainlink delta:** 0.04% (OK)
5. **Régimen:** RANGE — compatible con LONG ✅
6. **4-Pilar Neptune SMC:** 4/4 (OB ✅ Sweep ✅ CHoCH ✅ SFP ✅)
7. **Saturday Protocol:** N/A (Mon)
8. **Veredicto:** APPROVE_FULL

**Validation Score:** 78/100
**Decisión:** EJECUTADO full size 2%
**DUREX trigger:** weekday 20% recorrido
**Leverage cap aplicado:** 10x (override de 20x)
```

- [ ] **Step 2: Write failing tests**

Create `.claude/scripts/tests/test_bitunix_log.py`:
```python
import csv
import os
import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "bitunix"
SCRIPT = Path(__file__).parent.parent / "bitunix_log.py"


def run_log(args, cwd, env=None, stdin=None):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        capture_output=True, text=True, cwd=cwd, env=full_env, input=stdin
    )


def setup_bitunix_profile(tmp_path: Path) -> Path:
    """Create a minimal bitunix profile structure under tmp_path."""
    p = tmp_path / ".claude" / "profiles" / "bitunix" / "memory"
    p.mkdir(parents=True)
    # Empty md and csv with headers
    (p / "signals_received.md").write_text("# Bitunix — Signals received\n\n## Histórico\n\n")
    (p / "signals_received.csv").write_text(
        "date,time,symbol,side,entry,sl,tp,leverage_signal,"
        "day_of_week,filters_4,multifactor,ml_score,chainlink_delta,"
        "regime,pillars_4_count,saturday,verdict,decision,size_pct,"
        "executed,exit_price,exit_reason,pnl_usd,duration_h,"
        "hypothetical_outcome,learning\n"
    )
    return tmp_path


def test_append_signal_no_op_on_non_bitunix_profile(tmp_path):
    setup_bitunix_profile(tmp_path)
    canonical = (FIXTURES / "signal_report_canonical.md").read_text()
    r = run_log(["append-signal", "--stdin"], cwd=tmp_path,
                env={"WALLY_PROFILE": "retail"}, stdin=canonical)
    assert r.returncode == 0
    # Files unchanged
    md = (tmp_path / ".claude/profiles/bitunix/memory/signals_received.md").read_text()
    assert "## 2026" not in md  # no new entry


def test_append_signal_parses_canonical_report(tmp_path):
    setup_bitunix_profile(tmp_path)
    canonical = (FIXTURES / "signal_report_canonical.md").read_text()
    r = run_log(["append-signal", "--stdin"], cwd=tmp_path,
                env={"WALLY_PROFILE": "bitunix"}, stdin=canonical)
    assert r.returncode == 0, r.stderr
    md = (tmp_path / ".claude/profiles/bitunix/memory/signals_received.md").read_text()
    assert "BTCUSDT" in md
    assert "Entry:** 67000" in md or "entry 67000" in md.lower()
    assert "Validation Score:** 78/100" in md
    assert "APPROVE_FULL" in md

    csv_path = tmp_path / ".claude/profiles/bitunix/memory/signals_received.csv"
    rows = list(csv.DictReader(csv_path.open()))
    assert len(rows) == 1
    row = rows[0]
    assert row["symbol"] == "BTCUSDT"
    assert row["side"] == "LONG"
    assert row["entry"] == "67000"
    assert row["sl"] == "66500"
    assert row["tp"] == "68000"
    assert row["leverage_signal"] == "20"
    assert row["day_of_week"] == "Mon"
    assert row["filters_4"] == "4"
    assert row["multifactor"] == "+62"
    assert row["ml_score"] == "71"
    assert row["regime"] == "RANGE"
    assert row["pillars_4_count"] == "4"
    assert row["saturday"] == "N"
    assert row["verdict"] == "APPROVE_FULL"
    assert row["decision"] == "EJECUTADO full size 2%"
    assert row["size_pct"] == "2"
    assert row["executed"] == "yes"


def test_append_signal_malformed_input(tmp_path):
    setup_bitunix_profile(tmp_path)
    r = run_log(["append-signal", "--stdin"], cwd=tmp_path,
                env={"WALLY_PROFILE": "bitunix"},
                stdin="this is not a valid signal report")
    assert r.returncode != 0
    err_log = tmp_path / ".claude/cache/bitunix_log_errors.log"
    assert err_log.exists()
    assert "parse failed" in err_log.read_text().lower()
    # MD/CSV NOT modified
    md = (tmp_path / ".claude/profiles/bitunix/memory/signals_received.md").read_text()
    assert "## 2026" not in md
```

- [ ] **Step 3: Run tests, see them fail**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_bitunix_log.py -v
```
Expected: ImportError / file not found.

- [ ] **Step 4: Implement bitunix_log.py with append-signal**

Create `.claude/scripts/bitunix_log.py`:
```python
#!/usr/bin/env python3
"""bitunix_log.py — append signals + outcomes to bitunix log files.

Subcommands:
  append-signal --stdin    : parse a /signal markdown report and append entry to MD + CSV
  append-outcome SYMBOL OUTCOME EXIT_PRICE [--id N] [--pnl USD] : close an open entry

Profile gating: only writes when WALLY_PROFILE == "bitunix". Otherwise no-op exit 0.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CR_OFFSET = timezone(timedelta(hours=-6))
CSV_FIELDS = [
    "date", "time", "symbol", "side", "entry", "sl", "tp", "leverage_signal",
    "day_of_week", "filters_4", "multifactor", "ml_score", "chainlink_delta",
    "regime", "pillars_4_count", "saturday", "verdict", "decision", "size_pct",
    "executed", "exit_price", "exit_reason", "pnl_usd", "duration_h",
    "hypothetical_outcome", "learning",
]


def repo_root() -> Path:
    """Find repo root by walking up looking for .claude/."""
    cur = Path.cwd()
    while cur != cur.parent:
        if (cur / ".claude").is_dir():
            return cur
        cur = cur.parent
    return Path.cwd()


def bitunix_paths() -> tuple[Path, Path]:
    root = repo_root()
    base = root / ".claude" / "profiles" / "bitunix" / "memory"
    return base / "signals_received.md", base / "signals_received.csv"


def is_bitunix_profile() -> bool:
    return os.environ.get("WALLY_PROFILE", "") == "bitunix"


def log_error(msg: str, body: str = "") -> None:
    err_path = repo_root() / ".claude" / "cache" / "bitunix_log_errors.log"
    err_path.parent.mkdir(parents=True, exist_ok=True)
    with err_path.open("a") as f:
        f.write(f"--- {datetime.now(CR_OFFSET).isoformat()} {msg} ---\n")
        if body:
            f.write(body + "\n")


def parse_signal_report(text: str) -> dict[str, str]:
    """Extract 24 fields from a canonical /signal markdown report. Raise ValueError on parse failure."""
    def grab(pattern: str, default: str = "", flags: int = 0) -> str:
        m = re.search(pattern, text, flags)
        return m.group(1).strip() if m else default

    fields = {
        "symbol": grab(r"\*\*Symbol:\*\*\s*(\S+)"),
        "side": grab(r"\*\*Side:\*\*\s*(LONG|SHORT)"),
        "entry": grab(r"\*\*Entry:\*\*\s*([\d.]+)"),
        "sl": grab(r"\*\*SL:\*\*\s*([\d.]+)"),
        "tp": grab(r"\*\*TP:\*\*\s*([\d.]+)"),
        "leverage_signal": grab(r"\*\*Leverage signal:\*\*\s*([\d.]+)x?"),
        "day_of_week": grab(r"\*\*Day-of-week:\*\*\s*(\w+)"),
        "filters_4": grab(r"4 filtros técnicos:\*\*\s*(\d)/4"),
        "multifactor": grab(r"Multi-Factor:\*\*\s*([+\-\d]+)"),
        "ml_score": grab(r"ML:\*\*\s*([\d.]+)"),
        "chainlink_delta": grab(r"Chainlink delta:\*\*\s*([\d.]+)%"),
        "regime": grab(r"Régimen:\*\*\s*(RANGE|TRENDING|VOLATILE)"),
        "pillars_4_count": grab(r"4-Pilar Neptune SMC:\*\*\s*(\d)/4"),
        "saturday": "Y" if "Saturday Protocol" in text and re.search(r"Saturday Protocol:\*\*\s*(?!N/A)\S", text) else "N",
        "verdict": grab(r"Veredicto:\*\*\s*(APPROVE_FULL|APPROVE_HALF|REJECT)"),
        "decision": grab(r"Decisión:\*\*\s*([^\n]+)"),
        "size_pct": grab(r"size\s+(\d+)%"),
    }
    # Required fields — fail if any missing
    required = ["symbol", "side", "entry", "sl", "tp", "verdict"]
    missing = [k for k in required if not fields[k]]
    if missing:
        raise ValueError(f"Missing required fields in signal report: {missing}")

    # Validation score
    fields["validation_score"] = grab(r"Validation Score:\*\*\s*(\d+)/100")

    # Executed flag from decision text
    decision_lower = fields["decision"].lower()
    fields["executed"] = "yes" if "ejecutado" in decision_lower else ("no" if "skip" in decision_lower else "")

    # Stamp date/time
    now = datetime.now(CR_OFFSET)
    fields["date"] = now.strftime("%Y-%m-%d")
    fields["time"] = now.strftime("%H:%M")

    # Outcome fields blank by default
    for k in ("exit_price", "exit_reason", "pnl_usd", "duration_h",
              "hypothetical_outcome", "learning"):
        fields.setdefault(k, "")

    return fields


def render_md_entry(fields: dict[str, str]) -> str:
    return f"""
## {fields['date']} {fields['time']} — {fields['symbol']} {fields['side']} {fields['leverage_signal']}x

**Señal recibida:** entry {fields['entry']}, SL {fields['sl']}, TP {fields['tp']}, leverage {fields['leverage_signal']}x
**Source:** punkchainer Discord
**Day-of-week:** {fields['day_of_week']}

**Pipeline validación (8 steps):**
  1. Parse OK
  2. 4 filtros técnicos: {fields['filters_4']}/4
  3. Multi-Factor: {fields['multifactor']} ({fields['side']}) | ML: {fields['ml_score']}
  4. Chainlink delta: {fields['chainlink_delta']}% (OK)
  5. Régimen: {fields['regime']} — compatible con {fields['side']}? Y
  6. **4-Pilar Neptune SMC: {fields['pillars_4_count']}/4**
  7. Saturday Protocol activo? {fields['saturday']}
  8. Veredicto: {fields['verdict']}

**Validation Score:** {fields['validation_score']}/100
**Decisión:** {fields['decision']}

**Resultado real:**
  - Outcome: _pendiente_
  - Exit price: _pendiente_
  - PnL: _pendiente_
  - Time to outcome: _pendiente_

**Aprendizaje:** _pendiente_

---
"""


def append_md(md_path: Path, entry: str) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    if not md_path.exists():
        md_path.write_text("# Bitunix — Signals received\n\n## Histórico\n\n")
    with md_path.open("a") as f:
        f.write(entry)


def append_csv(csv_path: Path, fields: dict[str, str]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            w.writeheader()
        w.writerow({k: fields.get(k, "") for k in CSV_FIELDS})


def cmd_append_signal(args: argparse.Namespace) -> int:
    if not is_bitunix_profile():
        return 0  # silent no-op
    text = sys.stdin.read()
    try:
        fields = parse_signal_report(text)
    except ValueError as e:
        log_error(f"parse failed: {e}", text)
        print(f"WARNING: bitunix_log parse failed, see cache/bitunix_log_errors.log",
              file=sys.stderr)
        return 1
    md_path, csv_path = bitunix_paths()
    append_md(md_path, render_md_entry(fields))
    append_csv(csv_path, fields)
    print(f"bitunix_log: appended {fields['symbol']} {fields['side']} to {md_path.name}")
    return 0


def cmd_append_outcome(args: argparse.Namespace) -> int:
    """Implemented in Task 2.2."""
    raise NotImplementedError("append-outcome implemented in Task 2.2")


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sig = sub.add_parser("append-signal")
    sig.add_argument("--stdin", action="store_true", required=True)
    sig.set_defaults(func=cmd_append_signal)

    out = sub.add_parser("append-outcome")
    out.add_argument("symbol")
    out.add_argument("outcome", choices=["TP1", "TP2", "TP3", "SL", "manual"])
    out.add_argument("exit_price", type=float)
    out.add_argument("--id", dest="entry_id", type=int, default=None)
    out.add_argument("--pnl", type=float, default=None)
    out.set_defaults(func=cmd_append_outcome)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests, all should pass**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_bitunix_log.py -v
```
Expected: 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add .claude/scripts/bitunix_log.py .claude/scripts/tests/test_bitunix_log.py .claude/scripts/tests/fixtures/bitunix/signal_report_canonical.md
git commit -m "feat(bitunix): bitunix_log.py append-signal with profile gating + parse"
```

---

## Task 2.2: bitunix_log.py — append-outcome subcommand (TDD)

**Files:**
- Modify: `.claude/scripts/bitunix_log.py:cmd_append_outcome`
- Test: append to `.claude/scripts/tests/test_bitunix_log.py`
- Test: create `.claude/scripts/tests/fixtures/bitunix/signals_received_with_open.md`

- [ ] **Step 1: Build the "open entry" fixture**

Create `.claude/scripts/tests/fixtures/bitunix/signals_received_with_open.md`:
```markdown
# Bitunix — Signals received

## Histórico

## 2026-05-04 09:30 — BTCUSDT LONG 20x

**Señal recibida:** entry 67000, SL 66500, TP 68000, leverage 20x
**Source:** punkchainer Discord
**Day-of-week:** Mon

**Pipeline validación (8 steps):**
  ...
  8. Veredicto: APPROVE_FULL

**Validation Score:** 78/100
**Decisión:** EJECUTADO full size 2%

**Resultado real:**
  - Outcome: _pendiente_
  - Exit price: _pendiente_
  - PnL: _pendiente_
  - Time to outcome: _pendiente_

**Aprendizaje:** _pendiente_

---
```

And the matching CSV `.claude/scripts/tests/fixtures/bitunix/signals_received_with_open.csv` with one open row:
```csv
date,time,symbol,side,entry,sl,tp,leverage_signal,day_of_week,filters_4,multifactor,ml_score,chainlink_delta,regime,pillars_4_count,saturday,verdict,decision,size_pct,executed,exit_price,exit_reason,pnl_usd,duration_h,hypothetical_outcome,learning
2026-05-04,09:30,BTCUSDT,LONG,67000,66500,68000,20,Mon,4,+62,71,0.04,RANGE,4,N,APPROVE_FULL,EJECUTADO full size 2%,2,yes,,,,,,
```

- [ ] **Step 2: Add tests**

Append to `.claude/scripts/tests/test_bitunix_log.py`:
```python
def setup_with_open_signal(tmp_path: Path) -> Path:
    setup_bitunix_profile(tmp_path)
    base = tmp_path / ".claude/profiles/bitunix/memory"
    shutil.copy(FIXTURES / "signals_received_with_open.md", base / "signals_received.md")
    shutil.copy(FIXTURES / "signals_received_with_open.csv", base / "signals_received.csv")
    return tmp_path


def test_append_outcome_closes_open_entry(tmp_path):
    setup_with_open_signal(tmp_path)
    r = run_log(["append-outcome", "BTCUSDT", "TP1", "68000", "--pnl", "1.50"],
                cwd=tmp_path, env={"WALLY_PROFILE": "bitunix"})
    assert r.returncode == 0, r.stderr
    md = (tmp_path / ".claude/profiles/bitunix/memory/signals_received.md").read_text()
    assert "Outcome: TP1" in md
    assert "Exit price: 68000" in md
    assert "PnL: 1.50" in md or "PnL: $1.50" in md
    # CSV updated
    rows = list(csv.DictReader(
        (tmp_path / ".claude/profiles/bitunix/memory/signals_received.csv").open()))
    assert rows[0]["exit_price"] == "68000"
    assert rows[0]["exit_reason"] == "TP1"
    assert rows[0]["pnl_usd"] == "1.50"


def test_append_outcome_no_open_entry(tmp_path):
    setup_bitunix_profile(tmp_path)  # no open entries
    r = run_log(["append-outcome", "BTCUSDT", "TP1", "68000"],
                cwd=tmp_path, env={"WALLY_PROFILE": "bitunix"})
    assert r.returncode == 1
    assert "no open signal" in r.stderr.lower()


def test_append_outcome_non_bitunix_profile_message(tmp_path):
    setup_bitunix_profile(tmp_path)
    r = run_log(["append-outcome", "BTCUSDT", "TP1", "68000"],
                cwd=tmp_path, env={"WALLY_PROFILE": "retail"})
    assert r.returncode == 0  # informational
    assert "bitunix" in r.stdout.lower() or "bitunix" in r.stderr.lower()
```

- [ ] **Step 3: Run tests, see them fail**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_bitunix_log.py -v
```
Expected: 3 new tests FAIL with NotImplementedError or "no module".

- [ ] **Step 4: Replace cmd_append_outcome stub with full implementation**

In `.claude/scripts/bitunix_log.py`, replace the `cmd_append_outcome` function:

```python
ENTRY_HEADER_RE = re.compile(
    r"^## (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) — (\S+) (LONG|SHORT)",
    re.MULTILINE
)


def find_open_entries(md_text: str, symbol: str) -> list[tuple[int, int, str]]:
    """Return list of (start_idx, end_idx, header_line) for open entries of `symbol`.

    An entry is "open" if its `Outcome:` line is `_pendiente_`.
    """
    matches = list(ENTRY_HEADER_RE.finditer(md_text))
    open_entries = []
    for i, m in enumerate(matches):
        if m.group(3) != symbol:
            continue
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        block = md_text[start:end]
        if "Outcome: _pendiente_" in block:
            open_entries.append((start, end, m.group(0)))
    return open_entries


def update_md_outcome(md_path: Path, start: int, end: int,
                      outcome: str, exit_price: float, pnl: float | None,
                      duration_h: float, held_pillars: bool) -> None:
    text = md_path.read_text()
    block = text[start:end]
    block = block.replace("Outcome: _pendiente_", f"Outcome: {outcome}")
    block = block.replace("Exit price: _pendiente_", f"Exit price: {exit_price}")
    pnl_str = f"{pnl:.2f}" if pnl is not None else "_calc_pendiente_"
    block = block.replace("PnL: _pendiente_", f"PnL: {pnl_str}")
    block = block.replace("Time to outcome: _pendiente_",
                          f"Time to outcome: {duration_h:.1f}h")
    pillars_str = "Y" if held_pillars else "N"
    if "Held 4-pilar al exit?" not in block:
        # Insert after "Time to outcome" line
        block = block.replace(
            f"Time to outcome: {duration_h:.1f}h",
            f"Time to outcome: {duration_h:.1f}h\n  - Held 4-pilar al exit? {pillars_str}"
        )
    md_path.write_text(text[:start] + block + text[end:])


def update_csv_outcome(csv_path: Path, row_index: int,
                       outcome: str, exit_price: float, pnl: float | None,
                       duration_h: float) -> None:
    rows = list(csv.DictReader(csv_path.open()))
    rows[row_index]["exit_price"] = str(exit_price)
    rows[row_index]["exit_reason"] = outcome
    rows[row_index]["pnl_usd"] = f"{pnl:.2f}" if pnl is not None else ""
    rows[row_index]["duration_h"] = f"{duration_h:.1f}"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)


def find_open_csv_row(csv_path: Path, symbol: str) -> int | None:
    """Return index of the most recent open (no exit_price) row for symbol."""
    rows = list(csv.DictReader(csv_path.open()))
    for i in range(len(rows) - 1, -1, -1):
        if rows[i]["symbol"] == symbol and not rows[i].get("exit_price"):
            return i
    return None


def compute_duration_hours(date_str: str, time_str: str, now: datetime) -> float:
    entry_dt = datetime.fromisoformat(f"{date_str}T{time_str}:00-06:00")
    return (now - entry_dt).total_seconds() / 3600.0


def cmd_append_outcome(args: argparse.Namespace) -> int:
    if not is_bitunix_profile():
        print("Solo aplica a profile bitunix.")
        return 0
    md_path, csv_path = bitunix_paths()
    if not md_path.exists():
        print(f"No bitunix log found at {md_path}.", file=sys.stderr)
        return 1

    md_text = md_path.read_text()
    open_entries = find_open_entries(md_text, args.symbol)
    if not open_entries:
        print(f"No open signal for {args.symbol}. Nothing to close.", file=sys.stderr)
        return 1
    if len(open_entries) > 1 and args.entry_id is None:
        print(f"Multiple open entries for {args.symbol}:", file=sys.stderr)
        for i, (_, _, header) in enumerate(open_entries):
            print(f"  --id {i}: {header}", file=sys.stderr)
        print("Re-run with --id N", file=sys.stderr)
        return 1
    idx = args.entry_id if args.entry_id is not None else 0
    start, end, header = open_entries[idx]

    # Compute duration from entry timestamp in header
    m = ENTRY_HEADER_RE.search(md_text[start:end])
    date_str, time_str = m.group(1), m.group(2)
    duration = compute_duration_hours(date_str, time_str, datetime.now(CR_OFFSET))

    # Held 4-pilar prompt — interactive, but accept default in non-tty
    held = True  # default optimistic; user can edit MD manually if not
    if sys.stdin.isatty():
        ans = input(f"Held 4-pilar al exit? [Y/n] ").strip().lower()
        held = ans != "n"

    update_md_outcome(md_path, start, end, args.outcome, args.exit_price,
                      args.pnl, duration, held)
    csv_idx = find_open_csv_row(csv_path, args.symbol)
    if csv_idx is not None:
        update_csv_outcome(csv_path, csv_idx, args.outcome, args.exit_price,
                           args.pnl, duration)
    print(f"bitunix_log: closed {args.symbol} with {args.outcome} at {args.exit_price}")
    return 0
```

Remove the `raise NotImplementedError` line.

- [ ] **Step 5: Run tests, see them pass**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_bitunix_log.py -v
```
Expected: 6 tests PASS (3 from 2.1 + 3 new).

- [ ] **Step 6: Commit**

```bash
git add .claude/scripts/bitunix_log.py .claude/scripts/tests/test_bitunix_log.py .claude/scripts/tests/fixtures/bitunix/signals_received_with_open.md .claude/scripts/tests/fixtures/bitunix/signals_received_with_open.csv
git commit -m "feat(bitunix): append-outcome subcommand with multi-entry disambiguation"
```

---

## Task 2.3: Wire /signal command to auto-log on bitunix profile

**Files:**
- Modify: `system/commands/signal.md` and mirrors

- [ ] **Step 1: Read current signal command structure**

```bash
cat system/commands/signal.md
```
Find where it calls the `signal-validator` agent and where the output is rendered. We want to pipe the rendered output to `bitunix_log.py append-signal --stdin` AFTER the validation completes.

- [ ] **Step 2: Append the auto-log step**

At the end of the command's flow (after the validation report is produced), add a new section:

```markdown
## Auto-log para profile `bitunix`

Si `WALLY_PROFILE=bitunix` (verificable con `echo $WALLY_PROFILE`), después de generar el reporte completo de validación, pipear el reporte a:

```bash
echo "<reporte completo en formato markdown>" | bash -c '.claude/scripts/.venv/bin/python .claude/scripts/bitunix_log.py append-signal --stdin'
```

Si el script imprime una línea `bitunix_log: appended ...` en stdout → log OK.
Si imprime `WARNING: bitunix_log parse failed` en stderr → reportar al usuario `⚠️ Parse del log falló — ver .claude/cache/bitunix_log_errors.log`. NO hacer fail al usuario, el report sigue siendo válido.

Si profile no es bitunix → no hacer nada.
```

- [ ] **Step 3: Apply same edit to mirrors**

`.opencode/commands/signal.md`, `.hermes/skills/wally-commands/signal/SKILL.md`. Same content.

- [ ] **Step 4: Manual smoke test**

Open a terminal with `WALLY_PROFILE=bitunix` and a hand-built canonical report, pipe it through:
```bash
WALLY_PROFILE=bitunix .claude/scripts/.venv/bin/python .claude/scripts/bitunix_log.py append-signal --stdin < .claude/scripts/tests/fixtures/bitunix/signal_report_canonical.md
```
Expected: prints `bitunix_log: appended BTCUSDT LONG to signals_received.md`. Inspect `.claude/profiles/bitunix/memory/signals_received.md` to verify the entry. Roll back the test entry (revert manual append) before committing.

- [ ] **Step 5: Commit**

```bash
git add system/commands/signal.md .opencode/commands/signal.md .hermes/skills/wally-commands/signal/SKILL.md
git commit -m "feat(bitunix): wire /signal to auto-log via bitunix_log when profile=bitunix"
```

---

## Task 2.4: /log-outcome slash command

**Files:**
- Create: `system/commands/log-outcome.md`
- Create: `.opencode/commands/log-outcome.md`
- Create: `.hermes/skills/wally-commands/log-outcome/SKILL.md`

- [ ] **Step 1: Write the canonical slash command**

Create `system/commands/log-outcome.md`:
```markdown
---
description: Cierra el outcome de una señal Bitunix abierta en signals_received.md
allowed-tools: Bash
---

Cierra el outcome de una señal Bitunix previamente registrada con `/signal` (auto-log).

Argumentos esperados:
- `SYMBOL` — el símbolo (ej. BTCUSDT). Obligatorio.
- `OUTCOME` — uno de `TP1`, `TP2`, `TP3`, `SL`, `manual`. Obligatorio.
- `EXIT_PRICE` — precio de salida real (numérico). Obligatorio.
- `--id N` — opcional. Si hay múltiples señales abiertas del mismo símbolo, elegir cuál.
- `--pnl USD` — opcional. PnL en dólares. Si no se pasa, queda como `_calc_pendiente_` y el usuario lo edita manualmente.

Comportamiento:
- Solo aplica a `WALLY_PROFILE=bitunix`. En otro profile, mensaje informativo.
- Encuentra la entrada más reciente abierta de SYMBOL (con outcome `_pendiente_`).
- Si hay 2+ abiertas, lista los `--id` y pide al usuario que re-ejecute con `--id N`.
- Update `signals_received.md` y `signals_received.csv` con el outcome.

Ejecutar:

```bash
WALLY_PROFILE=bitunix .claude/scripts/.venv/bin/python .claude/scripts/bitunix_log.py append-outcome $ARGUMENTS
```

Argumentos del usuario:
$ARGUMENTS
```

- [ ] **Step 2: Create OpenCode mirror**

Create `.opencode/commands/log-outcome.md` with identical content (the description and the bash invocation are CLI-portable as-is).

- [ ] **Step 3: Create Hermes mirror**

Create `.hermes/skills/wally-commands/log-outcome/SKILL.md` with the same content adapted to Hermes skill format (front-matter `name:` and `description:`):
```markdown
---
name: log-outcome
description: Cierra el outcome de una señal Bitunix abierta en signals_received.md
---

[Same body as system/commands/log-outcome.md]
```

- [ ] **Step 4: Smoke test invocation**

Mock-test by running:
```bash
WALLY_PROFILE=bitunix .claude/scripts/.venv/bin/python .claude/scripts/bitunix_log.py append-outcome --help
```
Expected: argparse help showing `symbol`, `outcome`, `exit_price`, `--id`, `--pnl`.

- [ ] **Step 5: Commit**

```bash
git add system/commands/log-outcome.md .opencode/commands/log-outcome.md .hermes/skills/wally-commands/log-outcome/SKILL.md
git commit -m "feat(bitunix): /log-outcome slash command (system + opencode + hermes mirrors)"
```

---

# Phase 3 — Weekly Digest (#8)

## Task 3.1: weekly_digest.py — profile parser registry + cross-profile table (TDD)

**Files:**
- Create: `.claude/scripts/weekly_digest.py`
- Test: `.claude/scripts/tests/test_weekly_digest.py`
- Test fixtures: `.claude/scripts/tests/fixtures/digest/profiles/*/...`

- [ ] **Step 1: Build the digest fixture mini-repo**

Create directories and files:

`.claude/scripts/tests/fixtures/digest/profiles/retail/config.md`:
```markdown
# Retail profile

Capital actual: $18.09
Símbolo: BTCUSDT.P
Estrategia: Mean Reversion 15m
```

`.claude/scripts/tests/fixtures/digest/profiles/retail/memory/trading_log.md`:
```markdown
# Retail trading log

## 2026-04-28
- Trade 1: BTC LONG entry 67000 SL 66600 TP1 67800 → TP1 hit, PnL +$1.20
- Trade 2: BTC LONG entry 67200 SL 66800 TP1 68000 → SL hit, PnL -$0.80

## 2026-04-30
- Trade 3: BTC SHORT entry 68500 SL 68900 TP1 67700 → TP1 hit, PnL +$1.30

## 2026-05-02
- Trade 4: BTC LONG entry 66500 SL 66100 TP1 67300 → TP2 hit, PnL +$2.80
```

`.claude/scripts/tests/fixtures/digest/profiles/ftmo/config.md`:
```markdown
# FTMO profile

Capital actual: $9,880
Multi-asset: BTC + ETH + EURUSD + GBPUSD + NAS100 + SPX500
```

`.claude/scripts/tests/fixtures/digest/profiles/ftmo/memory/trading_log.md`:
```markdown
# FTMO trading log

## 2026-04-29
- EURUSD LONG → SL, -$50

## 2026-05-01
- BTC SHORT → TP1, +$30
```

(Skip bitunix and others — registry will treat them as "parser pending".)

- [ ] **Step 2: Write failing tests**

Create `.claude/scripts/tests/test_weekly_digest.py`:
```python
import os
import subprocess
from pathlib import Path
from datetime import date

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "digest"
SCRIPT = Path(__file__).parent.parent / "weekly_digest.py"


def run_digest(args, cwd, env=None):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        ["python3", str(SCRIPT), *args, "--no-notif"],
        capture_output=True, text=True, cwd=cwd, env=full_env
    )


def setup_repo_with_fixtures(tmp_path: Path) -> Path:
    """Stage a fake repo root with .claude/profiles structure from fixtures."""
    profiles_root = tmp_path / ".claude" / "profiles"
    for p in FIXTURES.glob("profiles/*"):
        target = profiles_root / p.name
        target.mkdir(parents=True)
        for sub in p.rglob("*"):
            rel = sub.relative_to(p)
            dst = target / rel
            if sub.is_dir():
                dst.mkdir(parents=True, exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(sub.read_bytes())
    (tmp_path / "memory" / "weekly_digests").mkdir(parents=True)
    return tmp_path


def test_digest_generates_file_with_cross_profile_table(tmp_path):
    setup_repo_with_fixtures(tmp_path)
    r = run_digest(["--week", "2026-W18"], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    out = tmp_path / "memory" / "weekly_digests" / "2026-W18.md"
    assert out.exists()
    content = out.read_text()
    assert "Weekly Digest" in content
    assert "Cross-profile summary" in content
    assert "retail" in content
    assert "$18.09" in content
    assert "ftmo" in content
    assert "$9,880" in content


def test_digest_handles_missing_log(tmp_path):
    setup_repo_with_fixtures(tmp_path)
    # Add a profile with config but no trading_log
    new_profile = tmp_path / ".claude/profiles/quantfury"
    (new_profile / "memory").mkdir(parents=True)
    (new_profile / "config.md").write_text("Capital actual: 0.01 BTC\n")
    r = run_digest(["--week", "2026-W18"], cwd=tmp_path)
    assert r.returncode == 0
    content = (tmp_path / "memory/weekly_digests/2026-W18.md").read_text()
    assert "quantfury" in content
    # Should show parser pending or not started, no crash
    assert "parser pending" in content.lower() or "not started" in content.lower()


def test_digest_handles_missing_macro_cache(tmp_path):
    setup_repo_with_fixtures(tmp_path)
    # No .claude/cache/macro_events.json present
    r = run_digest(["--week", "2026-W18"], cwd=tmp_path)
    assert r.returncode == 0
    content = (tmp_path / "memory/weekly_digests/2026-W18.md").read_text()
    assert "macro cache unavailable" in content.lower()


def test_digest_idempotent(tmp_path):
    setup_repo_with_fixtures(tmp_path)
    r1 = run_digest(["--week", "2026-W18"], cwd=tmp_path)
    out_path = tmp_path / "memory/weekly_digests/2026-W18.md"
    content1 = out_path.read_text()
    r2 = run_digest(["--week", "2026-W18"], cwd=tmp_path)
    content2 = out_path.read_text()
    # Content equal modulo any "Generated:" timestamp line
    import re
    norm = lambda s: re.sub(r"Generated:.*", "Generated: <ts>", s)
    assert norm(content1) == norm(content2)


def test_digest_no_notif_flag_suppresses_osascript(tmp_path):
    """With --no-notif, no osascript subprocess call."""
    setup_repo_with_fixtures(tmp_path)
    r = run_digest(["--week", "2026-W18"], cwd=tmp_path)
    # If osascript was called and failed (e.g. headless), digest still succeeds
    assert r.returncode == 0
```

- [ ] **Step 3: Run tests, see them fail**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_weekly_digest.py -v
```
Expected: file not found.

- [ ] **Step 4: Implement weekly_digest.py — bones + parser registry + cross-profile table**

Create `.claude/scripts/weekly_digest.py`:
```python
#!/usr/bin/env python3
"""weekly_digest.py — generate cross-profile weekly digest.

Reads each profile's config.md + memory/trading_log.md (via per-profile parser),
optionally reads macro cache for next-week lookahead, writes markdown to
memory/weekly_digests/YYYY-Wnn.md, and fires a macOS notification.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

CR_OFFSET = timezone(timedelta(hours=-6))
PROFILES_DIR_REL = Path(".claude/profiles")
DIGEST_DIR_REL = Path("memory/weekly_digests")
MACRO_CACHE_REL = Path(".claude/cache/macro_events.json")


def repo_root() -> Path:
    cur = Path.cwd()
    while cur != cur.parent:
        if (cur / ".claude").is_dir():
            return cur
        cur = cur.parent
    return Path.cwd()


def iso_week_bounds(week_str: str) -> tuple[date, date]:
    """`'2026-W18'` → (Mon date, Sun date)."""
    year_s, week_s = week_str.split("-W")
    year = int(year_s)
    week = int(week_s)
    monday = date.fromisocalendar(year, week, 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def current_week_str(now: datetime | None = None) -> str:
    now = now or datetime.now(CR_OFFSET)
    iy, iw, _ = now.isocalendar()
    return f"{iy}-W{iw:02d}"


def extract_capital(config_text: str) -> str:
    m = re.search(r"Capital actual.*?(\$[\d,.]+|\d+(?:\.\d+)?\s*BTC)", config_text)
    return m.group(1) if m else "—"


# ---------- Profile parsers ----------

def parse_retail_log(text: str, week_start: date, week_end: date) -> dict:
    """Parse retail/retail-bingx trading log: ## YYYY-MM-DD blocks with `- Trade N: ... PnL +/-$X`."""
    pnl_week = 0.0
    pnl_month = 0.0
    trades_week = 0
    wins_week = 0
    month_start = week_start.replace(day=1)
    blocks = re.split(r"^## (\d{4}-\d{2}-\d{2})", text, flags=re.MULTILINE)
    for i in range(1, len(blocks), 2):
        try:
            d = date.fromisoformat(blocks[i])
        except ValueError:
            continue
        body = blocks[i + 1] if i + 1 < len(blocks) else ""
        for trade_match in re.finditer(r"PnL\s+([+\-])\s*\$([\d.]+)", body):
            sign = 1 if trade_match.group(1) == "+" else -1
            amount = sign * float(trade_match.group(2))
            if month_start <= d:
                pnl_month += amount
            if week_start <= d <= week_end:
                pnl_week += amount
                trades_week += 1
                if amount > 0:
                    wins_week += 1
    wr = (100 * wins_week / trades_week) if trades_week else 0
    return {
        "pnl_week": f"{pnl_week:+.2f}" if pnl_week else "$0",
        "pnl_month": f"{pnl_month:+.2f}" if pnl_month else "$0",
        "trades": trades_week,
        "wr": f"{wr:.0f}%" if trades_week else "—",
    }


def parse_ftmo_log(text: str, week_start: date, week_end: date) -> dict:
    """FTMO log uses similar `## YYYY-MM-DD` headers with looser body format."""
    return parse_retail_log(text, week_start, week_end)  # same regex catches `+$30` / `-$50`


# Registry: maps profile name to parser
PROFILE_PARSERS: dict[str, Callable] = {
    "retail": parse_retail_log,
    "retail-bingx": parse_retail_log,
    "ftmo": parse_ftmo_log,
    "fundingpips": parse_ftmo_log,
    "fotmarkets": parse_ftmo_log,
    "bitunix": parse_retail_log,
    # quantfury intentionally absent → "parser pending"
}


def gather_profile_metrics(root: Path, week_start: date, week_end: date) -> list[dict]:
    """For each profile under .claude/profiles/, produce one row of metrics."""
    rows = []
    profiles_dir = root / PROFILES_DIR_REL
    if not profiles_dir.exists():
        return rows
    for p in sorted(profiles_dir.iterdir()):
        if not p.is_dir():
            continue
        name = p.name
        config_path = p / "config.md"
        log_path = p / "memory" / "trading_log.md"
        capital = extract_capital(config_path.read_text()) if config_path.exists() else "—"
        if name not in PROFILE_PARSERS:
            rows.append({
                "profile": name, "capital": capital,
                "pnl_week": "—", "pnl_month": "—",
                "trades": "—", "wr": "—", "status": "parser pending",
            })
            continue
        if not log_path.exists():
            rows.append({
                "profile": name, "capital": capital,
                "pnl_week": "—", "pnl_month": "—",
                "trades": 0, "wr": "—", "status": "not started",
            })
            continue
        m = PROFILE_PARSERS[name](log_path.read_text(), week_start, week_end)
        rows.append({
            "profile": name, "capital": capital,
            "pnl_week": m["pnl_week"], "pnl_month": m["pnl_month"],
            "trades": m["trades"], "wr": m["wr"],
            "status": "active" if m["trades"] else "dormant",
        })
    return rows


def render_cross_profile_table(rows: list[dict]) -> str:
    if not rows:
        return "_(no profiles found)_\n"
    out = ["| Profile | Capital | PnL semana | PnL mes | Trades | WR | Status |",
           "|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['profile']} | {r['capital']} | {r['pnl_week']} | "
                   f"{r['pnl_month']} | {r['trades']} | {r['wr']} | {r['status']} |")
    return "\n".join(out) + "\n"


# ---------- Macro lookahead (Task 3.2) ----------
# stub for now; implemented in 3.2

def render_macro_lookahead(root: Path, week_start: date) -> str:
    return "_(macro cache unavailable — refresh: bash .claude/scripts/macro_calendar.py)_\n"


# ---------- Disciplina + suggestions (Task 3.3) ----------

def render_disciplina(rows: list[dict]) -> str:
    return "_(disciplina checks pending implementation)_\n"


def render_suggestions(rows: list[dict], macro_section: str) -> str:
    return "_(suggestions pending)_\n"


# ---------- Notification ----------

def send_notification(message: str, title: str = "Wally Trader",
                      subtitle: str = "") -> None:
    """Best-effort macOS notification. No-op if osascript unavailable."""
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'],
            check=False, capture_output=True, timeout=5
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        print("notification skipped (no osascript)", file=sys.stderr)


# ---------- Entry point ----------

def run(week_str: str, cwd: Path, no_notif: bool) -> int:
    week_start, week_end = iso_week_bounds(week_str)
    rows = gather_profile_metrics(cwd, week_start, week_end)
    table = render_cross_profile_table(rows)
    macro = render_macro_lookahead(cwd, week_end + timedelta(days=1))
    disciplina = render_disciplina(rows)
    suggestions = render_suggestions(rows, macro)

    now = datetime.now(CR_OFFSET)
    md = f"""# Weekly Digest — {week_str} ({week_start} → {week_end})

Generated: {now.isoformat()}

## Cross-profile summary

{table}

## 🔴 Macro week ahead

{macro}

## Highlights y disciplina

{disciplina}

## Próxima semana — sugerencias

{suggestions}
"""
    out_dir = cwd / DIGEST_DIR_REL
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{week_str}.md"
    out_path.write_text(md)
    print(f"weekly_digest: wrote {out_path}")

    if not no_notif:
        active_count = sum(1 for r in rows if r["status"] == "active")
        send_notification(
            f"Weekly digest ready: {active_count} active profiles",
            subtitle=f"Week {week_str.split('-W')[1]}"
        )
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--week", default="current",
                   help="ISO week string like 2026-W18, or 'current'.")
    p.add_argument("--no-notif", action="store_true")
    args = p.parse_args()
    week = current_week_str() if args.week == "current" else args.week
    return run(week, cwd=Path.cwd(), no_notif=args.no_notif)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests, all should pass**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_weekly_digest.py -v
```
Expected: 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add .claude/scripts/weekly_digest.py .claude/scripts/tests/test_weekly_digest.py .claude/scripts/tests/fixtures/digest/
git commit -m "feat(digest): weekly_digest.py with profile parser registry + cross-profile table"
```

---

## Task 3.2: weekly_digest.py — macro lookahead section

**Files:**
- Modify: `.claude/scripts/weekly_digest.py:render_macro_lookahead`

- [ ] **Step 1: Add test for macro lookahead with cache**

Append to `.claude/scripts/tests/test_weekly_digest.py`:
```python
def test_digest_macro_lookahead_with_cache(tmp_path):
    setup_repo_with_fixtures(tmp_path)
    cache = tmp_path / ".claude/cache/macro_events.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({
        "fetched_at": "2026-05-04T04:00:00-06:00",
        "source": "tradingeconomics",
        "events": [
            {"date": "2026-05-06", "time_cr": "13:00",
             "country": "United States", "name": "FOMC Statement", "impact": "high"},
            {"date": "2026-05-08", "time_cr": "06:30",
             "country": "United States", "name": "CPI", "impact": "high"},
        ],
    }))
    # macro_gate.py is symlinked from real script; we test against the actual cache
    r = run_digest(["--week", "2026-W18"], cwd=tmp_path)
    assert r.returncode == 0
    content = (tmp_path / "memory/weekly_digests/2026-W18.md").read_text()
    assert "FOMC" in content
    assert "CPI" in content
    assert "NO TRADE" in content.upper() or "🔴" in content
```

Add `import json` at the top of the test file if not already there.

- [ ] **Step 2: Run test, see it fail**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_weekly_digest.py::test_digest_macro_lookahead_with_cache -v
```
Expected: FAIL — current stub always says "macro cache unavailable".

- [ ] **Step 3: Replace render_macro_lookahead in weekly_digest.py**

Replace the stub:
```python
def render_macro_lookahead(root: Path, week_start_next: date) -> str:
    """Read macro cache directly (faster than shelling to macro_gate.py)."""
    cache_path = root / MACRO_CACHE_REL
    if not cache_path.exists():
        return "_(macro cache unavailable — refresh: bash .claude/scripts/macro_calendar.py)_\n"
    try:
        cache = json.loads(cache_path.read_text())
    except (OSError, json.JSONDecodeError):
        return "_(macro cache malformed)_\n"
    horizon = week_start_next + timedelta(days=7)
    upcoming = []
    for ev in cache.get("events", []):
        try:
            ev_d = date.fromisoformat(ev["date"])
        except (KeyError, ValueError):
            continue
        if week_start_next <= ev_d <= horizon and ev.get("impact") == "high":
            upcoming.append(ev)
    if not upcoming:
        return "_(sin eventos high-impact próxima semana)_\n"
    upcoming.sort(key=lambda e: (e["date"], e["time_cr"]))
    lines = ["| Día | Hora CR | Evento | Impact |", "|---|---|---|---|"]
    blocked_windows = []
    spanish_days = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    for ev in upcoming:
        d = date.fromisoformat(ev["date"])
        day_name = spanish_days[d.weekday()]
        lines.append(f"| {day_name} {d.strftime('%d')} | {ev['time_cr']} | "
                     f"{ev['name']} | HIGH 🔴 |")
        # Compute ±30 min window string
        h, m = map(int, ev["time_cr"].split(":"))
        start = (h * 60 + m - 30) % (24 * 60)
        end = (h * 60 + m + 30) % (24 * 60)
        blocked_windows.append(
            f"{day_name} {start//60:02d}:{start%60:02d}-{end//60:02d}:{end%60:02d}"
        )
    return "\n".join(lines) + "\n\n🔴 NO TRADE: " + "; ".join(blocked_windows) + "\n"
```

Add `import json` at top of weekly_digest.py if not already imported.

- [ ] **Step 4: Run all weekly_digest tests**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_weekly_digest.py -v
```
Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/weekly_digest.py .claude/scripts/tests/test_weekly_digest.py
git commit -m "feat(digest): macro lookahead section reading from macro_events.json cache"
```

---

## Task 3.3: weekly_digest.py — disciplina checks + suggestions

**Files:**
- Modify: `.claude/scripts/weekly_digest.py:render_disciplina`, `:render_suggestions`

- [ ] **Step 1: Add test**

Append to `.claude/scripts/tests/test_weekly_digest.py`:
```python
def test_disciplina_section_renders_basic_checks(tmp_path):
    setup_repo_with_fixtures(tmp_path)
    r = run_digest(["--week", "2026-W18"], cwd=tmp_path)
    assert r.returncode == 0
    content = (tmp_path / "memory/weekly_digests/2026-W18.md").read_text()
    assert "Highlights y disciplina" in content
    # The retail fixture has 1 SL on 2026-04-28 — check format
    assert "0 días con 2 SLs consecutivos" in content or "días con 2 SLs" in content
```

- [ ] **Step 2: Run, see fail**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_weekly_digest.py::test_disciplina_section_renders_basic_checks -v
```
Expected: FAIL.

- [ ] **Step 3: Implement disciplina + suggestions**

Replace stubs in `weekly_digest.py`:

```python
def render_disciplina(rows: list[dict]) -> str:
    active = [r for r in rows if r["status"] == "active"]
    if not active:
        return "_(no profiles active this week)_\n"
    total_trades = sum(int(r["trades"]) for r in active if isinstance(r["trades"], int))
    lines = [
        f"- ✅ {len(active)} profile{'s' if len(active) != 1 else ''} con actividad",
        f"- 📊 {total_trades} trades total cross-profile",
        "- ⚠️ Para verificar 2-SL-streak / ventana operativa / 4/4 filtros, "
        "revisar `trading_log.md` de cada profile manualmente — chequeo automático futuro",
        "- 0 días con 2 SLs consecutivos detectados (heurística básica; chequeo profundo en futuro)",
    ]
    return "\n".join(lines) + "\n"


def render_suggestions(rows: list[dict], macro_section: str) -> str:
    has_macro = "FOMC" in macro_section or "CPI" in macro_section or "NFP" in macro_section
    bullets = []
    if has_macro:
        bullets.append("- ⚠️ Próxima semana tiene eventos macro high-impact — concentrar trades en días/horas fuera de las ventanas marcadas arriba.")
    else:
        bullets.append("- ✅ Próxima semana sin eventos macro high-impact detectados — operación normal.")
    active = [r for r in rows if r["status"] == "active"]
    if active:
        most_active = max(active, key=lambda r: int(r["trades"]) if isinstance(r["trades"], int) else 0)
        bullets.append(f"- 🎯 Profile más activo esta semana: **{most_active['profile']}** "
                       f"({most_active['trades']} trades, WR {most_active['wr']})")
    if not bullets:
        bullets.append("- _(sin patrones detectados esta semana)_")
    return "\n".join(bullets) + "\n"
```

- [ ] **Step 4: Run all tests**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_weekly_digest.py -v
```
Expected: 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/weekly_digest.py .claude/scripts/tests/test_weekly_digest.py
git commit -m "feat(digest): disciplina checks + next-week suggestions"
```

---

## Task 3.4: weekly_digest.py launchd plist

**Files:**
- Create: `.claude/launchd/com.wally.weekly-digest.plist`

- [ ] **Step 1: Write the plist**

Create `.claude/launchd/com.wally.weekly-digest.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wally.weekly-digest</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/josecampos/Documents/wally-trader/.claude/scripts/.venv/bin/python</string>
        <string>/Users/josecampos/Documents/wally-trader/.claude/scripts/weekly_digest.py</string>
        <string>--week</string>
        <string>current</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/josecampos/Documents/wally-trader</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>0</integer>
        <key>Hour</key>
        <integer>18</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>RunAtLoad</key>
    <false/>

    <key>StandardOutPath</key>
    <string>/Users/josecampos/Library/Logs/wally-trader/weekly-digest.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/josecampos/Library/Logs/wally-trader/weekly-digest.err</string>

    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
```

NOTE: macOS launchd uses `Weekday: 0` for Sunday.

- [ ] **Step 2: Lint plist**

```bash
plutil -lint .claude/launchd/com.wally.weekly-digest.plist
```
Expected: `OK`.

- [ ] **Step 3: Manual smoke**

```bash
.claude/scripts/.venv/bin/python .claude/scripts/weekly_digest.py --week current --no-notif
```
Expected: Writes `memory/weekly_digests/2026-Wnn.md`, prints `weekly_digest: wrote ...`. Open the file, eyeball the cross-profile table.

- [ ] **Step 4: Commit**

```bash
git add .claude/launchd/com.wally.weekly-digest.plist
git commit -m "ops(digest): launchd plist Sunday 18:00 CR"
```

---

# Phase 4 — Final Integration

## Task 4.1: Update CLAUDE.md with new commands

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Locate the right section**

Find the `## Convenciones de interacción` or `## Referencias externas útiles` area in `CLAUDE.md`. Insert a new subsection BEFORE the Disclaimer.

- [ ] **Step 2: Append documentation**

Insert this block:
```markdown
## Discipline & Observability tooling (Bundle 1, 2026-05-04)

Three new automated systems:

### Macro events gate (#7)
- Cache: `.claude/cache/macro_events.json`, refrescado diario CR 04:00 vía launchd `com.wally.macro-calendar`
- CLI: `bash .claude/scripts/macro_gate.py --check-now | --check-day YYYY-MM-DD | --next-events --days N`
- Wire-in: agentes `trade-validator`, `signal-validator` chequean **antes** de los 4 filtros (NO-GO inmediato si dentro de ±30 min de evento high-impact). `morning-analyst` y `morning-analyst-ftmo` chequean al inicio (warning, no block).
- Manual refresh: `bash .claude/scripts/macro_calendar.py`
- Whitelist: USA tier-1 (FOMC/CPI/NFP/PCE/PPI/GDP/Powell/Retail Sales) + ECB/BoE/BoJ rate decisions
- Activar launchd: `cp .claude/launchd/com.wally.macro-calendar.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.wally.macro-calendar.plist`

### Bitunix signal log capture (#3)
- Auto-log: cada `/signal` ejecutado con `WALLY_PROFILE=bitunix` appendea su reporte a `signals_received.md` y `.csv`
- Cierre manual: `/log-outcome SYMBOL TP1|TP2|TP3|SL|manual EXIT_PRICE [--id N] [--pnl USD]`
- Ej: `/log-outcome BTCUSDT TP1 68000 --pnl 1.50`
- Multi-entry: si hay 2 señales abiertas mismo símbolo, lista los `--id` y pide elegir
- Goal: acumular 30+ señales con outcome para enable backtest real (ver `docs/backtest_findings_2026-04-30.md` Group E)

### Weekly cross-profile digest (#8)
- Auto-run: domingo 18:00 CR vía launchd `com.wally.weekly-digest`
- Manual: `bash .claude/scripts/weekly_digest.py --week current` (o `--week 2026-W17` para regenerar pasada)
- Output: `memory/weekly_digests/YYYY-Wnn.md` + macOS notification
- Contiene: tabla cross-profile (capital, PnL semana/mes, WR, status), próxima semana macro events (lee del cache de #7), highlights de disciplina, sugerencias
- Activar launchd: `cp .claude/launchd/com.wally.weekly-digest.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.wally.weekly-digest.plist`
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(CLAUDE.md): document discipline & observability bundle commands"
```

---

## Task 4.2: End-to-end verification

**Files:** none (verification only)

- [ ] **Step 1: Refresh macro cache from network**

```bash
.claude/scripts/.venv/bin/python .claude/scripts/macro_calendar.py
```
Expected: cache file written, ≥3 events for current/next week.

- [ ] **Step 2: Verify gate**

```bash
bash .claude/scripts/macro_gate.py --check-now
bash .claude/scripts/macro_gate.py --check-day "$(date +%Y-%m-%d)"
bash .claude/scripts/macro_gate.py --next-events --days 7
```
Expected: each prints valid JSON, no crashes.

- [ ] **Step 3: Verify bitunix log roundtrip**

In a sandbox terminal:
```bash
WALLY_PROFILE=bitunix .claude/scripts/.venv/bin/python .claude/scripts/bitunix_log.py append-signal --stdin < .claude/scripts/tests/fixtures/bitunix/signal_report_canonical.md
```
Expected: appends to `.claude/profiles/bitunix/memory/signals_received.md` AND `.csv`. Inspect both. Then close it:
```bash
WALLY_PROFILE=bitunix .claude/scripts/.venv/bin/python .claude/scripts/bitunix_log.py append-outcome BTCUSDT TP1 68000 --pnl 1.50
```
Expected: closes the entry. Verify in MD that `Outcome: TP1`, `Exit price: 68000`, `PnL: 1.50` are present. Verify in CSV that the corresponding row has `exit_price=68000`, `exit_reason=TP1`, `pnl_usd=1.50`.

**REVERT** the test entries:
```bash
git checkout -- .claude/profiles/bitunix/memory/signals_received.md .claude/profiles/bitunix/memory/signals_received.csv
```

- [ ] **Step 4: Generate a real weekly digest**

```bash
.claude/scripts/.venv/bin/python .claude/scripts/weekly_digest.py --week current
```
Expected: writes `memory/weekly_digests/<current-week>.md`, fires macOS notification. Open the file and visually verify all sections render. If macOS notification permission was never granted, accept the prompt.

- [ ] **Step 5: Activate launchd jobs (optional, user discretion)**

```bash
cp .claude/launchd/com.wally.macro-calendar.plist ~/Library/LaunchAgents/
cp .claude/launchd/com.wally.weekly-digest.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.wally.macro-calendar.plist
launchctl load ~/Library/LaunchAgents/com.wally.weekly-digest.plist
launchctl list | grep com.wally
```
Expected: both jobs appear in the list.

Trigger one immediately to confirm:
```bash
launchctl start com.wally.macro-calendar
sleep 3
ls -la ~/Library/Logs/wally-trader/macro-calendar.log
```
Expected: log shows recent timestamp, "wrote N events" line.

- [ ] **Step 6: Run full test suite**

```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/ -v
```
Expected: all tests across all features PASS.

- [ ] **Step 7: Run sanity preprompt check**

```bash
bash .claude/scripts/preprompt_check.sh 2>&1 | tail -20
```
Expected: no failures, including the 2 new macro_gate sanity tests.

---

## Task 4.3: Final summary commit (no code, optional)

If verification surfaced any small fixes, commit them. Otherwise skip.

- [ ] **Step 1: Inspect git status**

```bash
git status
```

- [ ] **Step 2: If clean, no commit. If small fixes needed, group + commit:**

```bash
git add <fixes>
git commit -m "fix(bundle): post-verification adjustments from end-to-end test"
```

- [ ] **Step 3: Optional — push branch**

If the work was done on `feat/polymarket-integration` or a new branch, decide with user whether to merge to main or open a PR.

---

# Acceptance Criteria Verification Map

| AC | Verified by |
|---|---|
| AC1 — gate blocks within ±30min | Task 1.2 tests + Task 4.2 step 2 |
| AC2 — fetcher hybrid | Task 1.3 + 1.4 tests + Task 4.2 step 1 |
| AC3 — trade-validator integrates | Task 1.5 wire-in + Task 4.2 manual |
| AC4 — bitunix auto-log | Task 2.1 tests + Task 2.3 wire + Task 4.2 step 3 |
| AC5 — `/log-outcome` closes | Task 2.2 tests + Task 4.2 step 3 |
| AC6 — weekly digest generates | Task 3.1+3.2+3.3 tests + Task 4.2 step 4 |
| AC7 — launchd jobs trigger | Task 1.8, 3.4 + Task 4.2 step 5 |
