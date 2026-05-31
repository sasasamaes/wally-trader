"""Tests for rule_significance.py (RST permutation test)."""
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import rule_significance as rst


def _trend_bars(n: int = 400, start: float = 100.0, step: float = 0.5,
                noise: float = 0.0) -> list[dict]:
    """Serie con tendencia alcista determinista (close sube `step` por barra)."""
    bars = []
    c = start
    for i in range(n):
        o = c
        c = o + step + (noise * ((i % 7) - 3))
        h = max(o, c) + 0.1
        l = min(o, c) - 0.1
        bars.append({"t": i * 60000, "o": o, "h": h, "l": l, "c": c, "v": 1000.0})
    return bars


def test_aggregate_metrics():
    assert rst._aggregate([0.1, 0.2, -0.1], "total_return") == pytest.approx(0.2)
    assert rst._aggregate([0.1, 0.3], "mean_return") == pytest.approx(0.2)
    # sharpe of constant returns (std 0) → 0.0 guard
    assert rst._aggregate([0.1, 0.1, 0.1], "sharpe") == 0.0


def test_insufficient_entries_returns_insufficient():
    bars = _trend_bars(100)
    res = rst.significance_test(bars, [10, 20], rst.make_fixed_horizon_exit(5),
                                n_permutations=100)
    assert res["verdict"] == "INSUFFICIENT"


def test_edge_entries_beat_random_low_pvalue():
    """
    Entradas plantadas justo antes de subidas fuertes deben batir entradas aleatorias.
    Construimos serie con pumps localizados; las entradas reales caen en los pumps.
    """
    # Entradas reales en barras E; el pump (+10) ocurre en la barra E+1, DENTRO del
    # horizonte de salida → la entrada real captura el pump. Resto: drift bajista leve.
    entries = list(range(50, 350, 30))
    pump_after = {e + 1 for e in entries}
    bars = []
    c = 100.0
    for i in range(400):
        o = c
        c = o + (10.0 if i in pump_after else -0.05)
        h = max(o, c) + 0.1
        l = min(o, c) - 0.1
        bars.append({"t": i * 60000, "o": o, "h": h, "l": l, "c": c, "v": 1000.0})
    exit_fn = rst.make_fixed_horizon_exit(3)
    res = rst.significance_test(bars, entries, exit_fn, side="long",
                                n_permutations=1000, seed=7)
    assert res["verdict"] == "PASS"
    assert res["p_value"] < 0.05
    assert res["real_metric"] > res["null_mean"]


def test_random_entries_high_pvalue():
    """Entradas en barras arbitrarias de un random walk → no deben batir al azar."""
    import numpy as np
    rng = np.random.default_rng(123)
    bars = []
    c = 100.0
    for i in range(400):
        o = c
        c = o * (1 + rng.normal(0, 0.01))
        h = max(o, c) * 1.001
        l = min(o, c) * 0.999
        bars.append({"t": i * 60000, "o": o, "h": h, "l": l, "c": c, "v": 1000.0})
    # entradas "ciegas" cada 25 barras
    entries = list(range(30, 380, 25))
    exit_fn = rst.make_fixed_horizon_exit(5)
    res = rst.significance_test(bars, entries, exit_fn, side="long",
                                n_permutations=800, seed=42)
    # Sin edge plantado, el p-value típicamente NO es significativo
    assert res["verdict"] == "FAIL"
    assert res["p_value"] >= 0.05


def test_determinism_same_seed():
    bars = _trend_bars(300)
    entries = list(range(210, 280, 5))
    exit_fn = rst.make_fixed_horizon_exit(4)
    r1 = rst.significance_test(bars, entries, exit_fn, n_permutations=300, seed=11)
    r2 = rst.significance_test(bars, entries, exit_fn, n_permutations=300, seed=11)
    assert r1["p_value"] == r2["p_value"]
    assert r1["null_mean"] == r2["null_mean"]


def test_donchian_ema_entries_produces_signals_in_uptrend():
    bars = _trend_bars(500, step=0.5)
    entries = rst.donchian_ema_entries(bars, side="long", don_len=20, ema_len=200)
    # En una subida limpia el breakout long dispara al menos una vez
    assert len(entries) >= 1
    # Todas las entradas pasan el warmup
    assert all(i >= 200 for i in entries)


def test_donchian_atr_exit_returns_float():
    bars = _trend_bars(300, step=0.5)
    exit_fn = rst.make_donchian_atr_exit(don_len=20, atr_len=14, sl_mult=2.0, max_hold=20)
    r = exit_fn(bars, 250, "long")
    assert isinstance(r, float)


def test_fixed_horizon_exit_long_profit_in_uptrend():
    bars = _trend_bars(100, step=1.0)
    exit_fn = rst.make_fixed_horizon_exit(10)
    r = exit_fn(bars, 50, "long")
    assert r > 0  # subida → long gana
