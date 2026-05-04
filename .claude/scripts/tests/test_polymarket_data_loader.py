"""Tests for polymarket.research.data_loader."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from polymarket import config
from polymarket.research import data_loader


def _write_snapshots(path: Path, rows: list[dict]) -> None:
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _write_ohlcv_csv(path: Path, rows: list[tuple[str, float]]) -> None:
    """rows = [(iso_ts, close_price)]"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        f.write("ts,open,high,low,close,volume\n")
        for ts, close in rows:
            f.write(f"{ts},{close},{close},{close},{close},0\n")


def test_load_snapshots_as_series(tmp_path, monkeypatch):
    snaps = tmp_path / "snaps.jsonl"
    _write_snapshots(snaps, [
        {"ts": "2026-05-01T00:00:00+00:00", "slug": "fed-cut", "prob": 0.50, "vol_24h": 1},
        {"ts": "2026-05-01T01:00:00+00:00", "slug": "fed-cut", "prob": 0.55, "vol_24h": 1},
    ])
    monkeypatch.setattr(config, "SNAPSHOTS_PATH", snaps)

    series = data_loader.load_snapshots_for_market("fed-cut")
    assert len(series) == 2
    assert series[0][1] == 0.50


def test_align_pm_with_btc(tmp_path, monkeypatch):
    snaps = tmp_path / "snaps.jsonl"
    _write_snapshots(snaps, [
        {"ts": "2026-05-01T00:00:00+00:00", "slug": "fed-cut", "prob": 0.50, "vol_24h": 1},
        {"ts": "2026-05-01T04:00:00+00:00", "slug": "fed-cut", "prob": 0.55, "vol_24h": 1},
    ])
    csv = tmp_path / "btc.csv"
    _write_ohlcv_csv(csv, [
        ("2026-05-01T00:00:00+00:00", 70000.0),
        ("2026-05-01T04:00:00+00:00", 70500.0),
        ("2026-05-01T08:00:00+00:00", 71000.0),
    ])
    monkeypatch.setattr(config, "SNAPSHOTS_PATH", snaps)

    aligned = data_loader.align_with_btc(
        slug="fed-cut",
        btc_csv=csv,
        forward_window=timedelta(hours=4),
    )
    # For each PM snapshot we get (pm_prob, btc_close_at_t, btc_close_at_t+window)
    assert len(aligned) == 2
    pm0, btc0, btc_fwd0 = aligned[0]
    assert pm0 == 0.50
    assert btc0 == 70000.0
    assert btc_fwd0 == 70500.0  # 4h forward
    pm1, btc1, btc_fwd1 = aligned[1]
    assert pm1 == 0.55
    assert btc1 == 70500.0
    assert btc_fwd1 == 71000.0


def test_align_drops_when_no_forward_btc(tmp_path, monkeypatch):
    snaps = tmp_path / "snaps.jsonl"
    _write_snapshots(snaps, [
        {"ts": "2026-05-01T20:00:00+00:00", "slug": "fed-cut", "prob": 0.55, "vol_24h": 1},
    ])
    csv = tmp_path / "btc.csv"
    _write_ohlcv_csv(csv, [
        ("2026-05-01T20:00:00+00:00", 70000.0),
        # No row at +4h
    ])
    monkeypatch.setattr(config, "SNAPSHOTS_PATH", snaps)

    aligned = data_loader.align_with_btc(
        slug="fed-cut",
        btc_csv=csv,
        forward_window=timedelta(hours=4),
    )
    assert aligned == []
