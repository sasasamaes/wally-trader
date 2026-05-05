#!/usr/bin/env python3
"""
punk_smart_router.py — Detecta regime + ejecuta estrategia ganadora del backtest.

Lee mapping de `regime_mapping.json` y para cada asset del watchlist:
1. Pull data (15m + 1h)
2. Clasifica regime
3. Si regime tiene strategy ganadora (PnL > 0 backtest) → ejecuta esa
4. Si regime es STAND_ASIDE (PnL <= 0) → no recomienda este asset
5. Devuelve top setups ordenados por R:R

Mapping ganador (auto-loaded):
- STRONG_TREND_UP   → A_VWAP         ✅
- RANGING           → A_VWAP         ✅
- MIXED             → A_VWAP         ✅
- SQUEEZE           → B_TrendPullback ✅
- WEAK_TREND_DOWN   → B_TrendPullback ✅
- STRONG_TREND_DOWN → STAND_ASIDE
- WEAK_TREND_UP     → STAND_ASIDE
- VOLATILE          → STAND_ASIDE (insuficiente data)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Reuso funciones del backtest matrix
from backtest_regime_matrix import (
    fetch, calc_atr, calc_rsi, calc_ema, calc_macd, calc_bb, calc_adx, calc_vwap,
    classify_regime, strat_a_vwap, strat_b_trending_pullback,
)

ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "MSTRUSDT", "AVAXUSDT",
          "INJUSDT", "DOGEUSDT", "WIFUSDT", "XLMUSDT"]

STRATEGY_FNS = {
    "A_VWAP": strat_a_vwap,
    "B_TrendPullback": strat_b_trending_pullback,
}

MAPPING_FILE = Path(__file__).parent / "regime_mapping.json"


def load_mapping():
    if not MAPPING_FILE.exists():
        print(f"❌ Mapping not found: {MAPPING_FILE}", file=sys.stderr)
        print(f"   Run: python3 .claude/scripts/backtest_regime_matrix.py", file=sys.stderr)
        sys.exit(1)
    return json.loads(MAPPING_FILE.read_text())


def evaluate_asset(symbol, mapping):
    """Evalúa un asset: detecta regime + ejecuta estrategia ganadora."""
    bars_15m = fetch(symbol, "15m", 100)
    bars_1h = fetch(symbol, "1h", 80)

    if len(bars_15m) < 70 or len(bars_1h) < 50:
        return {"asset": symbol, "status": "INSUFFICIENT_DATA"}

    # Clasificar regime en bar más reciente
    i = len(bars_15m) - 1
    regime = classify_regime(bars_15m, bars_1h, i)
    regime_info = mapping.get(regime)

    base = {"asset": symbol, "regime": regime, "now_price": bars_15m[-1]["c"]}

    if regime_info is None:
        return {**base, "status": "STAND_ASIDE", "reason": f"regime {regime} insuficiente backtest data"}

    if regime_info["pnl"] <= 0:
        return {
            **base,
            "status": "STAND_ASIDE",
            "reason": f"regime {regime} backtest PnL ${regime_info['pnl']:+.2f} (todas estrategias pierden)",
            "backtest_strategy_attempted": regime_info["strategy"],
        }

    strategy_name = regime_info["strategy"]
    strat_fn = STRATEGY_FNS.get(strategy_name)
    if strat_fn is None:
        return {**base, "status": "STRATEGY_UNAVAILABLE", "strategy": strategy_name}

    setup = strat_fn(bars_15m, bars_1h, i)
    if setup is None:
        return {
            **base,
            "status": "NO_SETUP",
            "strategy": strategy_name,
            "reason": f"strategy {strategy_name} no triggea en este momento",
            "backtest_wr": round(regime_info["wr"], 1),
            "backtest_pnl_per_trade": round(regime_info["pnl_per_trade"], 2),
        }

    # Calcular R:R
    rr_tp1 = abs(setup["tp1"] - setup["entry"]) / abs(setup["sl"] - setup["entry"])
    rr_tp2 = abs(setup["tp2"] - setup["entry"]) / abs(setup["sl"] - setup["entry"])

    return {
        **base,
        "status": "SETUP_FOUND",
        "strategy": strategy_name,
        "side": setup["side"],
        "entry": round(setup["entry"], 4),
        "sl": round(setup["sl"], 4),
        "tp1": round(setup["tp1"], 4),
        "tp2": round(setup["tp2"], 4),
        "rr_tp1": round(rr_tp1, 2),
        "rr_tp2": round(rr_tp2, 2),
        "sl_distance_pct": round(abs(setup["sl"] - setup["entry"]) / setup["entry"] * 100, 3),
        "tp1_distance_pct": round(abs(setup["tp1"] - setup["entry"]) / setup["entry"] * 100, 3),
        "tp2_distance_pct": round(abs(setup["tp2"] - setup["entry"]) / setup["entry"] * 100, 3),
        "backtest_wr": round(regime_info["wr"], 1),
        "backtest_pnl_per_trade": round(regime_info["pnl_per_trade"], 2),
    }


def main():
    import argparse
    p = argparse.ArgumentParser(description="Smart router — regime detection + best strategy execution")
    p.add_argument("--asset", help="Single asset (default: scan all)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--show-all", action="store_true", help="Mostrar también STAND_ASIDE / NO_SETUP")
    args = p.parse_args()

    mapping = load_mapping()
    targets = [args.asset] if args.asset else ASSETS
    results = [evaluate_asset(s, mapping) for s in targets]

    setups = [r for r in results if r.get("status") == "SETUP_FOUND"]
    no_setup = [r for r in results if r.get("status") == "NO_SETUP"]
    stand_aside = [r for r in results if r.get("status") == "STAND_ASIDE"]

    if args.json:
        print(json.dumps({
            "setups": setups,
            "no_setup": no_setup,
            "stand_aside": stand_aside,
            "mapping_used": mapping,
        }, indent=2))
        return

    print(f"\n{'='*70}")
    print(f"PUNK-SMART — Regime-aware router — {datetime.now().strftime('%H:%M CR')}")
    print(f"{'='*70}")

    if setups:
        # Sort by R:R TP2 descendente
        setups.sort(key=lambda x: -x["rr_tp2"])
        print(f"\n✅ {len(setups)} SETUP(S) ENCONTRADO(S) (best mapping):\n")
        for i, s in enumerate(setups):
            arrow = "🟢 LONG" if s["side"] == "LONG" else "🔴 SHORT"
            print(f"#{i+1} {arrow} {s['asset']} (regime: {s['regime']}, strategy: {s['strategy']})")
            print(f"   Entry: {s['entry']} | Backtest: {s['backtest_wr']}% WR / ${s['backtest_pnl_per_trade']:+.2f} per trade")
            print(f"   SL:  {s['sl']} ({s['sl_distance_pct']}%)")
            print(f"   TP1: {s['tp1']} ({s['tp1_distance_pct']}%) — R:R {s['rr_tp1']}")
            print(f"   TP2: {s['tp2']} ({s['tp2_distance_pct']}%) — R:R {s['rr_tp2']}")
            print()
    else:
        print("\n⏳ NO SETUPS válidos del mapping ahora.")

    if args.show_all:
        if no_setup:
            print(f"\n{'─'*70}\nAssets con regime tradeable pero sin setup actual ({len(no_setup)}):")
            for s in no_setup:
                print(f"  {s['asset']:14s} regime={s['regime']:18s} strategy={s.get('strategy','-'):16s} (WR backtest {s.get('backtest_wr','-')}%)")
        if stand_aside:
            print(f"\n{'─'*70}\nAssets STAND_ASIDE (regime no rentable en backtest) ({len(stand_aside)}):")
            for s in stand_aside:
                print(f"  {s['asset']:14s} regime={s['regime']:18s} reason: {s.get('reason','')}")


if __name__ == "__main__":
    main()
