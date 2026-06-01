"""Tests for wally_core.macro — read-only macro events cache interface."""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

CR_OFFSET = timezone(timedelta(hours=-6))


def test_default_cache_path_points_to_repo_root_cache(monkeypatch):
    """Regression: the default cache must resolve to <repo>/.claude/cache/macro_events.json.

    A wrong parents[] index silently made upcoming_relevant()/next_events() read a
    nonexistent path in production (router context), so news always came back empty.
    """
    monkeypatch.delenv("WALLY_MACRO_CACHE", raising=False)
    from wally_core import macro
    repo_root = Path(__file__).resolve().parents[3]  # tests → wally_core → shared → repo
    expected = repo_root / ".claude" / "cache" / "macro_events.json"
    assert macro._cache_path() == expected


@pytest.fixture
def macro_cache_file(tmp_path):
    """Synthetic macro_events.json with two events:
    - one 15 min in the future (within ±30 min window)
    - one 4 hours in the future (outside window)
    """
    now = datetime(2026, 5, 7, 9, 0, 0, tzinfo=CR_OFFSET)
    event_near = {
        "name": "CPI m/m",
        "country": "USA",
        "impact": "high",
        "date": "2026-05-07",
        "time_cr": "09:15",
    }
    event_far = {
        "name": "FOMC Statement",
        "country": "USA",
        "impact": "high",
        "date": "2026-05-07",
        "time_cr": "13:00",
    }
    cache = {
        "fetched_at": "2026-05-07T08:00:00-06:00",
        "events": [event_near, event_far],
    }
    f = tmp_path / "macro_events.json"
    f.write_text(json.dumps(cache))
    return f


def set_cache_env(monkeypatch, path: Path):
    monkeypatch.setenv("WALLY_MACRO_CACHE", str(path))


# ── Test 1: within window ──────────────────────────────────────────────────────

def test_is_within_event_window_returns_true_when_15_min_away(monkeypatch, macro_cache_file):
    set_cache_env(monkeypatch, macro_cache_file)
    from wally_core.macro import is_within_event_window
    now = datetime(2026, 5, 7, 9, 0, 0, tzinfo=CR_OFFSET)
    result = is_within_event_window(now, window_min=30)
    assert result["within_event"] is True
    assert "CPI" in result["event"]
    assert result["time_to_event_min"] is not None
    assert result["time_to_event_min"] <= 30


# ── Test 2: outside window ────────────────────────────────────────────────────

def test_is_within_event_window_returns_false_when_4h_away(monkeypatch, macro_cache_file):
    set_cache_env(monkeypatch, macro_cache_file)
    from wally_core.macro import is_within_event_window
    # 9:00 CR — 4h before the far event (13:00), 15 min past the near event (09:15 + already gone)
    now = datetime(2026, 5, 7, 9, 50, 0, tzinfo=CR_OFFSET)
    result = is_within_event_window(now, window_min=30)
    assert result["within_event"] is False
    assert result["event"] is None


# ── Test 3: missing cache → graceful ─────────────────────────────────────────

def test_is_within_event_window_no_cache_returns_not_blocked(monkeypatch, tmp_path):
    monkeypatch.setenv("WALLY_MACRO_CACHE", str(tmp_path / "nonexistent.json"))
    from wally_core.macro import is_within_event_window
    now = datetime(2026, 5, 7, 9, 0, 0, tzinfo=CR_OFFSET)
    result = is_within_event_window(now)
    assert result["within_event"] is False


# ── Test 4: next_events returns sorted list ───────────────────────────────────

def test_next_events_returns_events_within_horizon(monkeypatch, macro_cache_file):
    set_cache_env(monkeypatch, macro_cache_file)
    from wally_core.macro import next_events
    now = datetime(2026, 5, 7, 8, 0, 0, tzinfo=CR_OFFSET)
    events = next_events(days=1, now=now)
    assert len(events) == 2
    # Should be sorted by time
    assert events[0]["time_cr"] < events[1]["time_cr"]


# ── Test 5: next_events empty when no cache ───────────────────────────────────

def test_next_events_empty_when_no_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("WALLY_MACRO_CACHE", str(tmp_path / "nonexistent.json"))
    from wally_core.macro import next_events
    now = datetime(2026, 5, 7, 8, 0, 0, tzinfo=CR_OFFSET)
    events = next_events(days=7, now=now)
    assert events == []


# ── upcoming_relevant ─────────────────────────────────────────────────────────

@pytest.fixture
def relevant_cache_file(tmp_path):
    """Mixed cache: USD + EUR (relevant) + AUD (noise) + a far USD event."""
    cache = {
        "fetched_at": "2026-06-01T04:00:00-06:00",
        "source": "forexfactory",
        "events": [
            {"name": "ADP Employment", "country": "United States", "impact": "high",
             "date": "2026-06-01", "time_cr": "10:00"},   # USD, +6h
            {"name": "ECB Rate", "country": "Euro Area", "impact": "high",
             "date": "2026-06-01", "time_cr": "07:00"},    # EUR, +3h
            {"name": "GDP q/q", "country": "AUD", "impact": "high",
             "date": "2026-06-01", "time_cr": "08:00"},    # AUD, noise
            {"name": "Far NFP", "country": "United States", "impact": "high",
             "date": "2026-06-05", "time_cr": "06:00"},    # USD, beyond 48h
        ],
    }
    f = tmp_path / "macro_events.json"
    f.write_text(json.dumps(cache))
    return f


def test_upcoming_relevant_filters_by_currency(monkeypatch, relevant_cache_file):
    set_cache_env(monkeypatch, relevant_cache_file)
    from wally_core.macro import upcoming_relevant
    now = datetime(2026, 6, 1, 4, 0, 0, tzinfo=CR_OFFSET)
    out = upcoming_relevant({"USD", "EUR"}, hours=48, now=now)
    names = [e["name"] for e in out["events"]]
    assert "GDP q/q" not in names          # AUD filtered out
    assert "Far NFP" not in names          # beyond 48h
    assert names == ["ECB Rate", "ADP Employment"]  # sorted by time


def test_upcoming_relevant_normalizes_country_to_currency(monkeypatch, relevant_cache_file):
    set_cache_env(monkeypatch, relevant_cache_file)
    from wally_core.macro import upcoming_relevant
    now = datetime(2026, 6, 1, 4, 0, 0, tzinfo=CR_OFFSET)
    out = upcoming_relevant({"USD"}, hours=48, now=now)
    assert all(e["currency"] == "USD" for e in out["events"])
    assert {e["name"] for e in out["events"]} == {"ADP Employment"}


def test_upcoming_relevant_nearest_and_hours_until(monkeypatch, relevant_cache_file):
    set_cache_env(monkeypatch, relevant_cache_file)
    from wally_core.macro import upcoming_relevant
    now = datetime(2026, 6, 1, 4, 0, 0, tzinfo=CR_OFFSET)
    out = upcoming_relevant({"USD", "EUR"}, hours=48, now=now)
    assert out["nearest"]["name"] == "ECB Rate"
    assert out["nearest"]["hours_until"] == 3.0
    assert out["events"][1]["hours_until"] == 6.0


def test_upcoming_relevant_excludes_outside_horizon(monkeypatch, relevant_cache_file):
    set_cache_env(monkeypatch, relevant_cache_file)
    from wally_core.macro import upcoming_relevant
    now = datetime(2026, 6, 1, 4, 0, 0, tzinfo=CR_OFFSET)
    out = upcoming_relevant({"USD"}, hours=2, now=now)   # 2h window excludes ADP(+6h)
    assert out["events"] == []
    assert out["nearest"] is None


def test_upcoming_relevant_stale_flag(monkeypatch, relevant_cache_file):
    set_cache_env(monkeypatch, relevant_cache_file)
    from wally_core.macro import upcoming_relevant
    fresh = datetime(2026, 6, 1, 5, 0, 0, tzinfo=CR_OFFSET)   # +1h after fetched
    assert upcoming_relevant({"USD"}, now=fresh)["stale"] is False
    stale = datetime(2026, 6, 2, 6, 0, 0, tzinfo=CR_OFFSET)   # +26h after fetched
    assert upcoming_relevant({"USD"}, now=stale)["stale"] is True


def test_upcoming_relevant_no_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("WALLY_MACRO_CACHE", str(tmp_path / "nonexistent.json"))
    from wally_core.macro import upcoming_relevant
    now = datetime(2026, 6, 1, 4, 0, 0, tzinfo=CR_OFFSET)
    out = upcoming_relevant({"USD"}, now=now)
    assert out == {"events": [], "nearest": None, "stale": True, "source": None}
