# Unit tests for guardian.py — run with: pytest .claude/scripts/test_guardian.py -v
import sys
import tempfile
import pathlib
from datetime import datetime, date

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import guardian


def _write_curve(rows):
    """Helper: write rows to a temp CSV, return path."""
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    tmp.write("timestamp,equity,source,note\n")
    for r in rows:
        tmp.write(",".join(str(x) for x in r) + "\n")
    tmp.close()
    return tmp.name


def test_load_empty_curve():
    path = _write_curve([])
    curve = guardian.load_equity_curve(path)
    assert curve == []


def test_load_single_row():
    path = _write_curve([
        ("2026-04-23T06:00:00", 10000.0, "manual", "initial"),
    ])
    curve = guardian.load_equity_curve(path)
    assert len(curve) == 1
    assert curve[0]["equity"] == 10000.0
    assert curve[0]["source"] == "manual"
    assert isinstance(curve[0]["timestamp"], datetime)


def test_peak_equity_empty():
    assert guardian.peak_equity([]) == 0.0


def test_peak_equity_single():
    curve = [{"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""}]
    assert guardian.peak_equity(curve) == 10000.0


def test_peak_equity_multiple():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,9,0), "equity": 10200.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,12,0), "equity": 10150.0, "source": "m", "note": ""},
    ]
    assert guardian.peak_equity(curve) == 10200.0


def test_daily_pnl_no_data():
    assert guardian.daily_pnl([], date(2026,4,23)) == 0.0


def test_daily_pnl_single_point_no_baseline():
    curve = [{"timestamp": datetime(2026,4,23,9,0), "equity": 10180.0, "source": "m", "note": ""}]
    # Only one point today — can't compute intraday P&L
    assert guardian.daily_pnl(curve, date(2026,4,23)) == 0.0


def test_daily_pnl_positive():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,9,0), "equity": 10180.0, "source": "m", "note": ""},
    ]
    assert guardian.daily_pnl(curve, date(2026,4,23)) == 180.0


def test_daily_pnl_negative():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,14,0), "equity": 9780.0, "source": "m", "note": ""},
    ]
    assert guardian.daily_pnl(curve, date(2026,4,23)) == -220.0


def test_trailing_dd_no_peak():
    curve = [{"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""}]
    assert guardian.trailing_dd(curve) == 0.0


def test_trailing_dd_in_drawdown():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,10,0), "equity": 10400.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,25,9,0), "equity": 10250.0, "source": "m", "note": ""},
    ]
    # Peak 10400, current 10250, dd = 150
    assert guardian.trailing_dd(curve) == 150.0


def test_trailing_dd_at_new_peak():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,10,0), "equity": 10400.0, "source": "m", "note": ""},
    ]
    assert guardian.trailing_dd(curve) == 0.0


def test_best_day_ratio_no_profit():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,16,0), "equity": 10000.0, "source": "m", "note": ""},
    ]
    best, total = guardian.best_day_ratio(curve)
    assert best == 0.0
    assert total == 0.0


def test_best_day_ratio_single_day():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,16,0), "equity": 10180.0, "source": "m", "note": ""},
    ]
    best, total = guardian.best_day_ratio(curve)
    assert best == 180.0
    assert total == 180.0


def test_best_day_ratio_multiple_days_balanced():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0),  "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,16,0), "equity": 10150.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,6,0),  "equity": 10150.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,16,0), "equity": 10300.0, "source": "m", "note": ""},
    ]
    # Day 1 profit 150, day 2 profit 150, total 300, best 150, ratio 0.5
    best, total = guardian.best_day_ratio(curve)
    assert best == 150.0
    assert total == 300.0


def test_best_day_ratio_one_big_day():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0),  "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,16,0), "equity": 10600.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,6,0),  "equity": 10600.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,16,0), "equity": 10700.0, "source": "m", "note": ""},
    ]
    # Best 600, total 700, ratio 0.857 — violates Best Day Rule
    best, total = guardian.best_day_ratio(curve)
    assert best == 600.0
    assert total == 700.0


def test_best_day_ratio_ignores_losing_days():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0),  "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,16,0), "equity": 10200.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,6,0),  "equity": 10200.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,16,0), "equity": 10100.0, "source": "m", "note": ""},  # losing day
    ]
    best, total = guardian.best_day_ratio(curve)
    assert best == 200.0
    assert total == 200.0  # Only positive days counted


def test_load_ftmo_config(tmp_path):
    cfg = tmp_path / "config.md"
    cfg.write_text("""# FTMO

Some prose.

```yaml
challenge_type: 1-step
initial_capital: 10000
max_daily_loss_pct: 3
max_total_trailing_pct: 10
best_day_cap_pct: 50
risk_per_trade_pct: 0.5
max_trades_per_day: 2
max_sl_consecutive: 2
```
""")
    c = guardian.load_profile_config(str(cfg))
    assert c["initial_capital"] == 10000
    assert c["max_daily_loss_pct"] == 3
    assert c["max_trades_per_day"] == 2


CFG_DEFAULT = {
    "initial_capital": 10000,
    "max_daily_loss_pct": 3,
    "max_total_trailing_pct": 10,
    "best_day_cap_pct": 50,
    "risk_per_trade_pct": 0.5,
    "max_trades_per_day": 2,
    "max_sl_consecutive": 2,
}


def test_check_entry_ok_fresh_day():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""},
    ]
    trade = {"asset": "BTCUSD", "entry": 77538, "sl": 77238, "loss_if_sl": 30}
    result = guardian.check_entry(CFG_DEFAULT, curve, trade, now=datetime(2026,4,23,9,0))
    assert result["verdict"] == "OK"
    assert result["blocking"] is False


def test_check_entry_block_daily_breach():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0),  "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,10,0), "equity":  9780.0, "source": "m", "note": ""},  # already -220
    ]
    trade = {"asset": "BTCUSD", "entry": 77538, "sl": 77238, "loss_if_sl": 100}
    # If SL hits: -220 - 100 = -320 = -3.2% → BREACH daily limit 3% ($300)
    result = guardian.check_entry(CFG_DEFAULT, curve, trade, now=datetime(2026,4,23,11,0))
    assert result["verdict"] in ("BLOCK_SIZE", "BLOCK_HARD")
    assert result["blocking"] is True


def test_check_entry_block_hard_daily_already_breached():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0),  "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,10,0), "equity":  9690.0, "source": "m", "note": ""},  # -310, past 3%
    ]
    trade = {"asset": "BTCUSD", "entry": 77538, "sl": 77238, "loss_if_sl": 50}
    result = guardian.check_entry(CFG_DEFAULT, curve, trade, now=datetime(2026,4,23,11,0))
    assert result["verdict"] == "BLOCK_HARD"
    assert "daily" in result["reason"].lower()


def test_check_entry_warn_trailing_close_to_limit():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0),  "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,9,0),  "equity": 10500.0, "source": "m", "note": ""},  # peak
        {"timestamp": datetime(2026,4,25,10,0), "equity":  9700.0, "source": "m", "note": ""},  # dd $800 = 8%
    ]
    trade = {"asset": "BTCUSD", "entry": 77538, "sl": 77238, "loss_if_sl": 50}
    result = guardian.check_entry(CFG_DEFAULT, curve, trade, now=datetime(2026,4,25,11,0))
    # Should warn but not block (trailing is WARN not BLOCK)
    assert result["verdict"] in ("OK_WITH_WARN", "BLOCK_SIZE")
    assert any("trailing" in w.lower() for w in result.get("warnings", []))


def test_check_entry_block_max_trades():
    # Simulate 2 trades already today via markers in notes
    curve = [
        {"timestamp": datetime(2026,4,23,6,0),  "equity": 10000.0, "source": "m", "note": "init"},
        {"timestamp": datetime(2026,4,23,8,0),  "equity": 10080.0, "source": "trade", "note": "BTC TP1"},
        {"timestamp": datetime(2026,4,23,11,0), "equity": 10050.0, "source": "trade", "note": "ETH SL"},
    ]
    trade = {"asset": "BTCUSD", "entry": 77538, "sl": 77238, "loss_if_sl": 50}
    result = guardian.check_entry(CFG_DEFAULT, curve, trade, now=datetime(2026,4,23,12,0))
    assert result["verdict"] == "BLOCK_HARD"
    assert "trades" in result["reason"].lower()
