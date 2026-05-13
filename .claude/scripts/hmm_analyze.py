#!/usr/bin/env python3
"""HMM Diagnostic Tool — main entry point.

Usage:
    hmm_analyze.py --symbol ETHUSDT --strategy A_VWAP [--html] [--suggest-mapping]
                   [--force-refresh] [--seed 42]

See docs/superpowers/specs/2026-05-13-hmm-diagnostic-tool-design.md
"""
import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))

# Strategies live in backtest_regime_matrix.py — import the registry
try:
    from backtest_regime_matrix import (
        strat_a_vwap, strat_b_trending_pullback,
        strat_c_bb_squeeze_break, strat_d_momentum_macd, strat_e_range_bounce,
    )
except ImportError as exc:
    print(f"ERROR: cannot import strategies from backtest_regime_matrix.py: {exc}",
          file=sys.stderr)
    sys.exit(7)

from hmm_lib import (
    fetcher, features as features_mod, model as model_mod,
    labeling, backtest as backtest_mod, reporting, suggest,
)
from hmm_lib.errors import (
    FetchError, InsufficientDataError, HMMFitError, StrategyExecError,
)

STRATEGY_REGISTRY = {
    "A_VWAP": strat_a_vwap,
    "B_TrendPullback": strat_b_trending_pullback,
    "C_BBSqueeze": strat_c_bb_squeeze_break,
    "D_MACDMomentum": strat_d_momentum_macd,
    "E_RangeBounce": strat_e_range_bounce,
}

CACHE_DIR = PROJECT_ROOT / ".claude" / "cache"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "hmm_analysis"


def _setup_logging() -> None:
    log_path = CACHE_DIR / "hmm_analyze.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )


def _df_to_15m_bars(df_1h) -> list[dict]:
    """Strategies want 15m granularity; for V1 we synthesize 15m bars from 1h
    by duplicating each 1h bar into 4 identical 15m bars. This is a known
    approximation — V2 should pull true 15m series."""
    out = []
    for _, row in df_1h.iterrows():
        ts_base = int(row["ts_utc"].timestamp())
        for sub in range(4):
            out.append({
                "t": ts_base + sub * 900,
                "o": row["open"],
                "h": row["high"],
                "l": row["low"],
                "c": row["close"],
                "v": row["volume"] / 4,
            })
    return out


def _df_to_1h_bars(df_1h) -> list[dict]:
    return [{
        "t": int(row["ts_utc"].timestamp()),
        "o": row["open"], "h": row["high"], "l": row["low"],
        "c": row["close"], "v": row["volume"],
    } for _, row in df_1h.iterrows()]


def _build_report(symbol: str, strategy: str, df, fit, labels, backtests,
                  mapping_note: str | None) -> dict:
    caveats = [
        "**V1 approximation:** 15m bars are synthesized by duplicating each 1H bar 4 times. "
        "Strategies that key off intrabar high/low or volume may see degraded signal quality. "
        "V2 should fetch true 15m series alongside 1H.",
    ]
    for sid, info in labels.items():
        if info.get("low_sample"):
            caveats.append(
                f"State {sid} ({info['label']}) covers only {info['pct_bars'] * 100:.1f}% of bars — "
                "labeling may be unreliable.")
    for r in backtests:
        if r.low_trade_count and r.regime_label != "GLOBAL":
            caveats.append(
                f"Regime {r.regime_label} has only {r.trades} trades — backtest metrics noisy.")
    if all(info.get("label", "").startswith("CHOP") for info in labels.values()):
        caveats.append("All detected regimes are CHOP-like; HMM provides little differentiation. "
                       "Consider a higher timeframe or a different asset.")

    return {
        "symbol": symbol,
        "strategy": strategy,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "n_bars": len(df),
        "best_k": fit.k,
        "bic": fit.bic,
        "log_likelihood": fit.log_likelihood,
        "labels": labels,
        "transition_matrix": fit.transition_matrix,
        "backtests": backtests,
        "current_mapping_note": mapping_note,
        "caveats": caveats,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hmm_analyze.py")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", required=True,
                        choices=sorted(STRATEGY_REGISTRY.keys()))
    parser.add_argument("--html", action="store_true")
    parser.add_argument("--suggest-mapping", action="store_true")
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    _setup_logging()
    log = logging.getLogger("hmm_analyze")
    symbol = args.symbol.upper()
    log.info("start symbol=%s strategy=%s", symbol, args.strategy)

    try:
        df = fetcher.fetch_ohlcv_1h_6m(symbol, force_refresh=args.force_refresh)
    except FetchError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2 if "not listed" in str(exc) else 3
    except InsufficientDataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4

    feat_matrix = features_mod.build_features(df)
    log.info("features shape=%s", feat_matrix.shape)

    try:
        fit = model_mod.fit_best_hmm(feat_matrix, random_state=args.seed)
    except HMMFitError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 5

    labels = labeling.label_states(fit, feat_matrix)
    log.info("k=%d labels=%s", fit.k, {sid: info["label"] for sid, info in labels.items()})

    # Map HMM states (defined on features=bars after WARMUP) back to original 1h timeline.
    # WARMUP bars are dropped from features. Mark them with sentinel -1 so backtest skips
    # any trades whose entry falls in the warmup window (avoids fake state attribution).
    from hmm_lib.features import WARMUP as FEATURE_WARMUP
    import numpy as np
    states_1h = np.concatenate([
        np.full(FEATURE_WARMUP, -1, dtype=np.int64),  # sentinel: skip warmup trades
        fit.states.astype(np.int64),
    ])
    # Trim to match df length
    states_1h = states_1h[:len(df)]
    warmup_count = int((states_1h == -1).sum())
    log.info("warmup bars (trades will be skipped): %d", warmup_count)

    bars_1h = _df_to_1h_bars(df)
    bars_15m = _df_to_15m_bars(df)
    # Each 15m bar inherits state from its parent 1h bar (4 sub-bars share state).
    # The backtest module looks up regime by entry_ts via bisect on bars_1h timestamps.

    strategy_fn = STRATEGY_REGISTRY[args.strategy]
    try:
        backtests = backtest_mod.backtest_per_regime(
            bars_15m, bars_1h, states_1h, labels,
            strategy_fn=strategy_fn, strategy_name=args.strategy,
        )
    except StrategyExecError as exc:
        print(f"ERROR: strategy crashed at bar {exc.bar_index}: {exc}", file=sys.stderr)
        return 6

    # Suggest mapping (optional)
    mapping_note: str | None = None
    if args.suggest_mapping:
        mapping_path = PROJECT_ROOT / ".claude" / "scripts" / "regime_mapping.json"
        mapping_note = suggest.suggest_mapping_patch(backtests, mapping_path, symbol, args.strategy)

    report = _build_report(symbol, args.strategy, df, fit, labels, backtests, mapping_note)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = report["date"]
    md_path = OUTPUT_DIR / f"{symbol}_{args.strategy}_{date_str}.md"
    reporting.emit_markdown(report, md_path)
    print(f"Wrote {md_path}")

    if args.html:
        html_path = OUTPUT_DIR / f"{symbol}_{args.strategy}_{date_str}.html"
        try:
            reporting.emit_html(report, html_path)
            print(f"Wrote {html_path}")
        except ImportError as exc:
            print(f"WARNING: {exc}", file=sys.stderr)

    if mapping_note:
        print()
        print(mapping_note)

    log.info("done exit=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
