"""Tests for min_rr_gate.py — dynamic min-R:R gate based on rolling WR."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from min_rr_gate import compute_min_rr, evaluate


def test_happy_path_high_wr_passes():
    """WR 0.55, setup R:R 1.5 → OK (min_rr = (1-0.55)/0.55 * 1.2 ≈ 0.98)."""
    out = evaluate(wr=0.55, setup_rr=1.5, sample_size=30)
    assert out["status"] == "OK"
    assert out["min_rr"] < 1.5
    assert "INSUFFICIENT_DATA" not in out.get("flags", [])


def test_warn_path_low_wr_demands_high_rr():
    """WR 0.40, setup R:R 1.2 → WARN (min_rr = 0.6/0.4 * 1.2 = 1.8)."""
    out = evaluate(wr=0.40, setup_rr=1.2, sample_size=30)
    assert out["status"] == "WARN"
    assert out["min_rr"] > 1.2


def test_insufficient_data_falls_back_to_15():
    """Fewer than 10 trades → fallback min_rr = 1.5 with INSUFFICIENT_DATA flag."""
    out = evaluate(wr=0.55, setup_rr=2.0, sample_size=5)
    assert out["status"] == "OK"
    assert out["min_rr"] == 1.5
    assert "INSUFFICIENT_DATA" in out["flags"]


def test_boundary_exact_min_rr_is_ok():
    """Setup R:R exactly equal to min_rr → OK (>=, not >)."""
    min_rr = compute_min_rr(wr=0.50)  # = 0.5/0.5 * 1.2 = 1.2
    out = evaluate(wr=0.50, setup_rr=min_rr, sample_size=20)
    assert out["status"] == "OK"


def test_wr_clamped_at_bounds():
    """WR clamped to [0.20, 0.80] to avoid pathological outputs."""
    high_wr = compute_min_rr(wr=0.95)  # clamped to 0.80 → 0.2/0.8 * 1.2 = 0.30
    low_wr = compute_min_rr(wr=0.05)   # clamped to 0.20 → 0.8/0.2 * 1.2 = 4.80
    assert 0.29 < high_wr < 0.31
    assert 4.79 < low_wr < 4.81


def test_fetch_wr_for_profile_returns_zero_when_log_missing(tmp_path):
    """fetch_wr_for_profile returns (0.0, 0) when the profile log doesn't exist (graceful degradation)."""
    from min_rr_gate import fetch_wr_for_profile
    out = fetch_wr_for_profile("nonexistent-profile-xyz")
    assert out == (0.0, 0)
