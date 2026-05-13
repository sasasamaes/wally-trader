"""Tests for hmm_lib.features — feature engineering."""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))

from hmm_lib import features


def _make_bars(closes: list[float]) -> pd.DataFrame:
    n = len(closes)
    return pd.DataFrame({
        "open": closes,
        "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes],
        "close": closes,
        "volume": [1000.0] * n,
        "ts_utc": pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC"),
    })


def test_log_returns_match_manual():
    closes = [100.0, 101.0, 99.0, 100.0, 102.0]
    bars = _make_bars(closes)
    raw = features._raw_log_returns(bars["close"].to_numpy())
    # First bar has NaN return — verify subsequent
    assert math.isclose(raw[1], math.log(101 / 100), abs_tol=1e-9)
    assert math.isclose(raw[2], math.log(99 / 101), abs_tol=1e-9)
    assert math.isclose(raw[3], math.log(100 / 99), abs_tol=1e-9)


def test_features_drops_warmup_bars():
    bars = _make_bars([100.0 + i for i in range(100)])
    matrix = features.build_features(bars)
    # warmup = 20 (max of vol_20 lookback, momentum_14 lookback)
    assert matrix.shape == (80, 3)


def test_features_are_standardized():
    rng = np.random.default_rng(seed=42)
    closes = (100 + rng.standard_normal(500).cumsum()).tolist()
    bars = _make_bars(closes)
    matrix = features.build_features(bars)
    # Each column mean ≈ 0, std ≈ 1
    means = matrix.mean(axis=0)
    stds = matrix.std(axis=0)
    assert np.allclose(means, 0, atol=1e-9), f"means={means}"
    assert np.allclose(stds, 1.0, atol=1e-2), f"stds={stds}"
