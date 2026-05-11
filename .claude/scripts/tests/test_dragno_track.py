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


def _sample_trades():
    """Subset of today's Dragno AI trades for deterministic stats."""
    return [
        {"date": "2026-05-10", "time_open": "11:19:47", "time_close": "13:08:02",
         "symbol": "KITEUSDT", "side": "SHORT", "leverage": 10,
         "entry": 0.18340, "exit": 0.18034, "pyg_pct": 15.48, "pyg_usd": 0.45994,
         "margin_est": 2.97, "duration_min": 108, "source": "manual_screenshot"},
        {"date": "2026-05-10", "time_open": "11:10:38", "time_close": "11:49:55",
         "symbol": "VIRTUALUSDT", "side": "SHORT", "leverage": 10,
         "entry": 0.9092, "exit": 0.9220, "pyg_pct": -15.28, "pyg_usd": -0.52676,
         "margin_est": 3.45, "duration_min": 39, "source": "manual_screenshot"},
        {"date": "2026-05-10", "time_open": "15:47:20", "time_close": "17:33:06",
         "symbol": "UNIUSDT", "side": "LONG", "leverage": 10,
         "entry": 3.956, "exit": 3.993, "pyg_pct": 8.21, "pyg_usd": 0.25984,
         "margin_est": 3.17, "duration_min": 105, "source": "manual_screenshot"},
        {"date": "2026-05-10", "time_open": "12:12:49", "time_close": "13:32:22",
         "symbol": "SUSDT", "side": "SHORT", "leverage": 10,
         "entry": 0.05556, "exit": 0.05660, "pyg_pct": -19.92, "pyg_usd": -0.59462,
         "margin_est": 2.98, "duration_min": 80, "source": "manual_screenshot"},
    ]


def test_compute_stats_aggregate():
    s = dt.compute_stats(_sample_trades(), sl_cap=-8.0)
    assert s["total_trades"] == 4
    assert s["wins"] == 2  # KITE, UNI
    assert s["losses"] == 2  # VIRTUAL, SUSDT
    assert s["win_rate_pct"] == 50.0
    assert abs(s["net_pnl"] - (0.45994 + 0.25984 - 0.52676 - 0.59462)) < 0.001
    assert abs(s["best_win"] - 0.45994) < 0.001
    assert abs(s["worst_loss"] - (-0.59462)) < 0.001


def test_compute_stats_side_breakdown():
    s = dt.compute_stats(_sample_trades(), sl_cap=-8.0)
    assert s["long"]["count"] == 1
    assert s["long"]["wins"] == 1
    assert s["short"]["count"] == 3
    assert s["short"]["wins"] == 1


def test_compute_stats_empty_returns_zero_stats():
    s = dt.compute_stats([], sl_cap=-8.0)
    assert s["total_trades"] == 0
    assert s["win_rate_pct"] == 0.0
    assert s["profit_factor"] == 0.0


def _full_dragno_2026_05_10():
    """All 14 trades from Dragno AI on 2026-05-10. Reference for counterfactual."""
    return dt.parse_input_rows([
        {"date": "2026-05-10", "time_open": "12:02:14", "time_close": "13:29:56",
         "symbol": "CHIPUSDT", "side": "Corto", "leverage": "10X",
         "entry": "0.06405", "exit": "0.06417", "pyg_pct": "-3.14", "pyg_usd": "-0.10114123"},
        {"date": "2026-05-10", "time_open": "11:19:47", "time_close": "13:08:02",
         "symbol": "KITEUSDT", "side": "Corto", "leverage": "10X",
         "entry": "0.18340", "exit": "0.18034", "pyg_pct": "15.48", "pyg_usd": "0.45994422"},
        {"date": "2026-05-10", "time_open": "11:10:38", "time_close": "11:49:55",
         "symbol": "VIRTUALUSDT", "side": "Corto", "leverage": "10X",
         "entry": "0.9092", "exit": "0.9220", "pyg_pct": "-15.28", "pyg_usd": "-0.52676148"},
        {"date": "2026-05-10", "time_open": "11:18:08", "time_close": "11:45:41",
         "symbol": "PAXGUSDT", "side": "Corto", "leverage": "10X",
         "entry": "4717.43", "exit": "4720.56", "pyg_pct": "-1.86", "pyg_usd": "-0.06154955"},
        {"date": "2026-05-10", "time_open": "18:50:25", "time_close": "19:38:10",
         "symbol": "IOTAUSDT", "side": "Largo", "leverage": "10X",
         "entry": "0.0631", "exit": "0.0637", "pyg_pct": "9.03", "pyg_usd": "0.14906275"},
        {"date": "2026-05-10", "time_open": "18:44:10", "time_close": "19:03:34",
         "symbol": "PIEVERSEUSDT", "side": "Largo", "leverage": "10X",
         "entry": "0.8228", "exit": "0.8198", "pyg_pct": "-4.84", "pyg_usd": "-0.16340796"},
        {"date": "2026-05-10", "time_open": "16:06:50", "time_close": "18:51:31",
         "symbol": "FILUSDT", "side": "Largo", "leverage": "10X",
         "entry": "1.132", "exit": "1.141", "pyg_pct": "7.49", "pyg_usd": "0.24509548"},
        {"date": "2026-05-10", "time_open": "16:36:35", "time_close": "17:47:51",
         "symbol": "MUSDT", "side": "Largo", "leverage": "10X",
         "entry": "3.3130", "exit": "3.3033", "pyg_pct": "-4.12", "pyg_usd": "-0.12302802"},
        {"date": "2026-05-10", "time_open": "15:47:20", "time_close": "17:33:06",
         "symbol": "UNIUSDT", "side": "Largo", "leverage": "10X",
         "entry": "3.956", "exit": "3.993", "pyg_pct": "8.21", "pyg_usd": "0.25984360"},
        {"date": "2026-05-10", "time_open": "16:15:22", "time_close": "16:23:12",
         "symbol": "BUSDT", "side": "Corto", "leverage": "10X",
         "entry": "0.4060", "exit": "0.4039", "pyg_pct": "3.76", "pyg_usd": "0.11303660"},
        {"date": "2026-05-10", "time_open": "13:49:50", "time_close": "15:34:18",
         "symbol": "GRTUSDT", "side": "Corto", "leverage": "10X",
         "entry": "0.02903", "exit": "0.02869", "pyg_pct": "10.51", "pyg_usd": "0.33330176"},
        {"date": "2026-05-10", "time_open": "13:57:01", "time_close": "15:33:44",
         "symbol": "LPTUSDT", "side": "Corto", "leverage": "10X",
         "entry": "2.399", "exit": "2.373", "pyg_pct": "9.44", "pyg_usd": "0.27629340"},
        {"date": "2026-05-10", "time_open": "13:42:03", "time_close": "15:31:31",
         "symbol": "ORDIUSDT", "side": "Corto", "leverage": "10X",
         "entry": "5.436", "exit": "5.298", "pyg_pct": "24.12", "pyg_usd": "0.81315061"},
        {"date": "2026-05-10", "time_open": "12:12:49", "time_close": "13:32:22",
         "symbol": "SUSDT", "side": "Corto", "leverage": "10X",
         "entry": "0.05556", "exit": "0.05660", "pyg_pct": "-19.92", "pyg_usd": "-0.59461795"},
    ])


def test_full_day_matches_known_baseline():
    """Pins 2026-05-10 analysis: 14 trades, WR 57.1%, net +$1.08, +56% with SL -8%."""
    s = dt.compute_stats(_full_dragno_2026_05_10(), sl_cap=-8.0)
    assert s["total_trades"] == 14
    assert s["wins"] == 8
    assert abs(s["win_rate_pct"] - 57.14) < 0.1
    assert abs(s["net_pnl"] - 1.0793) < 0.01
    # Counterfactual: SL -8% caps VIRTUAL (-15.28%) and SUSDT (-19.92%) → new total ≈ +$1.69
    assert s["counterfactual"]["sl_hits"] == 2
    assert abs(s["counterfactual"]["new_net_pnl"] - 1.6860) < 0.05
    assert s["counterfactual"]["delta_pct"] >= 50.0  # ≥ +56%
