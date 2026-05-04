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
