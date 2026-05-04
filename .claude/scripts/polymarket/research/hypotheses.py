"""Pure functions implementing H1-H4 of the research spec.

Each takes already-aligned data and returns a structured result dict.
No I/O, no side effects.
"""
from __future__ import annotations

import math
from typing import Any


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def _approx_p_value_from_corr(r: float, n: int) -> float | None:
    """Two-sided p-value approximation using Fisher z-transform."""
    if n < 4 or r is None or abs(r) >= 1.0:
        return None
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3)
    z_score = z / se
    # Two-sided p ≈ 2 * (1 - Φ(|z|))
    return 2 * (1 - 0.5 * (1 + math.erf(abs(z_score) / math.sqrt(2))))


def h1_composite_predicts_btc_return(aligned: list[tuple[float, float, float]]) -> dict[str, Any]:
    """aligned = [(pm_prob, btc_t, btc_t+window)] → corr(pm_prob, btc_return)."""
    if not aligned:
        return {"n": 0, "correlation": None, "p_value": None}
    probs = [a[0] for a in aligned]
    returns = [(a[2] - a[1]) / a[1] if a[1] != 0 else 0.0 for a in aligned]
    r = _pearson(probs, returns)
    p = _approx_p_value_from_corr(r, len(aligned)) if r is not None else None
    return {"n": len(aligned), "correlation": r, "p_value": p}


def h2_spike_predicts_volatility(
    rows: list[tuple[float, float]],
    *,
    spike_threshold: float = 0.05,
) -> dict[str, Any]:
    """rows = [(pm_delta_24h, btc_abs_return_t+24h)].

    Compares mean |btc_return| in spike rows vs baseline.
    """
    spike = [r for r in rows if abs(r[0]) >= spike_threshold]
    baseline = [r for r in rows if abs(r[0]) < spike_threshold]
    mean_spike = sum(r[1] for r in spike) / len(spike) if spike else None
    mean_base = sum(r[1] for r in baseline) / len(baseline) if baseline else None
    return {
        "spike_n": len(spike),
        "baseline_n": len(baseline),
        "mean_vol_spike": mean_spike,
        "mean_vol_baseline": mean_base,
        "spike_threshold": spike_threshold,
    }


def h3_pre_event_edge(
    rows: list[tuple[int, float, float]],
) -> dict[str, Any]:
    """rows = [(days_to_resolution, pm_prob, btc_return_t+24h)].

    Splits at days_to_resolution >= 0 (pre-event) vs < 0 (post-event)
    and computes correlation in each half.
    """
    pre = [r for r in rows if r[0] >= 0]
    post = [r for r in rows if r[0] < 0]

    def _corr(window: list[tuple[int, float, float]]):
        if not window:
            return {"n": 0, "correlation": None}
        xs = [r[1] for r in window]
        ys = [r[2] for r in window]
        r = _pearson(xs, ys)
        # Undefined correlation (constant input) → 0.0 (no predictive power)
        return {"n": len(window), "correlation": r if r is not None else 0.0}

    return {"pre_event": _corr(pre), "post_event": _corr(post)}


def h4_per_market_ic(
    series_per_market: dict[str, list[tuple[float, float]]],
    *,
    min_n: int = 30,
) -> dict[str, dict[str, Any]]:
    """Per-market information coefficient = corr(pm_prob, btc_fwd_return).

    series_per_market[slug] = [(pm_prob, btc_fwd_return), ...]
    Markets with sample below min_n are still computed but flagged.
    """
    out: dict[str, dict[str, Any]] = {}
    for slug, rows in series_per_market.items():
        n = len(rows)
        if n < 2:
            out[slug] = {"n": n, "ic": None, "flag": "INSUFFICIENT_DATA"}
            continue
        xs = [r[0] for r in rows]
        ys = [r[1] for r in rows]
        ic = _pearson(xs, ys)
        flag = "OK" if n >= min_n else "LOW_N"
        out[slug] = {"n": n, "ic": ic, "flag": flag}
    return out
