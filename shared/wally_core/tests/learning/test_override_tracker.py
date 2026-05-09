"""Tests for L8 — override_tracker."""
import json
import pytest
from pathlib import Path
from wally_core.learning.override_tracker import (
    log_override,
    update_override_outcome,
    override_calibration,
)


@pytest.fixture
def log_path(tmp_path):
    return tmp_path / "overrides.jsonl"


def test_log_override_creates_file(log_path):
    entry_id = log_override("GO", "HOLD", "trade001", log_path=log_path)
    assert log_path.exists()
    assert entry_id is not None


def test_log_override_fields(log_path):
    entry_id = log_override(
        "CUT", "HOLD", "trade002", "I saw a support bounce", log_path=log_path
    )
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    e = json.loads(lines[0])
    assert e["entry_id"] == entry_id
    assert e["my_rec"] == "CUT"
    assert e["user_action"] == "HOLD"
    assert e["override_type"] == "CUT->HOLD"
    assert e["trade_id"] == "trade002"
    assert e["rationale"] == "I saw a support bounce"
    assert e["outcome_resolved"] is False


def test_log_multiple_overrides(log_path):
    log_override("GO", "NO-GO", "t1", log_path=log_path)
    log_override("CUT", "HOLD", "t2", log_path=log_path)
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2


def test_update_override_outcome(log_path):
    entry_id = log_override("GO", "NO-GO", "t1", log_path=log_path)
    update_override_outcome(entry_id, 8.5, log_path=log_path)
    lines = log_path.read_text().strip().splitlines()
    e = json.loads(lines[0])
    assert e["outcome_pnl"] == 8.5
    assert e["outcome_resolved"] is True


def test_update_outcome_not_found(log_path):
    log_override("GO", "NO-GO", "t1", log_path=log_path)
    with pytest.raises(KeyError):
        update_override_outcome("nonexistent", 5.0, log_path=log_path)


def test_override_calibration_no_data(tmp_path):
    result = override_calibration(log_path=tmp_path / "overrides.jsonl")
    assert result["status"] == "no_data"


def test_override_calibration_no_resolved(log_path):
    log_override("GO", "HOLD", "t1", log_path=log_path)
    result = override_calibration(log_path=log_path)
    assert result["status"] == "no_resolved_overrides"


def test_override_calibration_basic_stats(log_path):
    """3 resolved overrides: 2 wins, 1 loss."""
    entries = [
        {"entry_id": "e1", "timestamp": "2026-03-01T10:00:00+00:00",
         "my_rec": "GO", "user_action": "HOLD", "override_type": "GO->HOLD",
         "trade_id": "t1", "rationale": "", "outcome_pnl": 5.0, "outcome_resolved": True},
        {"entry_id": "e2", "timestamp": "2026-03-01T11:00:00+00:00",
         "my_rec": "GO", "user_action": "HOLD", "override_type": "GO->HOLD",
         "trade_id": "t2", "rationale": "", "outcome_pnl": 3.0, "outcome_resolved": True},
        {"entry_id": "e3", "timestamp": "2026-03-01T12:00:00+00:00",
         "my_rec": "CUT", "user_action": "HOLD", "override_type": "CUT->HOLD",
         "trade_id": "t3", "rationale": "", "outcome_pnl": -2.0, "outcome_resolved": True},
    ]
    log_path.write_text("\n".join(json.dumps(e) for e in entries))

    result = override_calibration(log_path=log_path)
    assert result["status"] == "ok"
    assert result["total_overrides"] == 3
    assert result["overall_win_pct"] == pytest.approx(66.7, abs=0.2)
    assert "GO->HOLD" in result["buckets"]
    assert result["buckets"]["GO->HOLD"]["n"] == 2
    assert result["buckets"]["GO->HOLD"]["wr"] == 100.0


def test_override_calibration_narrative(log_path):
    """Check narrative is generated when bucket WR >= 60."""
    entries = [
        {"entry_id": f"e{i}", "timestamp": "2026-03-01T10:00:00+00:00",
         "my_rec": "GO", "user_action": "HOLD", "override_type": "GO->HOLD",
         "trade_id": f"t{i}", "rationale": "", "outcome_pnl": 5.0, "outcome_resolved": True}
        for i in range(3)
    ]
    log_path.write_text("\n".join(json.dumps(e) for e in entries))

    result = override_calibration(log_path=log_path)
    assert len(result["narrative"]) > 0
    assert any("GO->HOLD" in n for n in result["narrative"])
