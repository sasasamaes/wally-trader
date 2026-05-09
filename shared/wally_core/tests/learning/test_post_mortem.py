"""Tests for L5 — post_mortem."""
import csv
import pytest
from pathlib import Path
from wally_core.learning.post_mortem import (
    auto_postmortem,
    aggregate_postmortems,
    append_to_postmortem_log,
    _auto_lesson_tags,
    _structural_findings,
)


def test_auto_lesson_tags_win():
    row = {
        "lesson_tags": "WIN|intraday",
        "side": "LONG",
        "hold_minutes": "45",
        "pnl_usd": "5.0",
        "regime_at_entry": "RANGE_CHOP",
    }
    tags = _auto_lesson_tags(row)
    assert "WIN" in tags
    assert "intraday" in tags


def test_auto_lesson_tags_loss_adds_loss():
    row = {
        "lesson_tags": "",
        "side": "LONG",
        "hold_minutes": "45",
        "pnl_usd": "-3.0",
        "regime_at_entry": "RANGE_CHOP",
    }
    tags = _auto_lesson_tags(row)
    assert "LOSS" in tags


def test_auto_lesson_tags_counter_trend():
    row = {
        "lesson_tags": "",
        "side": "SHORT",
        "hold_minutes": "30",
        "pnl_usd": "-3.0",
        "regime_at_entry": "TREND_FUERTE",
    }
    tags = _auto_lesson_tags(row)
    assert "LOSS" in tags
    assert "counter_trend" in tags


def test_auto_lesson_tags_no_duplicate():
    row = {
        "lesson_tags": "LOSS|counter_trend",
        "side": "SHORT",
        "hold_minutes": "30",
        "pnl_usd": "-3.0",
        "regime_at_entry": "TREND_FUERTE",
    }
    tags = _auto_lesson_tags(row)
    assert tags.count("LOSS") == 1
    assert tags.count("counter_trend") == 1


def test_structural_findings_regime_change():
    row = {
        "regime_at_entry": "RANGE_CHOP",
        "regime_at_exit": "TREND_FUERTE",
        "side": "LONG",
        "pnl_usd": "-2.0",
        "max_favorable_excursion": "0",
        "max_adverse_excursion": "0",
        "hold_minutes": "60",
    }
    findings = _structural_findings(row)
    assert any("RANGE_CHOP" in f and "TREND_FUERTE" in f for f in findings)


def test_structural_findings_no_anomaly():
    row = {
        "regime_at_entry": "RANGE_CHOP",
        "regime_at_exit": "RANGE_CHOP",
        "side": "LONG",
        "pnl_usd": "-1.0",
        "max_favorable_excursion": "0",
        "max_adverse_excursion": "0",
        "hold_minutes": "20",
    }
    findings = _structural_findings(row)
    assert len(findings) >= 1
    assert any("standard" in f.lower() or "no anomal" in f.lower() for f in findings)


def test_auto_postmortem_from_row():
    row = {
        "symbol": "BTCUSDT",
        "open_time_utc": "2026-03-01T10:00:00Z",
        "close_time_utc": "2026-03-01T11:00:00Z",
        "hold_minutes": "60",
        "pnl_usd": "-5.0",
        "regime_at_entry": "RANGE_CHOP",
        "regime_at_exit": "RANGE_CHOP",
        "side": "LONG",
        "lesson_tags": "LOSS",
        "max_favorable_excursion": "0.5",
        "max_adverse_excursion": "-0.8",
    }
    report = auto_postmortem("BTCUSDT:2026-03-01T10:00:00Z", outcomes_row=row)
    assert report.trade_id == "BTCUSDT:2026-03-01T10:00:00Z"
    assert report.pnl_usd == -5.0
    assert "LOSS" in report.lesson_tags
    assert len(report.structural_findings) >= 1


def test_auto_postmortem_not_found(tmp_path):
    path = tmp_path / "bitunix" / "memory" / "outcomes_v2.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["symbol", "open_time_utc", "close_time_utc", "hold_minutes",
                  "pnl_usd", "regime_at_entry", "regime_at_exit", "side",
                  "lesson_tags", "max_favorable_excursion", "max_adverse_excursion"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    with pytest.raises(KeyError):
        auto_postmortem("nonexistent", profile="bitunix", profiles_dir=str(tmp_path))


def test_aggregate_postmortems_no_data(tmp_path):
    result = aggregate_postmortems("bitunix", profiles_dir=str(tmp_path))
    assert result["status"] == "no_data"


def test_aggregate_postmortems_clusters_tags(tmp_path):
    from datetime import datetime, timezone, timedelta

    path = tmp_path / "bitunix" / "memory" / "outcomes_v2.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["open_time_utc", "close_time_utc", "hold_minutes", "symbol", "side",
                  "pnl_usd", "regime_at_entry", "regime_at_exit", "lesson_tags",
                  "max_favorable_excursion", "max_adverse_excursion"]

    # Use a recent date (yesterday) so date filter doesn't cut it out
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT10:00:00Z")
    rows = []
    for i in range(5):
        rows.append({
            "open_time_utc": yesterday,
            "close_time_utc": yesterday,
            "hold_minutes": "60",
            "symbol": "BTCUSDT",
            "side": "SHORT",
            "pnl_usd": "-3.0",
            "regime_at_entry": "TREND_FUERTE",
            "regime_at_exit": "TREND_FUERTE",
            "lesson_tags": "LOSS|counter_trend",
            "max_favorable_excursion": "0",
            "max_adverse_excursion": "0",
        })

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    result = aggregate_postmortems("bitunix", days=30, profiles_dir=str(tmp_path))
    assert result["status"] == "ok"
    assert result["n_losses"] == 5
    tags = [t["tag"] for t in result["top_loss_tags"]]
    assert "counter_trend" in tags


def test_append_to_postmortem_log(tmp_path):
    from wally_core.learning.post_mortem import PostMortemReport
    report = PostMortemReport(
        trade_id="T001",
        lesson_tags=["LOSS", "counter_trend"],
        regime_entry="TREND_FUERTE",
        regime_exit="TREND_FUERTE",
        held_minutes=45,
        pnl_usd=-3.0,
        system_recommended=[],
        structural_findings=["Counter-trend entry"],
    )
    append_to_postmortem_log(report, "bitunix", profiles_dir=str(tmp_path))
    log_path = tmp_path / "bitunix" / "memory" / "learning" / "postmortems.md"
    assert log_path.exists()
    content = log_path.read_text()
    assert "T001" in content
    assert "counter_trend" in content
