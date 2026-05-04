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
