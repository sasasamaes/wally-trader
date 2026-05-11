"""Unit tests for dragno_track.py."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import dragno_track as dt


def test_derive_margin_from_win():
    # KITE: +15.48% / +$0.45994 → margin = 0.45994 / 0.1548 ≈ 2.972
    margin = dt.derive_margin(pyg_pct=15.48, pyg_usd=0.45994)
    assert abs(margin - 2.972) < 0.01


def test_derive_margin_from_loss():
    # VIRTUAL: -15.28% / -$0.52676 → margin = 0.52676 / 0.1528 ≈ 3.448
    margin = dt.derive_margin(pyg_pct=-15.28, pyg_usd=-0.52676)
    assert abs(margin - 3.448) < 0.01


def test_derive_margin_returns_zero_if_pct_zero():
    assert dt.derive_margin(pyg_pct=0.0, pyg_usd=0.0) == 0.0


def test_parse_input_rows_normalizes_side():
    raw = [
        {"date": "2026-05-10", "time_open": "11:19:47", "time_close": "13:08:02",
         "symbol": "KITEUSDT", "side": "Corto", "leverage": "10X",
         "entry": "0.18340", "exit": "0.18034",
         "pyg_pct": "+15.48", "pyg_usd": "+0.45994422"}
    ]
    rows = dt.parse_input_rows(raw)
    assert len(rows) == 1
    r = rows[0]
    assert r["side"] == "SHORT"
    assert r["leverage"] == 10
    assert r["pyg_pct"] == 15.48
    assert r["pyg_usd"] == 0.45994422
    assert r["margin_est"] > 0
    assert r["duration_min"] == 108  # 13:08:02 - 11:19:47 ≈ 108 min
    assert r["source"] == "manual_screenshot"


def test_parse_input_rows_handles_largo_as_long():
    raw = [
        {"date": "2026-05-10", "time_open": "18:50:25", "time_close": "19:38:10",
         "symbol": "IOTAUSDT", "side": "Largo", "leverage": "10X",
         "entry": "0.0631", "exit": "0.0637",
         "pyg_pct": "9.03", "pyg_usd": "0.14906275"}
    ]
    rows = dt.parse_input_rows(raw)
    assert rows[0]["side"] == "LONG"


def test_parse_input_rows_rejects_malformed():
    raw = [{"symbol": "KITEUSDT"}]  # missing required fields
    try:
        dt.parse_input_rows(raw)
        assert False, "Should have raised"
    except (KeyError, ValueError):
        pass


import csv as _csv
import pytest


@pytest.fixture
def tmp_csv(tmp_path, monkeypatch):
    """Isolated CSV path."""
    path = tmp_path / "dragno_ai.csv"
    monkeypatch.setattr(dt, "csv_path", lambda: path)
    return path


def test_read_rows_empty_when_missing(tmp_csv):
    assert dt.read_rows() == []


def test_write_and_read_roundtrip(tmp_csv):
    rows = [{
        "date": "2026-05-10", "time_open": "11:19:47", "time_close": "13:08:02",
        "symbol": "KITEUSDT", "side": "SHORT", "leverage": 10,
        "entry": 0.18340, "exit": 0.18034,
        "pyg_pct": 15.48, "pyg_usd": 0.45994,
        "margin_est": 2.97, "duration_min": 108, "source": "manual_screenshot",
    }]
    dt.write_rows(rows)
    loaded = dt.read_rows()
    assert len(loaded) == 1
    assert loaded[0]["symbol"] == "KITEUSDT"
    assert loaded[0]["pyg_pct"] == 15.48  # numeric, not string
    assert loaded[0]["leverage"] == 10


def test_append_dedup_skips_existing(tmp_csv):
    base = {
        "date": "2026-05-10", "time_open": "11:19:47", "time_close": "13:08:02",
        "symbol": "KITEUSDT", "side": "SHORT", "leverage": 10,
        "entry": 0.18340, "exit": 0.18034,
        "pyg_pct": 15.48, "pyg_usd": 0.45994,
        "margin_est": 2.97, "duration_min": 108, "source": "manual_screenshot",
    }
    dt.write_rows([base])
    # Try appending same trade + a new one
    new_trade = dict(base, symbol="ORDIUSDT", time_open="13:42:03")
    added = dt.append_rows_dedup([base, new_trade])
    assert added == 1  # only ORDIUSDT is new
    assert len(dt.read_rows()) == 2
