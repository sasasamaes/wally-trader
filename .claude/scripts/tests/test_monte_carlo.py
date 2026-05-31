"""Tests for monte_carlo.py (trades reshuffle + candles block-bootstrap)."""
import sys
from pathlib import Path

import numpy as np

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import monte_carlo as mc


def _trend_bars(n: int = 500, start: float = 100.0, step: float = 0.5) -> list[dict]:
    bars = []
    c = start
    for i in range(n):
        o = c
        c = o + step
        h = max(o, c) + 0.1
        l = min(o, c) - 0.1
        bars.append({"t": i * 60000, "o": o, "h": h, "l": l, "c": c, "v": 1000.0})
    return bars


def test_max_drawdown_basic():
    curve = np.array([0, 1, 2, 1, 0, 3])  # peak 2 then down to 0 → dd 2
    assert mc.max_drawdown(curve) == 2.0


def test_max_drawdown_monotonic_up_is_zero():
    curve = np.array([0.0, 1.0, 2.0, 3.0])
    assert mc.max_drawdown(curve) == 0.0


def test_mc_trades_reshuffle_preserves_total_return():
    returns = [0.05, -0.02, 0.03, -0.04, 0.06, -0.01, 0.02, -0.03]
    res = mc.monte_carlo_trades(returns, n_sims=500, seed=7, method="reshuffle")
    # El retorno final es invariante bajo reordenamiento puro
    assert res["orig_ret"] == round(sum(returns), 4)
    # Pero el max DD varía → p95 >= mediana >= p5
    assert res["dd_p95"] >= res["dd_median"] >= res["dd_p5"]


def test_mc_trades_insufficient():
    res = mc.monte_carlo_trades([0.1, -0.1], n_sims=100)
    assert res["verdict"] == "INSUFFICIENT"


def test_mc_trades_bootstrap_varies_return():
    returns = [0.05, -0.02, 0.03, -0.04, 0.06, -0.01, 0.02, -0.03]
    res = mc.monte_carlo_trades(returns, n_sims=500, seed=7, method="bootstrap")
    # Bootstrap con reemplazo → retorno varía, hay percentiles de ret
    assert "ret_p5" in res and "ret_p95" in res
    assert res["ret_p95"] >= res["ret_median"] >= res["ret_p5"]


def test_mc_trades_determinism():
    returns = [0.05, -0.02, 0.03, -0.04, 0.06, -0.01]
    r1 = mc.monte_carlo_trades(returns, n_sims=200, seed=3)
    r2 = mc.monte_carlo_trades(returns, n_sims=200, seed=3)
    assert r1["dd_p95"] == r2["dd_p95"]


def test_synthetic_bars_preserve_length():
    bars = _trend_bars(300)
    rng = np.random.default_rng(7)
    syn = mc.synthetic_bars(bars, rng, block=10)
    assert len(syn) == len(bars)
    # OHLC consistente: high es el máximo, low el mínimo
    for b in syn:
        assert b["h"] >= max(b["o"], b["c"]) - 1e-9
        assert b["l"] <= min(b["o"], b["c"]) + 1e-9


def test_synthetic_bars_positive_prices():
    bars = _trend_bars(300)
    rng = np.random.default_rng(11)
    syn = mc.synthetic_bars(bars, rng, block=8)
    assert all(b["c"] > 0 for b in syn)


def test_mc_candles_overfit_flag_on_memorized_strategy():
    """
    Estrategia que devuelve un Sharpe altísimo SOLO en la data real (la 'memoriza')
    y ~0 en cualquier sintética → overfit_flag debe activarse.
    """
    real = _trend_bars(400)
    real_id = id(real)

    def memorizing_strategy(bars):
        # Reconoce la serie real exacta por identidad; en sintéticas rinde ~0
        return 5.0 if id(bars) == real_id else 0.0

    res = mc.monte_carlo_candles(real, memorizing_strategy, n_sims=50, seed=7)
    assert res["overfit_flag"] is True
    assert res["zone"] == "OVERFIT_SUSPECT"
    assert res["verdict"] == "WARN"


def test_mc_candles_robust_when_orig_near_distribution():
    """Estrategia con Sharpe constante → orig == mediana → zona ROBUST, sin overfit."""
    real = _trend_bars(400)

    def constant_strategy(bars):
        return 1.0

    res = mc.monte_carlo_candles(real, constant_strategy, n_sims=40, seed=7)
    assert res["overfit_flag"] is False
    assert res["zone"] == "ROBUST"


def test_sharpe_zero_for_constant():
    assert mc.sharpe(np.array([0.1, 0.1, 0.1])) == 0.0


def test_sharpe_positive_for_positive_mean_with_variance():
    s = mc.sharpe(np.array([0.1, 0.2, 0.05, 0.15]))
    assert s > 0
