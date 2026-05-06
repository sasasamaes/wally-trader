#!/usr/bin/env python3
"""backtest_oos_split — 70/30 train/test split for /punk-smart v2 mapping.

Steps:
1. Fetch 60d per asset (paginated)
2. Walk through all bars; for each bar in train portion, build mapping winners
3. For each bar in test portion, apply the train mapping and simulate
4. Aggregate metrics for train and test, output JSON for backtest_split.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from backtest_regime_matrix import (
    fetch_paginated, classify_regime, simulate,
    strat_a_vwap, strat_b_trending_pullback,
    strat_c_bb_squeeze_break, strat_d_momentum_macd, strat_e_range_bounce,
    DAYS, MARGIN, LEVERAGE, FEES_PCT, ASSETS,
)

STRATS = {
    "A_VWAP": strat_a_vwap,
    "B_TrendPullback": strat_b_trending_pullback,
    "C_BBSqueeze": strat_c_bb_squeeze_break,
    "D_MACDMomentum": strat_d_momentum_macd,
    "E_RangeBounce": strat_e_range_bounce,
}
REGIMES = ["STRONG_TREND_UP", "STRONG_TREND_DOWN", "WEAK_TREND_UP",
           "WEAK_TREND_DOWN", "RANGING", "SQUEEZE", "VOLATILE",
           "UNKNOWN", "MIXED"]

NOTIONAL = MARGIN * LEVERAGE


def collect_trades(b15, b1h, start_idx, end_idx):
    """Collect trades for all (regime, strategy) cells over bar range [start, end)."""
    cells = {r: {s: [] for s in STRATS} for r in REGIMES}
    last_trade_idx = {s: -100 for s in STRATS}
    for i in range(max(start_idx, 70), min(end_idx, len(b15) - 24)):
        cr_h = (datetime.utcfromtimestamp(b15[i]["t"] / 1000).hour - 6) % 24
        if cr_h < 6 or cr_h > 22:
            continue
        regime = classify_regime(b15, b1h, i)
        for sname, sfn in STRATS.items():
            if i - last_trade_idx[sname] < 16:
                continue
            setup = sfn(b15, b1h, i)
            if setup is None:
                continue
            result = simulate(setup, b15[i + 1:])
            if result is None:
                continue
            cells[regime][sname].append({**setup, **result})
            last_trade_idx[sname] = i
    return cells


def build_mapping(cells):
    """For each regime, pick strategy with highest sum-PnL (min 5 trades)."""
    mapping = {}
    for regime in REGIMES:
        best, best_pnl = None, -9999
        for sname in STRATS:
            ts = cells[regime][sname]
            if len(ts) < 5:
                continue
            pnl = sum(t["pnl_usd"] for t in ts)
            if pnl > best_pnl:
                best_pnl, best = pnl, sname
        if best:
            mapping[regime] = best
    return mapping


def calc_max_dd(trades):
    """Compute max drawdown % of cumulative PnL curve (relative to peak)."""
    if not trades:
        return 0.0
    equity = MARGIN
    peak = equity
    max_dd = 0.0
    for t in trades:
        equity += t["pnl_usd"]
        peak = max(peak, equity)
        dd = (peak - equity) / peak * 100
        max_dd = max(max_dd, dd)
    return round(max_dd, 2)


def aggregate(cells, mapping):
    """Aggregate metrics for trades that follow the mapping."""
    trades_followed = []
    for regime, strat in mapping.items():
        if regime in cells and strat in cells[regime]:
            trades_followed.extend(cells[regime][strat])

    n = len(trades_followed)
    if n == 0:
        return {"wr": 0.0, "n": 0, "pnl": 0.0, "pf": 0.0, "ret_pct": 0.0, "ret": 0.0, "dd": 0.0}

    wins = [t for t in trades_followed if t["pnl_usd"] > 0]
    losses = [t for t in trades_followed if t["pnl_usd"] < 0]
    wr = len(wins) / n * 100
    pnl = sum(t["pnl_usd"] for t in trades_followed)
    gross_win = sum(t["pnl_usd"] for t in wins)
    gross_loss = abs(sum(t["pnl_usd"] for t in losses))
    pf = (gross_win / gross_loss) if gross_loss > 0 else 99.99
    ret_pct = pnl / MARGIN * 100  # % of $100 starting margin
    dd = calc_max_dd(trades_followed)
    return {
        "wr": round(wr, 1),
        "n": n,
        "pnl": round(pnl, 2),
        "pf": round(pf, 2),
        "ret_pct": round(ret_pct, 1),
        "ret": round(ret_pct, 1),   # alias expected by backtest_split.py
        "dd": dd,
    }


def main():
    print(f"OOS split: {len(ASSETS)} assets × {DAYS} days, 70/30 train/test", file=sys.stderr)
    train_cells_all = {r: {s: [] for s in STRATS} for r in REGIMES}
    test_cells_all = {r: {s: [] for s in STRATS} for r in REGIMES}

    for sym in ASSETS:
        print(f"  fetching {sym}...", file=sys.stderr)
        b15 = fetch_paginated(sym, "15m", days=DAYS)
        b1h = fetch_paginated(sym, "1h", days=DAYS + 3)
        if not b15 or not b1h:
            print(f"    skip (no data)", file=sys.stderr)
            continue

        n_bars = len(b15)
        split_idx = int(n_bars * 0.7)
        print(f"    total bars: {n_bars}, split at idx {split_idx} "
              f"(train: {split_idx}, test: {n_bars - split_idx})", file=sys.stderr)

        train_cells = collect_trades(b15, b1h, 70, split_idx)
        test_cells = collect_trades(b15, b1h, split_idx, n_bars - 24)

        for r in REGIMES:
            for s in STRATS:
                train_cells_all[r][s].extend(train_cells[r][s])
                test_cells_all[r][s].extend(test_cells[r][s])

        # Progress: show trade counts per slice
        train_total = sum(len(train_cells[r][s]) for r in REGIMES for s in STRATS)
        test_total = sum(len(test_cells[r][s]) for r in REGIMES for s in STRATS)
        print(f"    trades → train: {train_total}, test: {test_total}", file=sys.stderr)

    mapping = build_mapping(train_cells_all)
    print(f"\nTrain mapping ({len(mapping)} regimes): {mapping}", file=sys.stderr)

    train_metrics = aggregate(train_cells_all, mapping)
    test_metrics = aggregate(test_cells_all, mapping)

    print(f"\nTrain metrics: {train_metrics}", file=sys.stderr)
    print(f"Test  metrics: {test_metrics}", file=sys.stderr)

    print(json.dumps({"train": train_metrics, "test": test_metrics}, indent=2))


if __name__ == "__main__":
    main()
