"""
backtest_ftmo.py — Historical backtest of FTMO-Conservative strategy.

Usage:
    python backtest_ftmo.py --asset BTCUSDT --start 2026-01-22 --end 2026-04-22

Data source: uses TradingView MCP if available, else yfinance for FX.
Output: JSON summary + CSV of simulated trades.

Pass criteria (for Go to paper trading):
- WR >= 55%
- Max DD <= 5% of initial capital ($500 in $10k)
- 0 daily breaches (3% rule simulated)
- best_day_ratio <= 0.50 across backtest period
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import guardian


INITIAL_CAPITAL = 10000
RISK_PCT = 0.5
SL_PCT = 0.004
TP1_PCT = 0.006
TP2_PCT = 0.012


def load_ohlcv(asset, start, end):
    """Stub: load OHLCV data. Implementation depends on data source.

    Returns: list of dicts with keys: ts, open, high, low, close, volume
    """
    # Placeholder: in real implementation, read from CSV or call yfinance/TV
    raise NotImplementedError("Implement data loader in actual run")


def simulate_strategy(asset, ohlcv):
    """Walk forward bar-by-bar, apply FTMO-Conservative 7 filters, simulate trades."""
    trades = []
    equity = INITIAL_CAPITAL
    equity_curve = [{"timestamp": ohlcv[0]["ts"], "equity": equity, "source": "init", "note": ""}]

    for i in range(20, len(ohlcv)):  # start after warmup
        # ... compute Donchian(20), RSI(14), BB(20,2), session filter
        # ... check 7 filters
        # ... if LONG or SHORT signal triggered:
        #       simulate fill at close of current bar
        #       compute SL, TP1, TP2
        #       walk forward until one of them hits
        #       close trade, update equity, append to trades + equity_curve
        pass

    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "final_equity": equity,
    }


def compute_metrics(result):
    trades = result["trades"]
    curve = result["equity_curve"]
    if not trades:
        return {"trades": 0, "wr": 0, "avg_r": 0, "max_dd": 0, "best_day_ratio": 0, "daily_breaches": 0}

    wins = sum(1 for t in trades if t["result"] in ("TP1", "TP2"))
    wr = wins / len(trades) * 100

    # Max DD
    peak = INITIAL_CAPITAL
    max_dd = 0
    for r in curve:
        peak = max(peak, r["equity"])
        dd = peak - r["equity"]
        max_dd = max(max_dd, dd)

    # Daily breaches
    breaches = 0
    # Group by date, check if daily delta ever <= -3% of initial
    by_date = {}
    for r in curve:
        d = r["timestamp"].date() if hasattr(r["timestamp"], "date") else r["timestamp"]
        by_date.setdefault(d, []).append(r)
    for d, rows in by_date.items():
        if len(rows) >= 2:
            delta = rows[-1]["equity"] - rows[0]["equity"]
            if delta <= -INITIAL_CAPITAL * 0.03:
                breaches += 1

    # Best day ratio
    best, total = guardian.best_day_ratio(curve)
    ratio = (best / total) if total > 0 else 0

    avg_r = sum(t.get("r", 0) for t in trades) / len(trades)

    return {
        "trades": len(trades),
        "wr": round(wr, 2),
        "avg_r": round(avg_r, 2),
        "max_dd": round(max_dd, 2),
        "max_dd_pct": round(max_dd / INITIAL_CAPITAL * 100, 2),
        "best_day_ratio": round(ratio, 3),
        "daily_breaches": breaches,
        "final_equity": result["final_equity"],
        "return_pct": round((result["final_equity"] - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100, 2),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--data-csv", help="Pre-downloaded OHLCV CSV instead of API")
    args = parser.parse_args()

    ohlcv = load_ohlcv(args.asset, args.start, args.end)  # will raise if not implemented
    result = simulate_strategy(args.asset, ohlcv)
    metrics = compute_metrics(result)

    # Write trades CSV
    out_path = Path(__file__).parent / f"backtest_{args.asset}_{args.start}_{args.end}.csv"
    with open(out_path, "w", newline="") as f:
        if result["trades"]:
            w = csv.DictWriter(f, fieldnames=result["trades"][0].keys())
            w.writeheader()
            w.writerows(result["trades"])

    # Print metrics JSON
    print(json.dumps(metrics, indent=2))

    # Pass/fail summary
    pass_criteria = (
        metrics["wr"] >= 55 and
        metrics["max_dd_pct"] <= 5 and
        metrics["daily_breaches"] == 0 and
        metrics["best_day_ratio"] <= 0.50
    )
    print(f"\nBACKTEST VERDICT: {'PASS — OK para paper trading' if pass_criteria else 'FAIL — refinar estrategia'}")
    sys.exit(0 if pass_criteria else 1)


if __name__ == "__main__":
    main()
