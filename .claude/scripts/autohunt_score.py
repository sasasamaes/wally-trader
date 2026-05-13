#!/usr/bin/env python3
"""autohunt_score.py — Confluence fusion (0-100) for /punk-autohunt.

Pure-function module. No I/O. Side-effect free.

Implements §3 Stage 5 of `docs/superpowers/specs/2026-05-12-punk-autohunt-design.md`.

The 11-component scoring table has BTC/ETH-only components (USDT.D, on-chain).
For altcoins those weights redistribute proportionally to the remaining
components.

For the MVP, two components are intentionally NOT wired and are skipped via
component-missing graceful degradation:
  - pump_score (5)
  - on_chain_bias (5, BTC/ETH only)

The score module accepts any subset of components and normalizes whatever is
provided. Missing component → weight excluded from the denominator.

Tier thresholds:
  >= 80 → A-GRADE (force-propose if PnL floor passes)
  70-79 → B-GRADE
  60-69 → C-GRADE (propose only if no higher-tier asset exists)
  <  60 → DROP

The score range is 0..100. Negative contributions are clamped to 0 when summed,
but components individually may carry a sign-mismatch penalty (returning 0
weight instead of full).
"""
from __future__ import annotations

import math
from typing import Optional

# ---------------------------------------------------------------------------
# Component weight catalogue
# (key, default_weight, btc_eth_only)
# ---------------------------------------------------------------------------
WEIGHTS = [
    ("backtest_pnl_per_trade", 20, False),
    ("multifactor_score",       20, False),
    ("rr_tp1",                  10, False),
    ("liq_magnet_alignment",    10, False),
    ("fib_retracement_quality", 10, False),
    ("obv_slope_alignment",      5, False),
    ("smart_money_ls_alignment", 5, False),
    ("pump_score_alignment",     5, False),  # MVP: usually missing
    ("sentiment_funding_ok",     5, False),
    ("usdt_d_bias_alignment",    5, True),
    ("on_chain_bias_alignment",  5, True),   # MVP: usually missing
]

BTC_ETH_SYMBOLS = {"BTCUSDT", "ETHUSDT", "BTCUSD", "ETHUSD"}

TIER_A_MIN = 80
TIER_B_MIN = 70
TIER_C_MIN = 60


def _is_btc_eth(symbol: str) -> bool:
    """Match symbol against the BTC/ETH whitelist (case-insensitive, .P-tolerant)."""
    norm = (symbol or "").replace(".P", "").replace("PERP", "").upper().strip()
    return norm in BTC_ETH_SYMBOLS


# ---------------------------------------------------------------------------
# Component normalisers — each returns a 0..1 contribution
# ---------------------------------------------------------------------------
def _norm_backtest_pnl(value: Optional[float], n_trades: Optional[int] = None) -> Optional[float]:
    """pnl_per_trade in USD. Saturates at $2.5/trade. Decayed by n_trades<30."""
    if value is None:
        return None
    base = max(0.0, min(value / 2.5, 1.0))
    if n_trades is not None:
        decay = min(1.0, n_trades / 30.0)
        base *= decay
    return base


def _norm_multifactor(score: Optional[float], side: str) -> Optional[float]:
    """multifactor_score ranges -100..+100, sign should match side."""
    if score is None:
        return None
    if side.upper() == "LONG":
        return max(0.0, min(score / 100.0, 1.0))
    return max(0.0, min(-score / 100.0, 1.0))


def _norm_rr(rr_tp1: Optional[float]) -> Optional[float]:
    """R:R TP1 — full credit at 2.0, zero at 1.0 or below."""
    if rr_tp1 is None:
        return None
    return max(0.0, min((rr_tp1 - 1.0) / 1.0, 1.0))


def _norm_magnet_alignment(
    entry: float, tp1: float, magnet: Optional[float], side: str,
) -> Optional[float]:
    """Magnet should be on the trade side AND TP1 ≤ magnet distance."""
    if magnet is None or magnet <= 0 or entry <= 0:
        return None
    side_u = side.upper()
    if side_u == "LONG" and magnet <= entry:
        return 0.0  # magnet on wrong side
    if side_u == "SHORT" and magnet >= entry:
        return 0.0
    tp1_dist = abs(tp1 - entry)
    magnet_dist = abs(magnet - entry)
    if magnet_dist <= 0:
        return 0.0
    # Full credit if TP1 leaves room for TP2/TP3 before the magnet
    ratio = tp1_dist / magnet_dist
    if ratio <= 0.40:
        return 1.0
    if ratio >= 0.95:
        return 0.0
    # Linear decay 0.40..0.95
    return max(0.0, 1.0 - (ratio - 0.40) / 0.55)


def _norm_fib_retracement(zone: Optional[str]) -> Optional[float]:
    """Quality of retracement zone. zone ∈ {OTE, GOLDEN, SHALLOW, DEEP, OUT}."""
    if zone is None:
        return None
    table = {
        "OTE": 1.0,        # 0.618-0.786 ideal
        "GOLDEN": 0.9,     # 0.5-0.618
        "SHALLOW": 0.5,    # 0.382-0.5
        "DEEP": 0.3,       # 0.786-0.886
        "OUT": 0.0,        # not in retracement zone
    }
    return table.get(zone.upper(), 0.0)


def _norm_obv_alignment(verdict: Optional[str]) -> Optional[float]:
    """volume_divergence verdict ∈ {OK, WARN, BLOCK}. Aligned → 1, divergent → 0."""
    if verdict is None:
        return None
    return {"OK": 1.0, "WARN": 0.5, "BLOCK": 0.0}.get(verdict.upper(), 0.5)


def _norm_smart_money_ls(retail_ls: Optional[float], smart_ls: Optional[float],
                          side: str) -> Optional[float]:
    """Smart money L/S should LEAN with side. Retail divergence is a bonus."""
    if smart_ls is None:
        return None
    side_u = side.upper()
    # smart_ls > 1 → smart money net long; < 1 → net short
    if side_u == "LONG":
        smart_aligned = max(0.0, min((smart_ls - 1.0) / 0.5, 1.0))
    else:
        smart_aligned = max(0.0, min((1.0 - smart_ls) / 0.5, 1.0))
    if retail_ls is None:
        return smart_aligned
    # Retail contrarian = bonus
    if side_u == "LONG":
        retail_contrarian = max(0.0, min((1.0 - retail_ls) / 0.5, 1.0))
    else:
        retail_contrarian = max(0.0, min((retail_ls - 1.0) / 0.5, 1.0))
    return 0.7 * smart_aligned + 0.3 * retail_contrarian


def _norm_pump_alignment(pump_score: Optional[float], side_bias: Optional[str],
                         side: str) -> Optional[float]:
    """Pump score 0-100 with side_bias ∈ {LONG, SHORT, NONE}. Match → score/100."""
    if pump_score is None:
        return None
    if side_bias and side_bias.upper() == side.upper():
        return max(0.0, min(pump_score / 100.0, 1.0))
    if side_bias and side_bias.upper() == "NONE":
        return 0.3  # neutral
    return 0.0  # opposing bias


def _norm_sentiment_funding(passed: Optional[bool]) -> Optional[float]:
    """Vetos sentiment+funding both passed → 1.0. Else fallback 0.5 if missing."""
    if passed is None:
        return None
    return 1.0 if passed else 0.0


def _norm_usdt_d(bias: Optional[str], side: str) -> Optional[float]:
    """USDT.D bias ∈ {BEARISH, NEUTRAL, BULLISH} on BTC. Inverse-correlated."""
    if bias is None:
        return None
    bias_u = bias.upper()
    side_u = side.upper()
    # BEARISH (usdt.d rising) → bad for BTC long
    if side_u == "LONG":
        return {"BEARISH": 0.2, "NEUTRAL": 0.6, "BULLISH": 1.0}.get(bias_u, 0.5)
    return {"BEARISH": 1.0, "NEUTRAL": 0.6, "BULLISH": 0.2}.get(bias_u, 0.5)


def _norm_on_chain(bias: Optional[str], side: str) -> Optional[float]:
    """On-chain bias ∈ {BULL, NEUTRAL, BEAR}."""
    if bias is None:
        return None
    bias_u = bias.upper()
    side_u = side.upper()
    if side_u == "LONG":
        return {"BULL": 1.0, "NEUTRAL": 0.5, "BEAR": 0.2}.get(bias_u, 0.5)
    return {"BULL": 0.2, "NEUTRAL": 0.5, "BEAR": 1.0}.get(bias_u, 0.5)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def compute_score(
    *,
    symbol: str,
    side: str,
    # required confluence inputs (any may be None → component skipped)
    backtest_pnl_per_trade: Optional[float] = None,
    backtest_n_trades: Optional[int] = None,
    multifactor_score: Optional[float] = None,
    rr_tp1: Optional[float] = None,
    entry: Optional[float] = None,
    tp1: Optional[float] = None,
    liq_magnet: Optional[float] = None,
    fib_zone: Optional[str] = None,
    obv_verdict: Optional[str] = None,
    smart_money_ls: Optional[float] = None,
    retail_ls: Optional[float] = None,
    pump_score: Optional[float] = None,
    pump_side_bias: Optional[str] = None,
    sentiment_funding_passed: Optional[bool] = None,
    usdt_d_bias: Optional[str] = None,
    on_chain_bias: Optional[str] = None,
) -> dict:
    """Fuse heterogeneous confluence signals into a 0-100 score + tier.

    Missing components (passed as None) are excluded from the denominator —
    the remaining weights are renormalised so a partial-data score still
    spans 0-100.

    Returns:
      {
        "score": 0..100,
        "tier": "A-GRADE"|"B-GRADE"|"C-GRADE"|"DROP",
        "components": [{name, weight, value_0_1, contribution, used: bool}],
        "denominator_weight": int,  # sum of weights actually used
      }
    """
    side_u = (side or "LONG").upper()
    is_btc_eth = _is_btc_eth(symbol)

    normalised = {
        "backtest_pnl_per_trade":
            _norm_backtest_pnl(backtest_pnl_per_trade, backtest_n_trades),
        "multifactor_score":
            _norm_multifactor(multifactor_score, side_u),
        "rr_tp1":
            _norm_rr(rr_tp1),
        "liq_magnet_alignment":
            _norm_magnet_alignment(entry or 0, tp1 or 0, liq_magnet, side_u)
            if (entry is not None and tp1 is not None) else None,
        "fib_retracement_quality":
            _norm_fib_retracement(fib_zone),
        "obv_slope_alignment":
            _norm_obv_alignment(obv_verdict),
        "smart_money_ls_alignment":
            _norm_smart_money_ls(retail_ls, smart_money_ls, side_u),
        "pump_score_alignment":
            _norm_pump_alignment(pump_score, pump_side_bias, side_u),
        "sentiment_funding_ok":
            _norm_sentiment_funding(sentiment_funding_passed),
        "usdt_d_bias_alignment":
            _norm_usdt_d(usdt_d_bias, side_u) if is_btc_eth else None,
        "on_chain_bias_alignment":
            _norm_on_chain(on_chain_bias, side_u) if is_btc_eth else None,
    }

    components: list[dict] = []
    used_weight_total = 0
    weighted_sum = 0.0
    for name, weight, btc_eth_only in WEIGHTS:
        # For non-BTC/ETH symbols, btc_eth_only components are excluded entirely
        if btc_eth_only and not is_btc_eth:
            components.append({
                "name": name, "weight": weight,
                "value_0_1": None, "contribution": 0,
                "used": False, "reason": "btc_eth_only",
            })
            continue
        v = normalised.get(name)
        if v is None:
            components.append({
                "name": name, "weight": weight,
                "value_0_1": None, "contribution": 0,
                "used": False, "reason": "missing",
            })
            continue
        contrib = v * weight
        weighted_sum += contrib
        used_weight_total += weight
        components.append({
            "name": name, "weight": weight,
            "value_0_1": round(v, 3),
            "contribution": round(contrib, 2),
            "used": True,
        })

    # Renormalise to 0-100 over the weights actually used
    if used_weight_total == 0:
        score = 0.0
    else:
        score = (weighted_sum / used_weight_total) * 100.0

    score = max(0.0, min(100.0, score))

    if score >= TIER_A_MIN:
        tier = "A-GRADE"
    elif score >= TIER_B_MIN:
        tier = "B-GRADE"
    elif score >= TIER_C_MIN:
        tier = "C-GRADE"
    else:
        tier = "DROP"

    return {
        "score": round(score, 1),
        "tier": tier,
        "components": components,
        "denominator_weight": used_weight_total,
        "symbol_is_btc_eth": is_btc_eth,
    }


# ---------------------------------------------------------------------------
# Sanity self-test
# ---------------------------------------------------------------------------
def _sanity() -> int:
    import json
    cases = [
        # 1. Ideal SOL short: full bonus across the board (alt = 9 components)
        dict(
            label="SOL_SHORT_IDEAL",
            kwargs=dict(
                symbol="SOLUSDT", side="SHORT",
                backtest_pnl_per_trade=2.5, backtest_n_trades=40,
                multifactor_score=-75, rr_tp1=2.0,
                entry=145.0, tp1=143.5, liq_magnet=137.5,
                fib_zone="GOLDEN", obv_verdict="OK",
                smart_money_ls=0.5, retail_ls=1.4,
                pump_score=80, pump_side_bias="SHORT",
                sentiment_funding_passed=True,
            ),
            expect_score_min=75,
            expect_tier="A-GRADE",
        ),
        # 2. BTC long mediocre: most components weak
        dict(
            label="BTC_LONG_MEDIOCRE",
            kwargs=dict(
                symbol="BTCUSDT", side="LONG",
                backtest_pnl_per_trade=0.5, backtest_n_trades=20,
                multifactor_score=15, rr_tp1=1.4,
                entry=68000, tp1=68500, liq_magnet=70000,
                fib_zone="SHALLOW", obv_verdict="WARN",
                smart_money_ls=1.0, retail_ls=1.2,
                pump_score=20, pump_side_bias="NONE",
                sentiment_funding_passed=True,
                usdt_d_bias="NEUTRAL",
            ),
            expect_score_min=20,
            expect_score_max=60,
            expect_tier_in=("DROP", "C-GRADE"),
        ),
        # 3. Missing data graceful: only 3 components
        dict(
            label="ETH_LONG_PARTIAL",
            kwargs=dict(
                symbol="ETHUSDT", side="LONG",
                backtest_pnl_per_trade=2.0, backtest_n_trades=30,
                multifactor_score=70,
                sentiment_funding_passed=True,
            ),
            expect_denominator_min=25,  # 20 + 20 + 5 = 45 max
        ),
    ]
    fails = 0
    for case in cases:
        out = compute_score(**case["kwargs"])
        msgs = []
        if "expect_score_min" in case and out["score"] < case["expect_score_min"]:
            msgs.append(f"score {out['score']} < {case['expect_score_min']}")
        if "expect_score_max" in case and out["score"] > case["expect_score_max"]:
            msgs.append(f"score {out['score']} > {case['expect_score_max']}")
        if "expect_tier" in case and out["tier"] != case["expect_tier"]:
            msgs.append(f"tier {out['tier']} != {case['expect_tier']}")
        if "expect_tier_in" in case and out["tier"] not in case["expect_tier_in"]:
            msgs.append(f"tier {out['tier']} not in {case['expect_tier_in']}")
        if "expect_denominator_min" in case and out["denominator_weight"] < case["expect_denominator_min"]:
            msgs.append(f"denom {out['denominator_weight']} < {case['expect_denominator_min']}")
        ok = not msgs
        if not ok:
            fails += 1
        status = "PASS" if ok else "FAIL"
        used = [c["name"] for c in out["components"] if c["used"]]
        print(f"[{status}] {case['label']}: score={out['score']} tier={out['tier']} "
              f"denom={out['denominator_weight']} used={len(used)} {('; '.join(msgs)) if msgs else ''}")
    print(json.dumps({"sanity_passed": fails == 0, "failures": fails}))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    import sys
    if "--sanity" in sys.argv:
        sys.exit(_sanity())
    print("This is a pure-function module. Use --sanity to self-test.")
