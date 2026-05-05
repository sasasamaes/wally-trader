"""Tests for punk_smart_vetos."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "scripts"))

import punk_smart_vetos as vetos


class TestMacroVeto:
    def test_clear_when_no_event(self, monkeypatch):
        monkeypatch.setattr(vetos, "_macro_check",
                            lambda: {"blocked": False, "reason": None})
        result = vetos.veto_macro({"side": "LONG"})
        assert result.passed is True
        assert "clear" in result.reason.lower()

    def test_blocked_when_event_within_30min(self, monkeypatch):
        monkeypatch.setattr(vetos, "_macro_check",
                            lambda: {"blocked": True, "reason": "FOMC in 22 min"})
        result = vetos.veto_macro({"side": "LONG"})
        assert result.passed is False
        assert "FOMC" in result.reason


class TestBlacklistVeto:
    def test_clear_when_not_blacklisted(self, tmp_profile_dir, cr_time):
        result = vetos.veto_blacklist({"asset": "ETHUSDT"},
                                       now=cr_time(2026, 5, 5, 10, 0),
                                       memory_dir=tmp_profile_dir)
        assert result.passed is True

    def test_blocked_when_2sl_streak(self, tmp_profile_dir, cr_time):
        import punk_smart_state as state
        state.record_sl("XLMUSDT", cr_time(2026, 5, 5, 9, 0), pnl_usd=-3.0,
                        memory_dir=tmp_profile_dir)
        state.record_sl("XLMUSDT", cr_time(2026, 5, 5, 10, 0), pnl_usd=-3.0,
                        memory_dir=tmp_profile_dir)
        result = vetos.veto_blacklist({"asset": "XLMUSDT"},
                                       now=cr_time(2026, 5, 5, 11, 0),
                                       memory_dir=tmp_profile_dir)
        assert result.passed is False
        assert "blacklist" in result.reason.lower() or "2 sl" in result.reason.lower()


class TestCorrelationVeto:
    def test_clear_when_no_open_in_bucket(self, tmp_profile_dir, signals_csv_factory):
        signals_csv_factory([])  # no open positions
        result = vetos.veto_correlation({"asset": "BTCUSDT", "side": "LONG"},
                                         memory_dir=tmp_profile_dir)
        assert result.passed is True

    def test_blocked_when_same_bucket_same_side_open(self, tmp_profile_dir,
                                                      signals_csv_factory):
        signals_csv_factory([
            {"symbol": "BTCUSDT.P", "side": "LONG", "exit_price": ""},
        ])
        result = vetos.veto_correlation({"asset": "ETHUSDT", "side": "LONG"},
                                         memory_dir=tmp_profile_dir)
        assert result.passed is False
        assert "btc_majors" in result.reason.lower()

    def test_clear_when_opposite_side_open(self, tmp_profile_dir, signals_csv_factory):
        signals_csv_factory([
            {"symbol": "BTCUSDT.P", "side": "LONG", "exit_price": ""},
        ])
        result = vetos.veto_correlation({"asset": "ETHUSDT", "side": "SHORT"},
                                         memory_dir=tmp_profile_dir)
        assert result.passed is True
