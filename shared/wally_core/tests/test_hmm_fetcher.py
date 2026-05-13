"""Tests for hmm_lib.fetcher — OHLCV fetch + cache."""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Make .claude/scripts importable
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))

from hmm_lib import errors
from hmm_lib import fetcher


def _fake_binance_kline_row(ts_ms: int, close: float):
    """Binance kline response is a list of 12 fields per row."""
    return [ts_ms, "100.0", "110.0", "90.0", str(close), "1500.0", ts_ms + 3_600_000,
            "150000", 25, "750", "75000", "0"]


def test_fetch_returns_dataframe_with_correct_columns(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher, "CACHE_DIR", tmp_path)
    rows = [_fake_binance_kline_row(1_700_000_000_000 + i * 3_600_000, 100.0 + i)
            for i in range(1500)]
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = rows
    with patch.object(fetcher, "_http_get", return_value=mock_resp):
        df = fetcher.fetch_ohlcv_1h_6m("ETHUSDT")
    assert list(df.columns) == ["open", "high", "low", "close", "volume", "ts_utc"]
    assert len(df) >= 1000


def test_fetch_raises_insufficient_data_on_short_response(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher, "CACHE_DIR", tmp_path)
    rows = [_fake_binance_kline_row(1_700_000_000_000 + i * 3_600_000, 100.0 + i)
            for i in range(500)]
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = rows
    with patch.object(fetcher, "_http_get", return_value=mock_resp):
        with pytest.raises(errors.InsufficientDataError):
            fetcher.fetch_ohlcv_1h_6m("ETHUSDT")


def test_fetch_raises_fetch_error_on_4xx(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher, "CACHE_DIR", tmp_path)
    mock_resp = MagicMock(status_code=400)
    mock_resp.json.return_value = {"code": -1121, "msg": "Invalid symbol."}
    with patch.object(fetcher, "_http_get", return_value=mock_resp):
        with pytest.raises(errors.FetchError, match="not listed"):
            fetcher.fetch_ohlcv_1h_6m("XYZUSDT")


def test_fetch_uses_cache_within_ttl(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher, "CACHE_DIR", tmp_path)
    cache_payload = {
        "ts_saved": "2026-05-13T10:00:00",
        "symbol": "ETHUSDT",
        "rows": [_fake_binance_kline_row(1_700_000_000_000 + i * 3_600_000, 100.0 + i)
                 for i in range(1500)],
    }
    cache_file = tmp_path / "ohlcv_ETHUSDT_1h_6m.json"
    cache_file.write_text(json.dumps(cache_payload))
    # Simulate "now" is 30 minutes after save → still within 1h TTL
    monkeypatch.setattr(fetcher, "_now_iso", lambda: "2026-05-13T10:30:00")
    with patch.object(fetcher, "_http_get") as mock_http:
        df = fetcher.fetch_ohlcv_1h_6m("ETHUSDT")
    mock_http.assert_not_called()
    assert len(df) == 1500
