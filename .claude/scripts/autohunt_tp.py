#!/usr/bin/env python3
"""autohunt_tp.py — Dynamic TP formula for /punk-autohunt.

Pure-function module. No I/O. No side effects. Fully unit-testable.

Implements §4 of `docs/superpowers/specs/2026-05-12-punk-autohunt-design.md`:
  1. expected_move_pct = baseline × regime_mult × conf_mult × sess_mult, capped
     by structural obstacles (liq magnet, fib 1.618, hard 5%).
  2. TP1/TP2/TP3 are scaled multipliers of expected_move_pct (regime-dependent
     ladder, with close-% allocation also regime-dependent).
  3. $ PnL = (pct_move/100) × margin × leverage.
  4. $10 floor check: if tp3_$ < $10 → DROP_BELOW_FLOOR. A-GRADE may bump
     margin (capped 40% of capital) if `score >= 80`.
  5. ATR-percentile gate (Appendix B): if `atr_pct_percentile` is in top 5%
     of recent bars → flag `atr_extreme = True` for caller to drop the asset.
"""
from __future__ import annotations

import math
from typing import Optional

# ---------------------------------------------------------------------------
# Tunables (mirror §4 of the spec)
# ---------------------------------------------------------------------------
N_BARS_HORIZON = 6  # 6 × 15m = 90-min default holding horizon
HARD_CEILING_PCT = 5.0  # absolute %-move ceiling for 15m-1h horizon
STRUCTURAL_CAP_OVERSHOOT = 1.05  # allow 5% past the magnet/fib cap
PNL_FLOOR_USD = 10.0
ATR_EXTREME_PERCENTILE = 95.0  # top 5% → flag as too violent
A_GRADE_SCORE = 80
A_GRADE_MARGIN_CAP_USD = 75.0
A_GRADE_CAPITAL_PCT_CAP = 0.40  # margin ≤ 40% of capital
CAPITAL_USD_DEFAULT = 200.0  # bitunix profile

REGIME_MULTIPLIERS = {
    "STRONG_TREND_UP":   {"LONG": 1.6, "SHORT": 0.6},
    "STRONG_TREND_DOWN": {"LONG": 0.6, "SHORT": 1.6},
    "WEAK_TREND_UP":     {"LONG": 1.1, "SHORT": 0.8},
    "WEAK_TREND_DOWN":   {"LONG": 0.8, "SHORT": 1.1},
    "RANGING":           {"LONG": 0.9, "SHORT": 0.9},
    "SQUEEZE":           {"LONG": 1.3, "SHORT": 1.3},
    "MIXED":             {"LONG": 0.8, "SHORT": 0.8},
    "VOLATILE":          {"LONG": 0.7, "SHORT": 0.7},
    "UNKNOWN":           {"LONG": 0.8, "SHORT": 0.8},
}

# TP ladder per regime: (tp1_mult, tp2_mult, tp3_mult, close_pct_tuple)
TP_LADDER = {
    "STRONG_TREND_UP":   (0.30, 0.65, 1.00, (0.40, 0.30, 0.30)),
    "STRONG_TREND_DOWN": (0.30, 0.65, 1.00, (0.40, 0.30, 0.30)),
    "WEAK_TREND_UP":     (0.40, 0.75, 1.00, (0.50, 0.30, 0.20)),
    "WEAK_TREND_DOWN":   (0.40, 0.75, 1.00, (0.50, 0.30, 0.20)),
    "SQUEEZE":           (0.35, 0.70, 1.10, (0.40, 0.30, 0.30)),
    "RANGING":           (0.50, 0.85, 1.00, (0.60, 0.30, 0.10)),
    "MIXED":             (0.55, 0.85, 1.00, (0.70, 0.20, 0.10)),
    "VOLATILE":          (0.55, 0.85, 1.00, (0.70, 0.20, 0.10)),
    "UNKNOWN":           (0.55, 0.85, 1.00, (0.70, 0.20, 0.10)),
}


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def confluence_multiplier(score: float) -> float:
    """Linear 0.7..1.3 across confluence 60..100, clamped at the ends."""
    raw = 0.7 + (score - 60) / 40.0 * 0.6
    return _clamp(raw, 0.7, 1.3)


def session_multiplier(session_quality: str) -> float:
    """OK → 1.0, WARN → 0.7, anything else → 0.7 (defensive)."""
    return 1.0 if (session_quality or "").upper() == "OK" else 0.7


def baseline_move_pct(atr_pct_15m: float, n_bars: int = N_BARS_HORIZON) -> float:
    """Random-walk fair-value travel: sqrt(n) × ATR%."""
    if atr_pct_15m <= 0:
        return 0.0
    return math.sqrt(n_bars) * atr_pct_15m


def structural_cap_pct(
    magnet_dist_pct: Optional[float],
    fib_1618_dist_pct: Optional[float],
    hard_ceiling: float = HARD_CEILING_PCT,
) -> float:
    """Smallest among: magnet, fib 1.618, hard ceiling. Distances must be positive."""
    candidates = [hard_ceiling]
    for v in (magnet_dist_pct, fib_1618_dist_pct):
        if v is not None and v > 0:
            candidates.append(v)
    return min(candidates) * STRUCTURAL_CAP_OVERSHOOT


def expected_move_pct(
    atr_pct_15m: float,
    regime: str,
    side: str,
    confluence_score: float,
    session_quality: str = "OK",
    magnet_dist_pct: Optional[float] = None,
    fib_1618_dist_pct: Optional[float] = None,
) -> float:
    """Spec §4.2 — composite expected % move (favourable, from entry)."""
    baseline = baseline_move_pct(atr_pct_15m)
    rmult = REGIME_MULTIPLIERS.get(regime, REGIME_MULTIPLIERS["UNKNOWN"])
    regime_mult = rmult.get(side.upper(), 0.8)
    conf_mult = confluence_multiplier(confluence_score)
    sess_mult = session_multiplier(session_quality)
    raw = baseline * regime_mult * conf_mult * sess_mult
    cap = structural_cap_pct(magnet_dist_pct, fib_1618_dist_pct)
    return min(raw, cap)


def dollar_pnl(pct_move: float, margin_usd: float, leverage: int) -> float:
    """% move × notional → $."""
    notional = margin_usd * leverage
    return (pct_move / 100.0) * notional


def atr_extreme_gate(atr_percentile: Optional[float]) -> bool:
    """Appendix B: top 5% ATR → drop. None means caller didn't compute it (skip)."""
    if atr_percentile is None:
        return False
    return atr_percentile >= ATR_EXTREME_PERCENTILE


def compute_tp_plan(
    *,
    side: str,
    entry: float,
    atr_pct_15m: float,
    regime: str,
    confluence_score: float,
    session_quality: str = "OK",
    magnet_dist_pct: Optional[float] = None,
    fib_1618_dist_pct: Optional[float] = None,
    margin_usd: float = 50.0,
    leverage: int = 15,
    atr_percentile: Optional[float] = None,
    capital_usd: float = CAPITAL_USD_DEFAULT,
) -> dict:
    """End-to-end TP planner. Returns full diagnostic dict, never raises.

    Output schema:
      {
        "side": "LONG"|"SHORT",
        "entry": float,
        "expected_move_pct": float,
        "tp1": float, "tp2": float, "tp3": float,
        "tp1_pct": float, "tp2_pct": float, "tp3_pct": float,
        "tp1_usd": float, "tp2_usd": float, "tp3_usd": float,
        "close_pct": [tp1_close, tp2_close, tp3_close],
        "floor_passed": bool,
        "floor_status": "OK" | "DROP_BELOW_FLOOR" | "TP3_ONLY",
        "atr_extreme": bool,
        "regime_used": str,
        "components": { ... raw inputs and multipliers ... },
        "margin_used_usd": float,
        "leverage": int,
        "margin_bumped": bool,
      }
    """
    side_u = (side or "LONG").upper()
    sign = 1 if side_u == "LONG" else -1
    regime_used = regime if regime in TP_LADDER else "UNKNOWN"

    atr_extreme = atr_extreme_gate(atr_percentile)
    em_pct = expected_move_pct(
        atr_pct_15m=atr_pct_15m,
        regime=regime_used,
        side=side_u,
        confluence_score=confluence_score,
        session_quality=session_quality,
        magnet_dist_pct=magnet_dist_pct,
        fib_1618_dist_pct=fib_1618_dist_pct,
    )

    tp1_m, tp2_m, tp3_m, close_pct = TP_LADDER[regime_used]
    tp1_pct = em_pct * tp1_m
    tp2_pct = em_pct * tp2_m
    tp3_pct = em_pct * tp3_m

    tp1 = entry * (1 + sign * tp1_pct / 100.0)
    tp2 = entry * (1 + sign * tp2_pct / 100.0)
    tp3 = entry * (1 + sign * tp3_pct / 100.0)

    margin_used = margin_usd
    margin_bumped = False

    tp1_usd = dollar_pnl(tp1_pct, margin_used, leverage)
    tp2_usd = dollar_pnl(tp2_pct, margin_used, leverage)
    tp3_usd = dollar_pnl(tp3_pct, margin_used, leverage)

    # A-GRADE margin bump for $10-floor edge cases
    if (confluence_score >= A_GRADE_SCORE and tp3_usd < PNL_FLOOR_USD
            and em_pct > 0):
        needed_notional = PNL_FLOOR_USD / (em_pct / 100.0)
        needed_margin = needed_notional / leverage
        cap = min(A_GRADE_MARGIN_CAP_USD, capital_usd * A_GRADE_CAPITAL_PCT_CAP)
        if needed_margin <= cap:
            margin_used = math.ceil(needed_margin / 5.0) * 5.0
            margin_bumped = True
            tp1_usd = dollar_pnl(tp1_pct, margin_used, leverage)
            tp2_usd = dollar_pnl(tp2_pct, margin_used, leverage)
            tp3_usd = dollar_pnl(tp3_pct, margin_used, leverage)

    if tp3_usd < PNL_FLOOR_USD:
        floor_status = "DROP_BELOW_FLOOR"
        floor_passed = False
    elif tp1_usd >= PNL_FLOOR_USD:
        floor_status = "OK"
        floor_passed = True
    elif tp2_usd >= PNL_FLOOR_USD:
        floor_status = "OK_AT_TP2"
        floor_passed = True
    else:
        # only TP3 ≥ floor
        floor_status = "TP3_ONLY"
        # Strict gate: TP3-only is allowed only for A-GRADE in strong regimes
        is_strong = regime_used in ("STRONG_TREND_UP", "STRONG_TREND_DOWN", "SQUEEZE")
        is_a_grade = confluence_score >= A_GRADE_SCORE
        session_ok = (session_quality or "").upper() == "OK"
        floor_passed = is_strong and is_a_grade and session_ok

    return {
        "side": side_u,
        "entry": round(entry, 6),
        "expected_move_pct": round(em_pct, 4),
        "tp1": round(tp1, 6),
        "tp2": round(tp2, 6),
        "tp3": round(tp3, 6),
        "tp1_pct": round(tp1_pct, 4),
        "tp2_pct": round(tp2_pct, 4),
        "tp3_pct": round(tp3_pct, 4),
        "tp1_usd": round(tp1_usd, 2),
        "tp2_usd": round(tp2_usd, 2),
        "tp3_usd": round(tp3_usd, 2),
        "close_pct": list(close_pct),
        "floor_passed": bool(floor_passed),
        "floor_status": floor_status,
        "atr_extreme": atr_extreme,
        "regime_used": regime_used,
        "margin_used_usd": round(margin_used, 2),
        "leverage": leverage,
        "margin_bumped": margin_bumped,
        "components": {
            "atr_pct_15m": atr_pct_15m,
            "baseline_pct": round(baseline_move_pct(atr_pct_15m), 4),
            "regime_mult": REGIME_MULTIPLIERS.get(regime_used, {}).get(side_u),
            "conf_mult": round(confluence_multiplier(confluence_score), 3),
            "sess_mult": session_multiplier(session_quality),
            "structural_cap_pct": round(
                structural_cap_pct(magnet_dist_pct, fib_1618_dist_pct), 4),
            "atr_percentile": atr_percentile,
        },
    }


# ---------------------------------------------------------------------------
# Sanity self-test (run as `python autohunt_tp.py --sanity`)
# ---------------------------------------------------------------------------
def _sanity() -> int:
    """Validate the §4.4 example numbers. Exit 0 if all pass, 1 if any fails."""
    import json
    cases = [
        # SOL short, strong trend, conf 82, session OK → expected ~1.81%
        dict(
            label="SOL_SHORT_STRONG",
            kwargs=dict(
                side="SHORT", entry=145.20, atr_pct_15m=0.45,
                regime="STRONG_TREND_DOWN", confluence_score=82,
                session_quality="OK", magnet_dist_pct=5.0,
                fib_1618_dist_pct=3.2, margin_usd=50.0, leverage=15,
            ),
            expect_em_range=(1.5, 2.0),
            expect_floor=True,
        ),
        # BTC range chop, conf 65, session WARN → drop
        dict(
            label="BTC_LONG_RANGE_WARN",
            kwargs=dict(
                side="LONG", entry=68000, atr_pct_15m=0.18,
                regime="RANGING", confluence_score=65,
                session_quality="WARN", magnet_dist_pct=2.0,
                fib_1618_dist_pct=1.5, margin_usd=50.0, leverage=15,
            ),
            expect_em_range=(0.15, 0.30),
            expect_floor=False,
        ),
        # ETH long, strong trend, A-GRADE, $50×20x → expected ~5% → ~$50 TP3
        dict(
            label="ETH_LONG_STRONG_AGRADE",
            kwargs=dict(
                side="LONG", entry=3500, atr_pct_15m=1.3,
                regime="STRONG_TREND_UP", confluence_score=88,
                session_quality="OK", magnet_dist_pct=6.0,
                fib_1618_dist_pct=4.5, margin_usd=50.0, leverage=20,
            ),
            expect_em_range=(3.5, 5.5),
            expect_floor=True,
        ),
    ]
    fails = 0
    for case in cases:
        plan = compute_tp_plan(**case["kwargs"])
        em = plan["expected_move_pct"]
        em_lo, em_hi = case["expect_em_range"]
        em_ok = em_lo <= em <= em_hi
        floor_ok = plan["floor_passed"] == case["expect_floor"]
        ok = em_ok and floor_ok
        status = "PASS" if ok else "FAIL"
        if not ok:
            fails += 1
        print(f"[{status}] {case['label']}: em={em}% (expect {em_lo}-{em_hi}), "
              f"floor={plan['floor_passed']} (expect {case['expect_floor']}), "
              f"TP3=${plan['tp3_usd']}")
    print(json.dumps({"sanity_passed": fails == 0, "failures": fails}))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    import sys
    if "--sanity" in sys.argv:
        sys.exit(_sanity())
    print("This is a pure-function module. Use --sanity to self-test.")
