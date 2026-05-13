"""Tests for hmm_lib.labeling — state → human-readable regime label."""
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))

from hmm_lib import labeling


@dataclass
class _FakeFit:
    """Minimal stand-in for HMMFit used in labeling tests."""
    states: np.ndarray
    k: int


def _make_fake_fit_and_features(state_stats: list[dict]) -> tuple[_FakeFit, np.ndarray]:
    """state_stats: list of {'n': bars, 'log_ret': mean_log_return, 'vol': mean_vol}.
    Builds states array assigning each bar to its state, and synthetic features
    such that feature[:, 0] = log_return, feature[:, 1] = vol_20 (raw, not standardized).
    """
    states = []
    features_rows = []
    for sid, stats in enumerate(state_stats):
        states.extend([sid] * stats["n"])
        for _ in range(stats["n"]):
            # Place stats in columns 0 (log_ret) and 1 (vol_20)
            features_rows.append([stats["log_ret"], stats["vol"], 0.0])
    return _FakeFit(np.array(states), len(state_stats)), np.array(features_rows)


def test_high_vol_negative_return_is_stress():
    fit, features = _make_fake_fit_and_features([
        {"n": 800, "log_ret": +0.001, "vol": 0.01},
        {"n": 200, "log_ret": -0.005, "vol": 0.05},  # high vol, neg return
    ])
    labels = labeling.label_states(fit, features)
    assert labels[1]["label"] == "STRESS"


def test_low_vol_positive_return_is_calm_up():
    fit, features = _make_fake_fit_and_features([
        {"n": 800, "log_ret": +0.002, "vol": 0.005},  # low vol, pos return
        {"n": 200, "log_ret": -0.005, "vol": 0.05},
    ])
    labels = labeling.label_states(fit, features)
    assert labels[0]["label"] in ("CALM_UP", "TREND_UP")


def test_low_sample_flag_set_below_threshold():
    fit, features = _make_fake_fit_and_features([
        {"n": 970, "log_ret": +0.0001, "vol": 0.01},
        {"n": 30, "log_ret": -0.001, "vol": 0.02},  # 3% bars → low_sample
    ])
    labels = labeling.label_states(fit, features)
    assert labels[0]["low_sample"] is False
    assert labels[1]["low_sample"] is True


def test_returns_pct_bars_for_each_state():
    fit, features = _make_fake_fit_and_features([
        {"n": 600, "log_ret": +0.001, "vol": 0.01},
        {"n": 300, "log_ret": -0.001, "vol": 0.02},
        {"n": 100, "log_ret": -0.005, "vol": 0.04},
    ])
    labels = labeling.label_states(fit, features)
    assert abs(labels[0]["pct_bars"] - 0.60) < 1e-6
    assert abs(labels[1]["pct_bars"] - 0.30) < 1e-6
    assert abs(labels[2]["pct_bars"] - 0.10) < 1e-6
