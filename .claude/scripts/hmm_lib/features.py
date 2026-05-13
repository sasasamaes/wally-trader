"""Feature engineering for HMM input: log_return, vol_20, momentum_14 (standardized)."""
import numpy as np
import pandas as pd

VOL_WINDOW = 20
MOMENTUM_WINDOW = 14
WARMUP = 20  # max(VOL_WINDOW, MOMENTUM_WINDOW + 6 buffer for stable estimates)


def _raw_log_returns(closes: np.ndarray) -> np.ndarray:
    """Return log_returns. First entry is NaN."""
    ratios = closes[1:] / closes[:-1]
    out = np.full(len(closes), np.nan)
    out[1:] = np.log(ratios)
    return out


def _rolling_std(x: np.ndarray, window: int) -> np.ndarray:
    """Rolling stdev. First (window-1) entries NaN. Uses pandas for correctness."""
    return pd.Series(x).rolling(window=window, min_periods=window).std().to_numpy()


def _momentum(closes: np.ndarray, window: int) -> np.ndarray:
    """(close[t] - close[t-window]) / close[t-window]. First `window` entries NaN."""
    out = np.full(len(closes), np.nan)
    out[window:] = (closes[window:] - closes[:-window]) / closes[:-window]
    return out


def build_features(bars: pd.DataFrame) -> np.ndarray:
    """Return (N, 3) standardized matrix: [log_return, vol_20, momentum_14].
    Drops initial WARMUP bars. Mean-centered, unit-variance per column.
    """
    closes = bars["close"].to_numpy()
    log_ret = _raw_log_returns(closes)
    vol_20 = _rolling_std(log_ret, VOL_WINDOW)
    mom_14 = _momentum(closes, MOMENTUM_WINDOW)

    stacked = np.column_stack([log_ret, vol_20, mom_14])
    trimmed = stacked[WARMUP:]

    if np.isnan(trimmed).any():
        # Drop any rows that still contain NaN (shouldn't happen with WARMUP=20)
        mask = ~np.isnan(trimmed).any(axis=1)
        trimmed = trimmed[mask]

    means = trimmed.mean(axis=0)
    stds = trimmed.std(axis=0)
    stds[stds == 0] = 1.0  # avoid div-by-zero on flat series
    standardized = (trimmed - means) / stds
    return standardized
