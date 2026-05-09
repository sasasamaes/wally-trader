"""L3 — Re-weight composite score components based on actual outcomes via logistic regression."""
from __future__ import annotations

import json
import os
import csv
from pathlib import Path
from typing import Optional

DEFAULT_WEIGHTS = {
    "multifactor": 0.25,
    "regime_aligned": 0.20,
    "ml": 0.20,
    "sentiment": 0.15,
    "macro_clear": 0.10,
    "smart_router": 0.10,
}


def _weights_path(profile: str, profiles_dir: str = ".claude/profiles") -> Path:
    p = Path(profiles_dir) / profile / "memory" / "learning"
    p.mkdir(parents=True, exist_ok=True)
    return p / "composite_weights.json"


def _load_signals(profile: str, profiles_dir: str = ".claude/profiles") -> list[dict]:
    """Load signals_received.csv for a profile."""
    path = Path(profiles_dir) / profile / "memory" / "signals_received.csv"
    if not path.exists():
        return []
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _load_outcomes(profile: str, profiles_dir: str = ".claude/profiles") -> list[dict]:
    path = Path(profiles_dir) / profile / "memory" / "outcomes_v2.csv"
    if not path.exists():
        return []
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _build_feature_matrix(outcomes: list[dict]) -> tuple[list[list[float]], list[int]]:
    """Build (X, y) where X = component scores, y = 1 if win 0 if loss.

    Features: multifactor, regime_aligned(0/1 scaled 0-100), ml, sentiment, macro_clear, smart_router.
    We use whatever fields are available; missing → 50 (neutral).
    """
    X, y = [], []
    for row in outcomes:
        try:
            pnl = float(row.get("pnl_usd") or 0)
        except (ValueError, TypeError):
            continue

        # Map what we have
        try:
            multifactor = float(row.get("multifactor") or 50)
        except (ValueError, TypeError):
            multifactor = 50.0

        # regime_aligned: 100 if regime_at_entry matches a "good" regime, 0 otherwise
        regime = str(row.get("regime_at_entry") or "").upper()
        regime_aligned = 100.0 if "RANGE" in regime or "CHOP" not in regime else 0.0

        try:
            ml = float(row.get("ml_score") or 50)
        except (ValueError, TypeError):
            ml = 50.0

        try:
            sentiment = float(row.get("sentiment_score") or 50)
        except (ValueError, TypeError):
            sentiment = 50.0

        macro_clear = 100.0 if str(row.get("macro_clear") or "1") not in ("0", "False", "false") else 0.0
        smart_router = 100.0 if str(row.get("verdict") or "").upper() in ("APPROVE", "GO") else 50.0

        X.append([multifactor, regime_aligned, ml, sentiment, macro_clear, smart_router])
        y.append(1 if pnl > 0 else 0)

    return X, y


def _logistic_regression_weights(X: list[list[float]], y: list[int]) -> list[float]:
    """Simple logistic regression via gradient descent. Returns feature weights (raw)."""
    import math

    n = len(X)
    n_features = len(X[0]) if X else 6
    # Normalize features to [0,1]
    X_norm = [[xi / 100.0 for xi in row] for row in X]

    # Initialize weights
    w = [0.0] * n_features
    b = 0.0
    lr = 0.1
    epochs = 500

    for _ in range(epochs):
        dw = [0.0] * n_features
        db = 0.0
        total_loss = 0.0
        for xi, yi in zip(X_norm, y):
            # Sigmoid
            z = b + sum(w[j] * xi[j] for j in range(n_features))
            # Clamp to avoid overflow
            z = max(-500, min(500, z))
            pred = 1.0 / (1.0 + math.exp(-z))
            err = pred - yi
            for j in range(n_features):
                dw[j] += err * xi[j]
            db += err
        # Update
        for j in range(n_features):
            w[j] -= lr * dw[j] / n
        b -= lr * db / n

    # All weights must be positive (use softmax normalization)
    w_pos = [max(0.01, wi) for wi in w]
    total = sum(w_pos)
    normalized = [round(wi / total, 4) for wi in w_pos]

    # Ensure sum = 1.0 exactly (fix rounding)
    diff = round(1.0 - sum(normalized), 4)
    normalized[0] += diff
    return normalized


def fit_adaptive_weights(
    profile: str,
    n_trades: int = 50,
    *,
    profiles_dir: str = ".claude/profiles",
) -> dict:
    """Run logistic regression on closed trades.

    Returns new weights dict keyed by feature name (must sum to 1.0).
    Returns DEFAULT_WEIGHTS if insufficient data.
    """
    outcomes = _load_outcomes(profile, profiles_dir)
    closed = [r for r in outcomes if r.get("pnl_usd") not in (None, "", "0", "")]

    if len(closed) < n_trades:
        return {
            "status": "insufficient_data",
            "n_trades": len(closed),
            "n_required": n_trades,
            "weights": DEFAULT_WEIGHTS,
        }

    X, y = _build_feature_matrix(closed[-n_trades:])
    if len(set(y)) < 2:
        # All wins or all losses — can't fit
        return {
            "status": "degenerate_labels",
            "n_trades": len(closed),
            "weights": DEFAULT_WEIGHTS,
        }

    raw_weights = _logistic_regression_weights(X, y)
    keys = ["multifactor", "regime_aligned", "ml", "sentiment", "macro_clear", "smart_router"]
    new_weights = dict(zip(keys, raw_weights))

    return {
        "status": "ok",
        "n_trades": len(closed),
        "weights": new_weights,
    }


def _compute_auc(X: list[list[float]], y: list[int], weights: dict) -> float:
    """Compute ROC AUC for given feature weights."""
    keys = ["multifactor", "regime_aligned", "ml", "sentiment", "macro_clear", "smart_router"]
    scores = []
    for xi in X:
        s = sum(weights[k] * xi[i] / 100.0 for i, k in enumerate(keys))
        scores.append(s)

    # Compute AUC via trapezoidal rule
    pairs = sorted(zip(scores, y), key=lambda p: -p[0])
    n_pos = sum(y)
    n_neg = len(y) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5

    tp, fp = 0, 0
    prev_tp, prev_fp = 0, 0
    auc = 0.0
    for _, label in pairs:
        if label == 1:
            tp += 1
        else:
            fp += 1
        auc += (fp - prev_fp) * (tp + prev_tp) / 2
        prev_tp, prev_fp = tp, fp

    return auc / (n_pos * n_neg)


def ab_test_weights(
    old_weights: dict,
    new_weights: dict,
    trades: list[dict],
    *,
    min_auc_delta: float = 0.02,
) -> dict:
    """Backtest both weight sets on trades; promote new if AUC delta >= min_auc_delta.

    Returns dict with: promote (bool), old_auc, new_auc, delta.
    """
    X, y = _build_feature_matrix(trades)
    if not X or len(set(y)) < 2:
        return {"promote": False, "reason": "insufficient_or_degenerate_data", "old_auc": 0.5, "new_auc": 0.5, "delta": 0.0}

    old_auc = _compute_auc(X, y, old_weights)
    new_auc = _compute_auc(X, y, new_weights)
    delta = new_auc - old_auc

    return {
        "promote": delta >= min_auc_delta,
        "old_auc": round(old_auc, 4),
        "new_auc": round(new_auc, 4),
        "delta": round(delta, 4),
    }


def update_composite_weights(
    profile: str,
    new_weights: dict,
    *,
    profiles_dir: str = ".claude/profiles",
) -> None:
    """Write new weights to profile learning directory."""
    path = _weights_path(profile, profiles_dir)
    payload = {
        "profile": profile,
        "weights": new_weights,
        "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2))


def load_adaptive_weights(
    profile: Optional[str],
    *,
    profiles_dir: str = ".claude/profiles",
) -> Optional[dict]:
    """Load adaptive weights for profile. Returns None if missing/invalid."""
    if not profile:
        return None
    path = _weights_path(profile, profiles_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return data.get("weights")
    except Exception:
        return None
