"""Tests for L6 — drift_response."""
import json
import pytest
from pathlib import Path
from wally_core.learning.drift_response import (
    append_calibration_check,
    apply_tightening,
    check_drift_streak,
    get_current_tightening,
    relax_when_resolved,
)


def test_check_drift_no_history(tmp_path):
    result = check_drift_streak("bitunix", profiles_dir=str(tmp_path))
    assert result["status"] == "no_history"
    assert result["alert_streak"] == 0
    assert result["should_tighten"] is False


def test_append_and_check_streak(tmp_path):
    for _ in range(7):
        append_calibration_check("bitunix", "ALERT", profiles_dir=str(tmp_path))

    result = check_drift_streak("bitunix", alert_days_threshold=7, profiles_dir=str(tmp_path))
    assert result["alert_streak"] == 7
    assert result["should_tighten"] is True


def test_streak_broken_by_ok(tmp_path):
    for _ in range(5):
        append_calibration_check("bitunix", "ALERT", profiles_dir=str(tmp_path))
    append_calibration_check("bitunix", "OK", profiles_dir=str(tmp_path))
    append_calibration_check("bitunix", "ALERT", profiles_dir=str(tmp_path))

    result = check_drift_streak("bitunix", alert_days_threshold=7, profiles_dir=str(tmp_path))
    assert result["alert_streak"] == 1  # Only the last one
    assert result["should_tighten"] is False


def test_apply_tightening_level1(tmp_path):
    apply_tightening("bitunix", 1, profiles_dir=str(tmp_path))
    state = get_current_tightening("bitunix", profiles_dir=str(tmp_path))
    assert state["active"] is True
    assert state["level"] == 1
    assert state["composite_threshold_bump"] == 5
    assert state["confluence_requirement_bump"] == 0


def test_apply_tightening_level2(tmp_path):
    apply_tightening("bitunix", 2, profiles_dir=str(tmp_path))
    state = get_current_tightening("bitunix", profiles_dir=str(tmp_path))
    assert state["level"] == 2
    assert state["composite_threshold_bump"] == 5
    assert state["confluence_requirement_bump"] == 1


def test_apply_tightening_level0_resets(tmp_path):
    apply_tightening("bitunix", 2, profiles_dir=str(tmp_path))
    apply_tightening("bitunix", 0, profiles_dir=str(tmp_path))
    state = get_current_tightening("bitunix", profiles_dir=str(tmp_path))
    assert state["active"] is False
    assert state["level"] == 0


def test_relax_when_ok(tmp_path):
    apply_tightening("bitunix", 1, profiles_dir=str(tmp_path))
    append_calibration_check("bitunix", "OK", profiles_dir=str(tmp_path))
    result = relax_when_resolved("bitunix", profiles_dir=str(tmp_path))
    assert result["relaxed"] is True
    assert result["previous_level"] == 1
    state = get_current_tightening("bitunix", profiles_dir=str(tmp_path))
    assert state["active"] is False


def test_no_relax_if_still_alert(tmp_path):
    apply_tightening("bitunix", 1, profiles_dir=str(tmp_path))
    append_calibration_check("bitunix", "ALERT", profiles_dir=str(tmp_path))
    result = relax_when_resolved("bitunix", profiles_dir=str(tmp_path))
    assert result["relaxed"] is False


def test_initial_state_inactive(tmp_path):
    state = get_current_tightening("bitunix", profiles_dir=str(tmp_path))
    assert state["active"] is False
    assert state["level"] == 0
    assert state["composite_threshold_bump"] == 0
