"""Tests for L4 — strategy_refresh."""
import csv
import json
import pytest
from pathlib import Path
from wally_core.learning.strategy_refresh import refresh_strategy_mapping


def _write_outcomes_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "open_time_utc", "close_time_utc", "hold_minutes", "profile",
        "symbol", "side", "entry", "exit", "qty", "pnl_usd", "pnl_pct",
        "regime_at_entry", "regime_at_exit", "max_favorable_excursion",
        "max_adverse_excursion", "raw_outcome", "lesson_tags", "notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            full = {k: "" for k in fieldnames}
            full.update(row)
            writer.writerow(full)


def test_refresh_no_data(tmp_path):
    result = refresh_strategy_mapping("bitunix", profiles_dir=str(tmp_path))
    assert result["status"] == "no_recent_trades"
    assert result["n_cells_updated"] == 0


def test_refresh_detects_new_regime(tmp_path):
    rows = [
        {
            "close_time_utc": "2026-04-01T10:00:00Z",
            "pnl_usd": "5.0",
            "regime_at_entry": "RANGE_CHOP",
        },
    ] * 5

    path = tmp_path / "bitunix" / "memory" / "outcomes_v2.csv"
    _write_outcomes_csv(path, rows)

    result = refresh_strategy_mapping(
        "bitunix", days=90, profiles_dir=str(tmp_path), dry_run=True
    )
    assert result["status"] == "ok"
    assert result["n_trades"] == 5
    # RANGE_CHOP with all wins = 100% WR
    assert "RANGE_CHOP" in result["regime_stats"]
    assert result["regime_stats"]["RANGE_CHOP"]["wr"] == 100.0


def test_refresh_detects_drift(tmp_path):
    """Existing mapping with RANGE_CHOP at 70% WR, live data at 30% → drift detected."""
    mapping = {
        "regime_strategy_map": [
            {"regime": "RANGE_CHOP", "strategy": "MeanReversion", "backtest_wr": 70.0}
        ]
    }
    mapping_file = tmp_path / "regime_mapping.json"
    mapping_file.write_text(json.dumps(mapping))

    rows = []
    for i in range(10):
        rows.append({
            "close_time_utc": "2026-04-01T10:00:00Z",
            "pnl_usd": "5.0" if i < 3 else "-2.0",  # 30% WR
            "regime_at_entry": "RANGE_CHOP",
        })

    path = tmp_path / "bitunix" / "memory" / "outcomes_v2.csv"
    _write_outcomes_csv(path, rows)

    result = refresh_strategy_mapping(
        "bitunix", days=90, threshold_drift=10.0,
        profiles_dir=str(tmp_path), mapping_path=mapping_file, dry_run=True
    )

    assert result["status"] == "ok"
    drift_changes = [c for c in result["changes"] if c["type"] == "drift_detected"]
    assert len(drift_changes) == 1
    assert drift_changes[0]["regime"] == "RANGE_CHOP"
    assert drift_changes[0]["drift"] < -10  # Negative drift


def test_refresh_no_drift_if_small_delta(tmp_path):
    """Live WR = 75% vs backtest 70% → no drift (delta=5 < threshold=10)."""
    mapping = {
        "regime_strategy_map": [
            {"regime": "RANGE_CHOP", "strategy": "MeanReversion", "backtest_wr": 70.0}
        ]
    }
    mapping_file = tmp_path / "regime_mapping.json"
    mapping_file.write_text(json.dumps(mapping))

    rows = []
    for i in range(8):
        rows.append({
            "close_time_utc": "2026-04-01T10:00:00Z",
            "pnl_usd": "5.0" if i < 6 else "-2.0",  # 75% WR
            "regime_at_entry": "RANGE_CHOP",
        })

    path = tmp_path / "bitunix" / "memory" / "outcomes_v2.csv"
    _write_outcomes_csv(path, rows)

    result = refresh_strategy_mapping(
        "bitunix", days=90, threshold_drift=10.0,
        profiles_dir=str(tmp_path), mapping_path=mapping_file, dry_run=True
    )

    drift_changes = [c for c in result["changes"] if c["type"] == "drift_detected"]
    assert len(drift_changes) == 0
