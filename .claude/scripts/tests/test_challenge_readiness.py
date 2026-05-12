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


def test_parse_monthly_from_log_uses_pnl_column_not_first_numeric(tmp_path):
    """Regression: log with Lots-then-PnL columns must aggregate PnL, not Lots."""
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from challenge_readiness import _parse_monthly_from_log

    log = tmp_path / "trading_log.md"
    log.write_text(
        "# Trades\n\n"
        "| Date | Asset | Dir | Entry | Lots | SL | TP | Exit | Duration | PnL $ | Notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|\n"
        "| 2026-04-15 | EURUSD | LONG | 1.0500 | 0.03 | 1.0450 | 1.0600 | 1.0470 | 45m | -2.91 | SL hit |\n"
        "| 2026-04-22 | EURUSD | SHORT | 1.0650 | 0.03 | 1.0700 | 1.0550 | 1.0560 | 60m | +5.40 | TP1 |\n"
    )
    out = _parse_monthly_from_log(log)
    assert abs(out.get("2026-04", 0.0) - 2.49) < 0.001  # -2.91 + 5.40 = +2.49 (not 0.06 from summing Lots)


def test_parse_monthly_from_log_handles_missing_pnl_column(tmp_path):
    """Tables without a recognizable PnL column are silently skipped."""
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from challenge_readiness import _parse_monthly_from_log

    log = tmp_path / "trading_log.md"
    log.write_text(
        "| Date | Notes |\n"
        "|---|---|\n"
        "| 2026-04-15 | observation only |\n"
    )
    assert _parse_monthly_from_log(log) == {}


def test_parse_monthly_from_log_handles_bare_numbers_no_dollar_sign(tmp_path):
    """Cells like `-2.91` (no $ prefix) parse correctly."""
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from challenge_readiness import _parse_monthly_from_log

    log = tmp_path / "trading_log.md"
    log.write_text(
        "| Date | PnL $ |\n"
        "|---|---|\n"
        "| 2026-04-15 | -2.91 |\n"
    )
    assert _parse_monthly_from_log(log) == {"2026-04": -2.91}
