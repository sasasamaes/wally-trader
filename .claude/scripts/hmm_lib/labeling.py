"""State → human-readable regime label via mean_return × mean_vol heuristic."""
from dataclasses import dataclass
from typing import Protocol

import numpy as np

CHOP_RETURN_THRESHOLD = 0.0005      # |mean_ret| < this → CHOP override
LOW_SAMPLE_THRESHOLD = 0.05         # state with <5% bars flagged


class _FitLike(Protocol):
    states: np.ndarray
    k: int


def label_states(fit: _FitLike, features: np.ndarray) -> dict[int, dict]:
    """Returns {state_id: {label, mean_return, mean_vol, pct_bars, low_sample}}.

    Heuristic:
      mean_vol > p66                        → STRESS
      |mean_ret| < CHOP_RETURN_THRESHOLD    → CHOP
      mean_ret > 0:  vol < p33 → CALM_UP   else → TREND_UP
      mean_ret < 0:  vol < p33 → CALM_DOWN else → TREND_DOWN

    If two states get the same label, the higher-vol one is renamed STRESS_LITE.
    """
    states = fit.states
    n_total = len(states)
    log_ret_col = features[:, 0]
    vol_col = features[:, 1]

    per_state: dict[int, dict] = {}
    for sid in range(fit.k):
        mask = states == sid
        n = int(mask.sum())
        if n == 0:
            per_state[sid] = {
                "label": "EMPTY",
                "mean_return": 0.0,
                "mean_vol": 0.0,
                "pct_bars": 0.0,
                "low_sample": True,
            }
            continue
        per_state[sid] = {
            "mean_return": float(log_ret_col[mask].mean()),
            "mean_vol": float(vol_col[mask].mean()),
            "pct_bars": n / n_total,
            "low_sample": (n / n_total) < LOW_SAMPLE_THRESHOLD,
        }

    # Percentile thresholds across states (not bars)
    mean_vols = np.array([s["mean_vol"] for s in per_state.values()])
    p66 = np.percentile(mean_vols, 66) if len(mean_vols) > 0 else 0.0
    p33 = np.percentile(mean_vols, 33) if len(mean_vols) > 0 else 0.0

    for sid, info in per_state.items():
        if "label" in info:  # EMPTY already set
            continue
        mv = info["mean_vol"]
        mr = info["mean_return"]
        if mv > p66:
            label = "STRESS"
        elif abs(mr) < CHOP_RETURN_THRESHOLD:
            label = "CHOP"
        elif mr > 0:
            label = "CALM_UP" if mv < p33 else "TREND_UP"
        else:
            label = "CALM_DOWN" if mv < p33 else "TREND_DOWN"
        info["label"] = label

    # Disambiguate duplicates by promoting higher-vol to STRESS_LITE
    seen_labels: dict[str, int] = {}
    for sid in sorted(per_state.keys(),
                      key=lambda s: per_state[s]["mean_vol"], reverse=True):
        label = per_state[sid]["label"]
        if label in seen_labels and label != "EMPTY":
            per_state[sid]["label"] = f"{label}_LITE" if label != "STRESS" else "STRESS_LITE"
        else:
            seen_labels[label] = sid

    return per_state
