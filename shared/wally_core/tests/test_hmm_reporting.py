"""Tests for hmm_lib.reporting — markdown emitter."""
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))

from hmm_lib import reporting
from hmm_lib.backtest import RegimeBacktest


def _sample_report() -> dict:
    return {
        "symbol": "ETHUSDT",
        "strategy": "A_VWAP",
        "date": "2026-05-13",
        "n_bars": 4360,
        "best_k": 3,
        "bic": -37934.6,
        "log_likelihood": 19105.2,
        "labels": {
            0: {"label": "TREND_UP", "mean_return": 0.0012, "mean_vol": 0.014,
                "pct_bars": 0.28, "low_sample": False},
            1: {"label": "CHOP", "mean_return": 0.0001, "mean_vol": 0.010,
                "pct_bars": 0.51, "low_sample": False},
            2: {"label": "STRESS", "mean_return": -0.0018, "mean_vol": 0.028,
                "pct_bars": 0.21, "low_sample": False},
        },
        "transition_matrix": np.array([[0.82, 0.15, 0.03],
                                       [0.09, 0.86, 0.05],
                                       [0.06, 0.18, 0.76]]),
        "backtests": [
            RegimeBacktest("GLOBAL", 4360, 1.0, 147, 51.7, 1.18, 8.3, 11.2, False),
            RegimeBacktest("TREND_UP", 1221, 0.28, 42, 42.9, 0.81, -3.1, 8.4, False),
            RegimeBacktest("CHOP", 2224, 0.51, 78, 61.5, 1.74, 12.8, 4.2, False),
            RegimeBacktest("STRESS", 915, 0.21, 27, 37.0, 0.62, -1.4, 6.8, False),
        ],
        "current_mapping_note": None,
        "caveats": [],
    }


def test_markdown_emits_all_required_sections(tmp_path):
    out = tmp_path / "report.md"
    reporting.emit_markdown(_sample_report(), out)
    content = out.read_text()
    for heading in ("# HMM Analysis", "## Summary", "## Regime Distribution",
                    "## Transition Matrix", "## Backtest per Regime",
                    "## Recommendations", "## Caveats"):
        assert heading in content, f"missing heading: {heading}"


def test_markdown_includes_all_regime_labels(tmp_path):
    out = tmp_path / "report.md"
    reporting.emit_markdown(_sample_report(), out)
    content = out.read_text()
    assert "TREND_UP" in content
    assert "CHOP" in content
    assert "STRESS" in content
    assert "GLOBAL" in content
