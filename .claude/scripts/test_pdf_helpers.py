#!/usr/bin/env python3
"""
Sanity tests para los 3 helpers introducidos a partir del Manual del Trader Algorítmico:
  - adx_calc.py       (ADX/+DI/-DI + clasificación de régimen)
  - trailing_stop.py  (EMA-based trailing stop, modo de salida #4 del PDF)
  - backtest_split.py (out-of-sample validation, detector de overfit)

Run:
  python3 .claude/scripts/test_pdf_helpers.py
"""
from __future__ import annotations
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import adx_calc  # noqa: E402
import trailing_stop  # noqa: E402
import backtest_split  # noqa: E402
import macross  # noqa: E402
import per_asset_backtest  # noqa: E402

import json
import subprocess
import tempfile


def make_trending_bars(n: int = 60, slope: float = 1.0) -> list[dict]:
    bars = []
    p = 100.0
    for i in range(n):
        prev = p
        p += slope + math.sin(i / 3) * 0.2
        bars.append({"o": prev, "h": max(prev, p) + 0.5, "l": min(prev, p) - 0.5, "c": p})
    return bars


def make_ranging_bars(n: int = 60) -> list[dict]:
    bars = []
    prev = 100
    for i in range(n):
        c = 100 + math.sin(i / 2) * 2
        bars.append({"o": prev, "h": max(prev, c) + 0.3, "l": min(prev, c) - 0.3, "c": c})
        prev = c
    return bars


# ──────────────────────────────────────────────────────────────────
# ADX
# ──────────────────────────────────────────────────────────────────

def test_adx_trending_high():
    res = adx_calc.adx(make_trending_bars(slope=1.0), length=14)
    assert "error" not in res
    assert res["last_adx"] > 25, f"trending ADX should be >25, got {res['last_adx']}"


def test_adx_ranging_low():
    res = adx_calc.adx(make_ranging_bars(), length=14)
    assert "error" not in res
    assert res["last_adx"] < 25, f"ranging ADX should be <25, got {res['last_adx']}"


def test_adx_regime_labels():
    label = adx_calc.label_regime(15, 20, 18)
    assert label[0] == "RANGE_CHOP"
    assert "TREND_FUERTE" in adx_calc.label_regime(35, 30, 10)[0]
    assert "TREND_EXTREMO" in adx_calc.label_regime(45, 25, 10)[0]


def test_adx_short_data_errors():
    res = adx_calc.adx([{"h": 1, "l": 0, "c": 0.5}] * 10, length=14)
    assert "error" in res


# ──────────────────────────────────────────────────────────────────
# Trailing Stop
# ──────────────────────────────────────────────────────────────────

def test_trailing_long_holds_above_ema():
    bars = make_trending_bars(slope=1.0)
    last_close = bars[-1]["c"]
    res = trailing_stop.evaluate(bars, "long", entry=80, current=last_close + 5)
    assert res["action"] in ("HOLD", "HOLD_WARN"), res


def test_trailing_long_exits_when_price_below_ema():
    bars = make_trending_bars(slope=1.0)
    res = trailing_stop.evaluate(bars, "long", entry=80, current=90)
    assert res["action"] == "EXIT_TRAIL", res


def test_trailing_invalid_when_in_loss():
    bars = make_trending_bars()
    res = trailing_stop.evaluate(bars, "long", entry=200, current=100)
    assert res["action"] == "INVALID"


def test_trailing_short_mirrors_long():
    bars = make_trending_bars(slope=-1.0)
    last = bars[-1]["c"]
    # in profit short: entry above current, EMA above current
    res = trailing_stop.evaluate(bars, "short", entry=last + 30, current=last - 5)
    assert res["action"] in ("HOLD", "HOLD_WARN", "EXIT_TRAIL"), res


# ──────────────────────────────────────────────────────────────────
# OOS split
# ──────────────────────────────────────────────────────────────────

def test_temporal_split_proportions():
    bars = list(range(100))
    train, test = backtest_split.temporal_split(bars, 0.7)
    assert len(train) == 70 and len(test) == 30
    assert train[-1] == 69 and test[0] == 70  # secuencial


def test_temporal_split_rejects_small_data():
    try:
        backtest_split.temporal_split([1, 2, 3], 0.7)
    except ValueError:
        return
    raise AssertionError("expected ValueError for n<50")


def test_oos_pass_label():
    train = {"n": 20, "wr": 70, "pf": 2.0, "ret": 10, "dd": 4}
    test = {"n": 8, "wr": 65, "pf": 1.8, "ret": 8, "dd": 5}
    status, _ = backtest_split.degradation_flag(train, test)
    assert status == "PASS"


def test_oos_fail_on_return_flip():
    train = {"n": 20, "wr": 70, "pf": 2.0, "ret": 10, "dd": 4}
    test = {"n": 8, "wr": 65, "pf": 1.8, "ret": -2, "dd": 5}
    status, _ = backtest_split.degradation_flag(train, test)
    assert status == "FAIL"


def test_oos_fail_on_wr_collapse():
    train = {"n": 20, "wr": 80, "pf": 2.5, "ret": 15, "dd": 3}
    test = {"n": 8, "wr": 50, "pf": 1.0, "ret": 1, "dd": 6}
    status, _ = backtest_split.degradation_flag(train, test)
    assert status == "FAIL"


# ──────────────────────────────────────────────────────────────────
# MA Crossover
# ──────────────────────────────────────────────────────────────────

def test_macross_bull_cross():
    # Construct a series where EMA(9) crosses above EMA(21) in last bar
    closes = [100] * 25 + [c for c in range(100, 130)]
    res = macross.detect_cross(closes, 9, 21)
    assert res["signal"] in ("LONG", "BULL_TREND_NO_CROSS"), res


def test_macross_bear_alignment():
    closes = [c for c in range(150, 100, -1)]
    res = macross.detect_cross(closes, 9, 21)
    assert "BEAR" in res["signal"] or res["signal"] == "SHORT", res


def test_macross_neutral_when_choppy():
    closes = [100 + (i % 4 - 2) * 0.5 for i in range(50)]
    res = macross.detect_cross(closes, 9, 21)
    assert res["signal"] in ("NEUTRAL", "BULL_TREND_NO_CROSS", "BEAR_TREND_NO_CROSS"), res


def test_macross_handles_short_data():
    res = macross.detect_cross([100, 101, 102], 9, 21)
    assert res["signal"] == "NO_DATA"


# ──────────────────────────────────────────────────────────────────
# Per-asset backtest
# ──────────────────────────────────────────────────────────────────

def test_per_asset_runs_without_errors():
    bars_a = make_trending_bars(slope=1.0, n=100)
    bars_b = make_ranging_bars(n=100)
    res = per_asset_backtest.run_per_asset({"A": bars_a, "B": bars_b})
    assert "A" in res and "B" in res
    assert "full" in res["A"] and "n" in res["A"]["full"]


def test_per_asset_renders_table():
    bars_a = make_trending_bars(n=80)
    res = per_asset_backtest.run_per_asset({"X": bars_a})
    table = per_asset_backtest.render_table(res)
    assert "X" in table and "WR%" in table


# ──────────────────────────────────────────────────────────────────
# Macro Gate
# ──────────────────────────────────────────────────────────────────

def test_macro_gate_handles_missing_cache():
    """macro_gate.py --check-now exits 0 even with empty cache."""
    with tempfile.TemporaryDirectory() as d:
        empty = Path(d) / "nope.json"
        r = subprocess.run(
            ["python3", str(Path(__file__).parent / "macro_gate.py"),
             "--cache", str(empty), "--check-now"],
            capture_output=True, text=True
        )
        assert r.returncode == 0, f"Expected returncode 0, got {r.returncode}\nstderr: {r.stderr}"
        payload = json.loads(r.stdout)
        assert payload["blocked"] is False
        assert payload["reason"] == "no_cache"


def test_macro_gate_check_day_smoke():
    """macro_gate.py --check-day with empty cache returns empty events."""
    with tempfile.TemporaryDirectory() as d:
        empty = Path(d) / "nope.json"
        r = subprocess.run(
            ["python3", str(Path(__file__).parent / "macro_gate.py"),
             "--cache", str(empty), "--check-day", "2026-05-04"],
            capture_output=True, text=True
        )
        assert r.returncode == 0, f"Expected returncode 0, got {r.returncode}\nstderr: {r.stderr}"
        payload = json.loads(r.stdout)
        assert payload["events"] == []


# ──────────────────────────────────────────────────────────────────
# Runner
# ──────────────────────────────────────────────────────────────────

def main() -> int:
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__}: {type(e).__name__} {e}")
            failed += 1
    print(f"\n{len(tests)-failed}/{len(tests)} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
