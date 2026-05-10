"""Tests for win_streak_advice — overconfidence detection."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from wally_core.discipline import (
    TradeRecord,
    WinStreakAdvice,
    win_streak_advice,
)


def _trade(pnl: float, mins_ago: int, sym: str = "BTCUSDT") -> TradeRecord:
    return TradeRecord(
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=mins_ago),
        symbol=sym,
        side="LONG",
        pnl_usd=pnl,
        margin_usd=50.0,
        is_loss=pnl < 0,
    )


def test_no_trades_returns_normal():
    r = win_streak_advice([])
    assert r.advice == "NORMAL_SIZE"
    assert r.size_multiplier == 1.0
    assert r.consecutive_wins == 0


def test_single_win_normal_size():
    r = win_streak_advice([_trade(10, 60)])
    assert r.consecutive_wins == 1
    assert r.advice == "NORMAL_SIZE"
    assert r.size_multiplier == 1.0


def test_two_wins_normal_size():
    r = win_streak_advice([_trade(10, 60), _trade(15, 30)])
    assert r.consecutive_wins == 2
    assert r.advice == "NORMAL_SIZE"


def test_three_wins_triggers_half_size():
    """3 consecutive wins = overconfidence zone → HALF SIZE."""
    trades = [_trade(10, 180), _trade(15, 120), _trade(20, 60)]
    r = win_streak_advice(trades)
    assert r.consecutive_wins == 3
    assert r.advice == "HALF_SIZE"
    assert r.size_multiplier == 0.5
    assert "consecutive wins" in r.reason


def test_four_wins_still_half_size():
    trades = [_trade(10, 240), _trade(15, 180), _trade(20, 120), _trade(25, 60)]
    r = win_streak_advice(trades)
    assert r.consecutive_wins == 4
    assert r.advice == "HALF_SIZE"


def test_five_wins_triggers_skip_day():
    """5 consecutive wins = take the W, close session."""
    trades = [_trade(10, 300 - 60 * i, f"AST{i}") for i in range(5)]
    r = win_streak_advice(trades)
    assert r.consecutive_wins == 5
    assert r.advice == "SKIP_DAY"
    assert r.size_multiplier == 0.0


def test_loss_resets_streak():
    """A loss between wins resets the streak counter."""
    trades = [
        _trade(10, 240),    # win 4h ago
        _trade(15, 180),    # win 3h ago
        _trade(-20, 120),   # LOSS 2h ago
        _trade(10, 60),     # win 1h ago
    ]
    r = win_streak_advice(trades)
    assert r.consecutive_wins == 1  # only the most-recent win counts
    assert r.advice == "NORMAL_SIZE"


def test_be_resets_streak():
    """A BE (PnL == 0) breaks the streak too."""
    trades = [
        _trade(10, 180),    # win
        _trade(15, 120),    # win
        _trade(0, 60),      # BE (closes the streak)
        _trade(20, 30),     # win — should be only 1 in streak
    ]
    r = win_streak_advice(trades)
    assert r.consecutive_wins == 1
    assert r.advice == "NORMAL_SIZE"


def test_streak_starts_from_most_recent():
    """If recent trade is a loss, streak is 0 regardless of older wins."""
    trades = [
        _trade(10, 180),    # old win
        _trade(15, 120),    # old win
        _trade(20, 60),     # old win
        _trade(-10, 30),    # most recent: LOSS
    ]
    r = win_streak_advice(trades)
    assert r.consecutive_wins == 0
    assert r.advice == "NORMAL_SIZE"


def test_advice_is_actionable_for_5_wins_skip():
    trades = [_trade(10, 60 * i + 60) for i in range(5, 0, -1)]
    r = win_streak_advice(trades)
    assert r.advice == "SKIP_DAY"
    assert "Close session" in r.reason
