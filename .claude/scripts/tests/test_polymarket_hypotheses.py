"""Tests for polymarket.research.hypotheses."""
import math
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from polymarket.research import hypotheses


def test_h1_correlation_perfect_positive():
    # composite = pm_prob, btc_return = pm_prob (identical) ⇒ corr = 1
    aligned = [(0.4, 100.0, 110.0), (0.5, 100.0, 105.0), (0.6, 100.0, 100.0), (0.7, 100.0, 95.0)]
    # btc_return: +10%, +5%, 0%, -5% — and pm_prob 0.4..0.7 ⇒ negative correlation
    res = hypotheses.h1_composite_predicts_btc_return(aligned)
    assert res["n"] == 4
    assert res["correlation"] < -0.95  # near -1
    assert "p_value" in res


def test_h2_spike_predicts_volatility():
    # synthetic: every spike row has high subsequent volatility, baseline rows low
    # input shape: list[(pm_delta_24h, btc_abs_return_24h_after)]
    rows = [
        (0.06, 0.05),  # spike
        (0.08, 0.06),  # spike
        (0.01, 0.01),  # baseline
        (0.02, 0.005),  # baseline
        (0.07, 0.04),  # spike
    ]
    res = hypotheses.h2_spike_predicts_volatility(rows, spike_threshold=0.05)
    assert res["spike_n"] == 3
    assert res["baseline_n"] == 2
    assert res["mean_vol_spike"] > res["mean_vol_baseline"]


def test_h3_pre_event_edge():
    # rows: (days_to_resolution, pm_prob, btc_return_t+24h)
    # Pre-event window: high correlation; post-event: noise
    pre = [(2, 0.6, 0.05), (1, 0.65, 0.06), (0, 0.7, 0.07)]
    post = [(-1, 0.5, -0.01), (-2, 0.5, 0.005)]
    res = hypotheses.h3_pre_event_edge(pre + post)
    assert res["pre_event"]["n"] == 3
    assert res["post_event"]["n"] == 2
    # Pre should have stronger absolute correlation
    assert abs(res["pre_event"]["correlation"]) > abs(res["post_event"]["correlation"])


def test_h4_per_market_ic():
    # Two synthetic markets: one with strong IC, one with zero IC
    series = {
        "good-market": [(0.4, 0.05), (0.5, 0.0), (0.6, -0.05), (0.7, -0.10)],  # strong negative
        "noise-market": [(0.4, 0.0), (0.5, 0.0), (0.4, 0.0), (0.5, 0.0)],  # constant ⇒ undefined or 0
    }
    res = hypotheses.h4_per_market_ic(series, min_n=2)
    assert "good-market" in res
    assert abs(res["good-market"]["ic"]) > 0.95
    # noise-market: stdev zero on btc side, IC should be None
    assert res["noise-market"]["ic"] is None


def test_pearson_correlation_handles_constant():
    assert hypotheses._pearson([1, 1, 1], [1, 2, 3]) is None
