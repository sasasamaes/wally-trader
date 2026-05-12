"""Tests for challenge_readiness.py."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from challenge_readiness import classify


def test_ready_three_consecutive_positive():
    """Three consecutive positive months → READY."""
    monthly_pnl = {"2026-02": 50.0, "2026-03": 30.0, "2026-04": 80.0}
    assert classify(monthly_pnl, today="2026-05-01")["status"] == "READY"


def test_borderline_one_positive_two_flat():
    """One positive, two flat (or one negative) in last 3 → BORDERLINE."""
    monthly_pnl = {"2026-02": -10.0, "2026-03": 5.0, "2026-04": 40.0}
    assert classify(monthly_pnl, today="2026-05-01")["status"] == "BORDERLINE"


def test_not_ready_last_month_negative():
    """Last month negative → NOT_READY regardless of earlier months."""
    monthly_pnl = {"2026-02": 50.0, "2026-03": 80.0, "2026-04": -30.0}
    assert classify(monthly_pnl, today="2026-05-01")["status"] == "NOT_READY"


def test_not_ready_no_track_record():
    """Empty input → NOT_READY with NO_DATA flag."""
    out = classify({}, today="2026-05-01")
    assert out["status"] == "NOT_READY"
    assert "NO_DATA" in out["flags"]


def test_only_last_3_months_count():
    """A profitable Jan 2025 doesn't help when 2026 has 3 negative."""
    monthly_pnl = {
        "2025-01": 500.0,
        "2026-02": -10.0,
        "2026-03": -20.0,
        "2026-04": -5.0,
    }
    assert classify(monthly_pnl, today="2026-05-01")["status"] == "NOT_READY"
