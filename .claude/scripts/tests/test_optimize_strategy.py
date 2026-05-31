"""Tests for optimize_strategy.py (optimization loop + Pine export)."""
import sys
from pathlib import Path

import numpy as np

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import optimize_strategy as opt


def _trend_bars(n: int = 600, start: float = 100.0, step: float = 0.4,
                wobble: float = 0.3) -> list[dict]:
    """Uptrend con ruido → da entradas donchian_ema y trades reales."""
    bars = []
    c = start
    for i in range(n):
        o = c
        c = o + step + wobble * np.sin(i / 5.0)
        h = max(o, c) + 0.2
        l = min(o, c) - 0.2
        bars.append({"t": i * 3600_000, "o": o, "h": h, "l": l, "c": c, "v": 1000.0})
    return bars


# ── métricas ──

def test_compute_metrics_empty():
    m = opt.compute_metrics([])
    assert m["n"] == 0 and m["pf"] == 0.0


def test_compute_metrics_basic():
    m = opt.compute_metrics([0.05, -0.02, 0.03, -0.01])
    assert m["n"] == 4
    assert m["wr"] == 50.0
    # PF = (0.05+0.03)/(0.02+0.01) = 0.08/0.03 ≈ 2.67
    assert m["pf"] == 2.67
    assert m["ret"] == 5.0  # sum 0.05 * 100


def test_compute_metrics_all_wins_pf_capped():
    m = opt.compute_metrics([0.01, 0.02, 0.03])
    assert m["pf"] == 999.0  # sin pérdidas → PF tope


# ── backtest + score ──

def test_backtest_config_returns_structure():
    bars = _trend_bars()
    params = {"don_len": 20, "ema_len": 200, "atr_len": 14, "sl_mult": 2.0, "max_hold": 48}
    bt = opt.backtest_config(bars, params, "long")
    assert "entries" in bt and "returns" in bt and "metrics" in bt
    assert len(bt["entries"]) == len(bt["returns"])


def test_base_score_penalizes_low_trades():
    assert opt.base_score({"n": 2, "wr": 99, "pf": 5, "ret": 50, "dd": 1, "sharpe": 3},
                          min_trades=15) < -1e8


def test_sample_config_in_space():
    rng = np.random.default_rng(1)
    p = opt.sample_config(rng)
    for k, vals in opt.SEARCH_SPACE.items():
        assert p[k] in vals


# ── loop de optimización ──

def test_optimize_runs_and_is_deterministic():
    bars = _trend_bars(600)
    r1 = opt.optimize(bars=bars, side="long", iterations=12, validate_top=2,
                      min_trades=3, rst_perms=120, mc_sims=15, seed=7)
    r2 = opt.optimize(bars=bars, side="long", iterations=12, validate_top=2,
                      min_trades=3, rst_perms=120, mc_sims=15, seed=7)
    assert r1["verdict"] == r2["verdict"]
    assert r1["leaderboard"] == r2["leaderboard"]
    assert r1["configs_tried"] >= 1
    assert r1["verdict"] in ("RECOMMEND", "NONE_SURVIVED")


def test_optimize_insufficient_bars():
    bars = _trend_bars(100)
    r = opt.optimize(bars=bars, iterations=5)
    assert "error" in r


def test_optimize_leaderboard_sorted_by_score():
    bars = _trend_bars(600)
    r = opt.optimize(bars=bars, side="long", iterations=15, validate_top=1,
                     min_trades=3, rst_perms=80, mc_sims=10, seed=3)
    scores = [c["score"] for c in r["leaderboard"]]
    assert scores == sorted(scores, reverse=True)


def test_optimize_minutes_budget_stops():
    """minutes=0 → no corre ninguna iteración (presupuesto agotado al instante)."""
    bars = _trend_bars(600)
    r = opt.optimize(bars=bars, iterations=999, minutes=0.0, validate_top=0,
                     min_trades=3, rst_perms=50, mc_sims=10, seed=1)
    assert r["configs_tried"] == 0
    assert r["verdict"] == "NONE_SURVIVED"


# ── Pine export ──

def test_to_pine_strategy_long_has_required_blocks():
    params = {"don_len": 20, "ema_len": 200, "atr_len": 14, "sl_mult": 2.0, "max_hold": 48}
    code = opt.to_pine_strategy(params, "BTCUSDT", "4h", "long",
                                {"n": 30, "wr": 55, "pf": 1.8, "ret": 40, "dd": 12, "sharpe": 1.2})
    assert code.startswith("//@version=6")
    assert "strategy(" in code
    assert "strategy.entry(\"Long\", strategy.long)" in code
    assert "ta.ema(close, emaLen)" in code
    assert "input.int(20" in code  # don_len inyectado


def test_to_pine_strategy_short_uses_short_block():
    params = {"don_len": 15, "ema_len": 100, "atr_len": 14, "sl_mult": 2.5, "max_hold": 24}
    code = opt.to_pine_strategy(params, "ETHUSDT", "1h", "short")
    assert "strategy.entry(\"Short\", strategy.short)" in code
    assert "strategy.entry(\"Long\"" not in code


def test_write_pine_creates_file(tmp_path):
    params = {"don_len": 20, "ema_len": 200, "atr_len": 14, "sl_mult": 2.0, "max_hold": 48}
    path = opt.write_pine(params, "BTCUSDT", "4h", "long", {"n": 30, "wr": 55, "pf": 1.8,
                          "ret": 40, "dd": 12, "sharpe": 1.2}, out_dir=str(tmp_path))
    p = Path(path)
    assert p.exists()
    assert p.read_text().startswith("//@version=6")
    assert p.name == "opt_donchian_ema_btcusdt_4h_long.pine"
