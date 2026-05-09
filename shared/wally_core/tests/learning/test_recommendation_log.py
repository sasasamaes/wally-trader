"""Tests for L1 — recommendation_log."""
import pytest
from pathlib import Path
from wally_core.learning.recommendation_log import (
    log_recommendation,
    update_user_action,
    update_outcome,
    calibration_report,
    _load_entries,
)


@pytest.fixture
def log_path(tmp_path):
    return tmp_path / "recommendations.jsonl"


def test_log_entry_creates_file(log_path):
    entry_id = log_recommendation("agent-x", "GO", "RSI oversold", log_path=log_path)
    assert log_path.exists()
    assert entry_id is not None
    assert len(entry_id) > 0


def test_log_entry_fields(log_path):
    entry_id = log_recommendation(
        "punk-watch-analyst", "CUT", "RSI divergence",
        trade_id="trade123",
        log_path=log_path,
    )
    entries = _load_entries(log_path)
    assert len(entries) == 1
    e = entries[0]
    assert e["entry_id"] == entry_id
    assert e["agent"] == "punk-watch-analyst"
    assert e["recommendation"] == "CUT"
    assert e["rationale"] == "RSI divergence"
    assert e["trade_id"] == "trade123"
    assert e["user_action"] == "pending"
    assert e["outcome_final_pnl"] is None


def test_update_user_action(log_path):
    entry_id = log_recommendation("agent", "GO", "reason", log_path=log_path)
    update_user_action(entry_id, "OVERRIDE", log_path=log_path)
    entries = _load_entries(log_path)
    assert entries[0]["user_action"] == "OVERRIDE"


def test_update_user_action_not_found(log_path):
    log_recommendation("agent", "GO", "reason", log_path=log_path)
    with pytest.raises(KeyError):
        update_user_action("nonexistent", "OVERRIDE", log_path=log_path)


def test_update_outcome(log_path):
    entry_id = log_recommendation("agent", "GO", "reason", log_path=log_path)
    update_outcome(entry_id, pnl_24h=5.0, pnl_final=8.0, log_path=log_path)
    entries = _load_entries(log_path)
    assert entries[0]["outcome_24h_pnl"] == 5.0
    assert entries[0]["outcome_final_pnl"] == 8.0


def test_multiple_entries_preserved(log_path):
    id1 = log_recommendation("a1", "GO", "r1", log_path=log_path)
    id2 = log_recommendation("a2", "NO-GO", "r2", log_path=log_path)
    update_outcome(id1, 3.0, 5.0, log_path=log_path)
    entries = _load_entries(log_path)
    assert len(entries) == 2
    assert entries[0]["outcome_final_pnl"] == 5.0
    assert entries[1]["outcome_final_pnl"] is None


def test_calibration_report_insufficient_data(log_path):
    log_recommendation("agent", "GO", "reason", log_path=log_path)
    report = calibration_report(min_entries=10, days=30, log_path=log_path)
    assert report["status"] == "insufficient_data"
    assert "n" in report


def test_calibration_report_aggregation(log_path):
    """Build 10 entries with outcomes and verify report math."""
    import json

    # Write 10 resolved entries directly
    entries = []
    for i in range(10):
        rec = "GO"
        action = "GO" if i < 7 else "OVERRIDE"  # 7 followed, 3 overridden
        pnl = 5.0 if i < 6 else -2.0            # 6 wins, 4 losses
        e = {
            "entry_id": f"id{i}",
            "timestamp": "2026-01-15T10:00:00+00:00",
            "agent": "test",
            "recommendation": rec,
            "rationale": "r",
            "user_action": action,
            "trade_id": None,
            "outcome_24h_pnl": pnl,
            "outcome_final_pnl": pnl,
        }
        entries.append(e)

    log_path.write_text("\n".join(json.dumps(e) for e in entries))

    report = calibration_report(min_entries=10, days=365, log_path=log_path)
    assert report["status"] == "ok"
    assert report["n"] == 10
    assert report["n_followed"] == 7
    assert report["n_overridden"] == 3
