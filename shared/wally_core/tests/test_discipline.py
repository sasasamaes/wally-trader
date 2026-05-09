import pytest
import json
from datetime import datetime, timedelta, timezone
from wally_core.discipline import (
    tilt_score, TradeRecord, TiltLevel,
    cooldown_active, trigger_cooldown,
    pre_trade_checklist, discipline_scorecard,
)


def _trade(minutes_ago, pnl, is_loss, margin=50):
    return TradeRecord(
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
        symbol="TEST", side="LONG",
        pnl_usd=pnl, margin_usd=margin, is_loss=is_loss,
    )


def test_tilt_calm_no_recent_trades():
    report = tilt_score(recent_trades=[])
    assert report.score == 0
    assert report.level == TiltLevel.CALM


def test_tilt_overtrading_5_in_4h():
    trades = [_trade(i * 30, pnl=1, is_loss=False) for i in range(5)]
    # 5 trades over 2.5h, all in last 4h
    report = tilt_score(recent_trades=trades)
    assert report.score >= 20
    assert any("overtrading" in f for f in report.flags)


def test_tilt_revenge_trade():
    # Loss 2h ago + win trade 15min after
    trades = [
        _trade(120, pnl=-5, is_loss=True),
        _trade(105, pnl=2, is_loss=False),  # 15min after the loss
    ]
    report = tilt_score(recent_trades=trades)
    assert any("revenge" in f for f in report.flags)


def test_tilt_loss_streak_2_triggers():
    trades = [
        _trade(180, pnl=-3, is_loss=True),
        _trade(60, pnl=-5, is_loss=True),
    ]
    report = tilt_score(recent_trades=trades)
    assert report.score >= 25
    assert any("loss_streak" in f for f in report.flags)


def test_tilt_high_level_blocks():
    # Combine multiple flags
    trades = [
        _trade(180, pnl=-5, is_loss=True),
        _trade(150, pnl=-5, is_loss=True),  # streak
        _trade(120, pnl=-5, is_loss=True),  # streak
        _trade(105, pnl=-3, is_loss=True),  # revenge (within 30min of prev)
        _trade(60, pnl=-2, is_loss=True),   # streak
    ]
    report = tilt_score(recent_trades=trades, baseline_avg_size=30)
    assert report.level in (TiltLevel.ELEVATED, TiltLevel.HIGH)


def test_tilt_size_escalation():
    trades = [
        _trade(180, pnl=2, is_loss=False, margin=100),
        _trade(120, pnl=2, is_loss=False, margin=100),
        _trade(60, pnl=2, is_loss=False, margin=100),
    ]
    # baseline 30, recent 100 → 3.3x
    report = tilt_score(recent_trades=trades, baseline_avg_size=30)
    assert any("size_escalation" in f for f in report.flags)


def test_tilt_no_escalation_within_threshold():
    trades = [
        _trade(180, pnl=1, is_loss=False, margin=40),
        _trade(120, pnl=1, is_loss=False, margin=40),
        _trade(60, pnl=1, is_loss=False, margin=40),
    ]
    # baseline 40, recent 40 → 1.0x (no escalation)
    report = tilt_score(recent_trades=trades, baseline_avg_size=40)
    assert not any("size_escalation" in f for f in report.flags)


def test_tilt_calm_single_loss():
    """Single loss, not in 4h window → calm."""
    trades = [_trade(300, pnl=-5, is_loss=True)]  # 5h ago
    report = tilt_score(recent_trades=trades)
    assert report.level == TiltLevel.CALM


def test_cooldown_active_no_file(tmp_path):
    cs = cooldown_active(profile="bitunix", cooldown_file=str(tmp_path / "missing.json"))
    assert not cs.active


def test_cooldown_trigger_and_check(tmp_path):
    cooldown_file = str(tmp_path / "cooldowns.json")
    until = trigger_cooldown(
        profile="bitunix", minutes=60,
        reason="manual_test", cooldown_file=cooldown_file,
    )
    cs = cooldown_active(profile="bitunix", cooldown_file=cooldown_file)
    assert cs.active
    assert cs.reason == "manual_test"
    assert cs.minutes_remaining > 50
    assert cs.minutes_remaining <= 60


def test_cooldown_expires_after_until(tmp_path):
    cooldown_file = str(tmp_path / "cooldowns.json")
    # Manually write expired cooldown
    past = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    (tmp_path / "cooldowns.json").write_text(json.dumps({
        "bitunix": {"until": past, "reason": "test"}
    }))
    cs = cooldown_active(profile="bitunix", cooldown_file=cooldown_file)
    assert not cs.active


def test_cooldown_does_not_affect_other_profile(tmp_path):
    cooldown_file = str(tmp_path / "cooldowns.json")
    trigger_cooldown(
        profile="bitunix", minutes=60,
        reason="test", cooldown_file=cooldown_file,
    )
    cs = cooldown_active(profile="retail", cooldown_file=cooldown_file)
    assert not cs.active


def test_pre_trade_checklist_returns_6_questions():
    qs = pre_trade_checklist()
    assert len(qs) == 6
    blockers = [q for q in qs if q.is_blocker]
    assert len(blockers) >= 4


def test_pre_trade_checklist_keys_unique():
    qs = pre_trade_checklist()
    keys = [q.key for q in qs]
    assert len(keys) == len(set(keys))


def test_discipline_scorecard_basic():
    trades = [
        _trade(60, pnl=2, is_loss=False),
        _trade(30, pnl=-1, is_loss=True),
    ]
    sc = discipline_scorecard(recent_trades=trades, cooldown_breaches=0, checklist_overrides=0)
    assert sc["n_trades"] == 2
    assert sc["wr"] == 50.0
    assert sc["score"] == 100


def test_discipline_scorecard_penalties():
    trades = [_trade(60, pnl=1, is_loss=False)]
    sc = discipline_scorecard(recent_trades=trades, cooldown_breaches=2, checklist_overrides=3)
    # 100 - 2*20 - 3*10 = 30
    assert sc["score"] == 30


def test_discipline_scorecard_empty_trades():
    sc = discipline_scorecard(recent_trades=[])
    assert sc["score"] == 100
    assert sc["n_trades"] == 0
