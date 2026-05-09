"""Tests for L2 — pattern_miner."""
import csv
import pytest
from pathlib import Path
from wally_core.learning.pattern_miner import (
    mine_patterns,
    pattern_to_recommendation,
    _asset_type,
    _hour_bucket,
)


def _write_outcomes_csv(path: Path, rows: list[dict]) -> None:
    """Write outcomes_v2.csv rows for testing."""
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


def _make_outcomes_path(profiles_dir: Path, profile: str) -> Path:
    return profiles_dir / profile / "memory" / "outcomes_v2.csv"


def test_asset_type_classification():
    assert _asset_type("BTCUSDT.P") == "major"
    assert _asset_type("ETHUSDT") == "major"
    assert _asset_type("AVAXUSDT.P") == "mid"
    assert _asset_type("FARTCOINUSDT.P") == "alt"


def test_hour_bucket():
    assert _hour_bucket(3) == "00-06"
    assert _hour_bucket(8) == "06-12"
    assert _hour_bucket(15) == "12-18"
    assert _hour_bucket(20) == "18-24"


def test_mine_patterns_no_data(tmp_path):
    result = mine_patterns("bitunix", profiles_dir=str(tmp_path))
    assert result["total_trades"] == 0
    assert result["winning"] == []
    assert result["losing"] == []


def test_mine_patterns_basic(tmp_path):
    """5 BTC LONG wins in RANGE + 5 ETH SHORT losses in TREND → pattern detected."""
    rows = []
    for i in range(6):
        rows.append({
            "open_time_utc": "2026-03-01T10:00:00Z",
            "close_time_utc": "2026-03-01T11:00:00Z",
            "symbol": "BTCUSDT.P",
            "side": "LONG",
            "pnl_usd": "5.0",
            "regime_at_entry": "RANGE_CHOP",
        })
    for i in range(6):
        rows.append({
            "open_time_utc": "2026-03-01T10:00:00Z",
            "close_time_utc": "2026-03-01T11:00:00Z",
            "symbol": "ETHUSDT",
            "side": "SHORT",
            "pnl_usd": "-3.0",
            "regime_at_entry": "TREND_FUERTE",
        })

    path = _make_outcomes_path(tmp_path, "bitunix")
    _write_outcomes_csv(path, rows)

    result = mine_patterns("bitunix", days=90, min_n=5, profiles_dir=str(tmp_path))
    assert result["total_trades"] == 12
    assert result["combos_analyzed"] >= 2

    # The winning combo should have WR=100 (LONG RANGE)
    winning_wrs = [p["wr"] for p in result["winning"]]
    assert 100.0 in winning_wrs


def test_pattern_to_recommendation_format(tmp_path):
    rows = []
    for i in range(6):
        rows.append({
            "open_time_utc": "2026-03-01T10:00:00Z",
            "close_time_utc": "2026-03-01T11:00:00Z",
            "symbol": "BTCUSDT.P",
            "side": "LONG",
            "pnl_usd": "5.0",
            "regime_at_entry": "RANGE_CHOP",
        })

    path = _make_outcomes_path(tmp_path, "bitunix")
    _write_outcomes_csv(path, rows)

    patterns = mine_patterns("bitunix", days=90, min_n=5, profiles_dir=str(tmp_path))
    suggestions = pattern_to_recommendation(patterns)
    assert isinstance(suggestions, list)
    # Should have at least a PREFER suggestion
    prefer = [s for s in suggestions if "PREFER" in s]
    assert len(prefer) > 0


def test_mine_patterns_min_n_filter(tmp_path):
    """Combos with n < min_n should be excluded."""
    rows = [
        {
            "open_time_utc": "2026-03-01T10:00:00Z",
            "close_time_utc": "2026-03-01T11:00:00Z",
            "symbol": "BTCUSDT.P",
            "side": "LONG",
            "pnl_usd": "5.0",
            "regime_at_entry": "RANGE_CHOP",
        }
    ] * 3  # Only 3 trades, below default min_n=5

    path = _make_outcomes_path(tmp_path, "bitunix")
    _write_outcomes_csv(path, rows)

    result = mine_patterns("bitunix", days=90, min_n=5, profiles_dir=str(tmp_path))
    assert result["combos_analyzed"] == 1
    assert result["winning"] == []  # Filtered out


def test_mine_patterns_top_10_sort(tmp_path):
    """Winning patterns should be sorted highest WR first."""
    rows = []
    # Two combos: BTC LONG RANGE (100% WR), ETH SHORT TREND (50% WR)
    for i in range(6):
        rows.append({
            "open_time_utc": "2026-03-01T10:00:00Z",
            "close_time_utc": "2026-03-01T11:00:00Z",
            "symbol": "BTCUSDT.P",
            "side": "LONG",
            "pnl_usd": "5.0" if i < 6 else "-2.0",
            "regime_at_entry": "RANGE_CHOP",
        })
    for i in range(6):
        rows.append({
            "open_time_utc": "2026-03-01T10:00:00Z",
            "close_time_utc": "2026-03-01T11:00:00Z",
            "symbol": "ETHUSDT",
            "side": "SHORT",
            "pnl_usd": "3.0" if i < 3 else "-2.0",
            "regime_at_entry": "TREND_FUERTE",
        })

    path = _make_outcomes_path(tmp_path, "bitunix")
    _write_outcomes_csv(path, rows)

    result = mine_patterns("bitunix", days=90, min_n=5, profiles_dir=str(tmp_path))
    if len(result["winning"]) >= 2:
        wrs = [p["wr"] for p in result["winning"]]
        assert wrs[0] >= wrs[1]  # Sorted descending
