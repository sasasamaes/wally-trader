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


def test_fetch_te_success():
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


def test_fetch_te_429_raises():
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
         patch("macro_calendar.fetch_ff", side_effect=FetcherError("dom changed")), \
         patch("macro_calendar.log_error") as mock_log:
        rc = run(cache_path)
    assert rc == 1
    cached = json.loads(cache_path.read_text())
    assert cached["fetched_at"] == "2026-05-03T04:00:00-06:00"
    # Should have logged twice: once for TE fail, once for FF fail
    assert mock_log.call_count == 2


def test_fetch_te_json_decode_error_raises():
    """If TE returns 200 with non-JSON body (HTML error page), raise FetcherError."""
    from macro_calendar import fetch_te, FetcherError
    with patch("httpx.get") as mock_get:
        resp = MagicMock(status_code=200, text="<html>Rate limited</html>")
        resp.raise_for_status.return_value = None
        resp.json.side_effect = json.JSONDecodeError("bad json", "<html>", 0)
        mock_get.return_value = resp
        with pytest.raises(FetcherError):
            fetch_te()


def test_fetch_te_malformed_date_raises():
    """If TE returns event with Date='TBD' or None, raise FetcherError instead of crashing."""
    from macro_calendar import fetch_te, FetcherError
    bad_response = [
        {"Date": "TBD", "Country": "United States", "Event": "FOMC", "Importance": 3}
    ]
    with patch("httpx.get") as mock_get:
        resp = MagicMock(status_code=200)
        resp.raise_for_status.return_value = None
        resp.json.return_value = bad_response
        mock_get.return_value = resp
        with pytest.raises(FetcherError):
            fetch_te()


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


def test_parse_ff_response_finds_expected_high_impact_events():
    """Test that parser finds the expected NFP-class and FOMC events from real fixture.

    Without this, a WHITELIST gap silently drops critical events (e.g., FF's
    'Non-Farm Employment Change' was missed before the whitelist included
    'employment change').
    """
    from macro_calendar import parse_ff_response
    html = (FIXTURES / "ff_response.html").read_text()
    events = parse_ff_response(html)
    names = [e["name"].lower() for e in events]
    # The fixture contains real high-impact USD events from one week
    # We expect at minimum FOMC + NFP-class events to be parsed
    assert any("fomc" in n for n in names), f"FOMC missing from {names}"
    assert any("employment change" in n or "non-farm" in n.lower() or "nfp" in n for n in names), \
        f"NFP-class event missing from {names}"


def test_convert_ff_time_to_cr_dst_aware():
    """Verify EST (winter) and EDT (summer) both convert correctly to CR."""
    from macro_calendar import _convert_ff_time_to_cr
    # January is EST: 1pm ET → 12:00 CR (offset 1h)
    assert _convert_ff_time_to_cr("1:00pm", "2026-01-15") == "12:00"
    # July is EDT: 1pm ET → 11:00 CR (offset 2h)
    assert _convert_ff_time_to_cr("1:00pm", "2026-07-15") == "11:00"
    # Empty/tentative still returns None
    assert _convert_ff_time_to_cr("All Day", "2026-01-15") is None
    assert _convert_ff_time_to_cr("", "2026-01-15") is None
