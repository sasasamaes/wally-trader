"""Tests for punk_smart_state module."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "scripts"))

import punk_smart_state as state


class TestAssetBlacklist:
    def test_blacklist_after_2sl_same_day(self, tmp_profile_dir, cr_time):
        state.record_sl("XLMUSDT", cr_time(2026, 5, 5, 9, 14), pnl_usd=-3.20,
                        memory_dir=tmp_profile_dir)
        assert not state.is_blacklisted("XLMUSDT", cr_time(2026, 5, 5, 10, 0),
                                         memory_dir=tmp_profile_dir)
        state.record_sl("XLMUSDT", cr_time(2026, 5, 5, 11, 23), pnl_usd=-4.05,
                        memory_dir=tmp_profile_dir)
        assert state.is_blacklisted("XLMUSDT", cr_time(2026, 5, 5, 12, 0),
                                     memory_dir=tmp_profile_dir)

    def test_blacklist_clears_on_tp(self, tmp_profile_dir, cr_time):
        state.record_sl("XLMUSDT", cr_time(2026, 5, 5, 9, 0), pnl_usd=-3.20,
                        memory_dir=tmp_profile_dir)
        state.record_tp("XLMUSDT", cr_time(2026, 5, 5, 10, 0),
                        memory_dir=tmp_profile_dir)
        # Now next SL should not blacklist (count was reset)
        state.record_sl("XLMUSDT", cr_time(2026, 5, 5, 11, 0), pnl_usd=-3.20,
                        memory_dir=tmp_profile_dir)
        assert not state.is_blacklisted("XLMUSDT", cr_time(2026, 5, 5, 12, 0),
                                         memory_dir=tmp_profile_dir)

    def test_blacklist_expires_next_cr_midnight(self, tmp_profile_dir, cr_time):
        state.record_sl("XLMUSDT", cr_time(2026, 5, 5, 22, 0), pnl_usd=-3.20,
                        memory_dir=tmp_profile_dir)
        state.record_sl("XLMUSDT", cr_time(2026, 5, 5, 23, 0), pnl_usd=-3.20,
                        memory_dir=tmp_profile_dir)
        assert state.is_blacklisted("XLMUSDT", cr_time(2026, 5, 5, 23, 30),
                                     memory_dir=tmp_profile_dir)
        # After CR 00:00 next day → expired
        assert not state.is_blacklisted("XLMUSDT", cr_time(2026, 5, 6, 0, 1),
                                         memory_dir=tmp_profile_dir)


class TestKillSwitch:
    def test_2sl_in_4h_activates_killswitch(self, tmp_profile_dir, cr_time):
        state.record_sl("ETHUSDT", cr_time(2026, 5, 5, 10, 15), pnl_usd=-3.85,
                        memory_dir=tmp_profile_dir)
        active, _ = state.is_kill_switch_active(cr_time(2026, 5, 5, 11, 0),
                                                 memory_dir=tmp_profile_dir)
        assert not active
        state.record_sl("AVAXUSDT", cr_time(2026, 5, 5, 11, 50), pnl_usd=-4.10,
                        memory_dir=tmp_profile_dir)
        active, reason = state.is_kill_switch_active(cr_time(2026, 5, 5, 12, 0),
                                                      memory_dir=tmp_profile_dir)
        assert active
        assert "2 SL" in reason or "kill" in reason.lower()

    def test_killswitch_purge_old_events(self, tmp_profile_dir, cr_time):
        state.record_sl("BTCUSDT", cr_time(2026, 5, 5, 6, 0), pnl_usd=-3.0,
                        memory_dir=tmp_profile_dir)
        # 5h later — first SL is outside the 4h window now
        state.record_sl("ETHUSDT", cr_time(2026, 5, 5, 11, 0), pnl_usd=-3.0,
                        memory_dir=tmp_profile_dir)
        active, _ = state.is_kill_switch_active(cr_time(2026, 5, 5, 11, 30),
                                                 memory_dir=tmp_profile_dir)
        assert not active

    def test_killswitch_persists_until_cr_midnight(self, tmp_profile_dir, cr_time):
        state.record_sl("BTCUSDT", cr_time(2026, 5, 5, 22, 0), pnl_usd=-3.0,
                        memory_dir=tmp_profile_dir)
        state.record_sl("ETHUSDT", cr_time(2026, 5, 5, 23, 30), pnl_usd=-3.0,
                        memory_dir=tmp_profile_dir)
        active, _ = state.is_kill_switch_active(cr_time(2026, 5, 5, 23, 45),
                                                 memory_dir=tmp_profile_dir)
        assert active
        active, _ = state.is_kill_switch_active(cr_time(2026, 5, 6, 0, 1),
                                                 memory_dir=tmp_profile_dir)
        assert not active

    def test_reset_killswitch(self, tmp_profile_dir, cr_time):
        state.record_sl("BTCUSDT", cr_time(2026, 5, 5, 10, 0), pnl_usd=-3.0,
                        memory_dir=tmp_profile_dir)
        state.record_sl("ETHUSDT", cr_time(2026, 5, 5, 11, 0), pnl_usd=-3.0,
                        memory_dir=tmp_profile_dir)
        state.reset_killswitch(memory_dir=tmp_profile_dir)
        active, _ = state.is_kill_switch_active(cr_time(2026, 5, 5, 12, 0),
                                                 memory_dir=tmp_profile_dir)
        assert not active
