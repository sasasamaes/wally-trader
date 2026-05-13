"""Per-regime backtest harness.

Strategies use the existing contract from backtest_regime_matrix.py:
    fn(bars_15m: list[dict], bars_1h: list[dict], i: int) -> Optional[Signal]

Where Signal is {side, entry, sl, tp1, tp2}. Exit logic: TP1 first hit OR SL first hit
over the next MAX_HOLD bars. We do NOT model TP2 partial fills in V1 — full position
exits at first TP1 or SL touch.
"""
import bisect
from dataclasses import dataclass

import numpy as np

from hmm_lib.errors import StrategyExecError

MAX_HOLD_BARS = 24      # 24 × 15m = 6h max hold
LOW_TRADE_THRESHOLD = 10


@dataclass
class RegimeBacktest:
    regime_label: str
    n_bars: int
    pct_time: float
    trades: int
    wr: float
    pf: float
    net_pnl_pct: float
    max_dd_pct: float
    low_trade_count: bool


def _resolve_trade(bars_15m: list[dict], signal: dict, entry_idx: int) -> tuple[float, str]:
    """Return (pnl_pct, exit_reason) by simulating TP1/SL hit over next MAX_HOLD_BARS."""
    side = signal["side"]
    entry = signal["entry"]
    sl = signal["sl"]
    tp1 = signal["tp1"]

    last_idx = min(entry_idx + MAX_HOLD_BARS, len(bars_15m) - 1)
    for j in range(entry_idx + 1, last_idx + 1):
        bar = bars_15m[j]
        if side == "LONG":
            if bar["l"] <= sl:
                return ((sl - entry) / entry, "SL")
            if bar["h"] >= tp1:
                return ((tp1 - entry) / entry, "TP1")
        else:  # SHORT
            if bar["h"] >= sl:
                return ((entry - sl) / entry, "SL")
            if bar["l"] <= tp1:
                return ((entry - tp1) / entry, "TP1")
    # Timeout: exit at last close
    close = bars_15m[last_idx]["c"]
    pnl = ((close - entry) / entry) if side == "LONG" else ((entry - close) / entry)
    return (pnl, "TIMEOUT")


def _regime_at_entry(entry_ts: int, bars_1h: list[dict], states_1h: np.ndarray) -> int | None:
    """Find the 1h bar covering the entry timestamp; return state or None if out of range."""
    timestamps = [b["t"] for b in bars_1h]
    idx = bisect.bisect_right(timestamps, entry_ts) - 1
    if idx < 0 or idx >= len(states_1h):
        return None
    return int(states_1h[idx])


def _aggregate_trades(trades: list[tuple[float, str]]) -> tuple[int, float, float, float, float]:
    """Compute (n, wr, pf, net_pnl_pct, max_dd_pct) from a list of (pnl, reason) tuples."""
    if not trades:
        return (0, 0.0, 0.0, 0.0, 0.0)
    pnls = np.array([t[0] for t in trades])
    n = len(pnls)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    wr = (len(wins) / n) * 100.0
    pf = (wins.sum() / -losses.sum()) if len(losses) > 0 else float("inf")
    net = float(pnls.sum() * 100.0)
    equity = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity)
    drawdowns = peak - equity
    max_dd = float(drawdowns.max() * 100.0) if len(drawdowns) > 0 else 0.0
    return (n, wr, pf if pf != float("inf") else 999.99, net, max_dd)


def backtest_per_regime(
    bars_15m: list[dict],
    bars_1h: list[dict],
    states_1h: np.ndarray,
    labels: dict[int, dict],
    *,
    strategy_fn,
    strategy_name: str,
) -> list[RegimeBacktest]:
    """Run strategy across all 15m bars, partition trades by entry-bar regime (1h state).
    Always emits GLOBAL row + one row per state label present in `labels`.
    """
    all_trades: list[tuple[float, str, int]] = []      # (pnl, reason, regime_state)
    n_15m = len(bars_15m)

    for i in range(n_15m):
        try:
            signal = strategy_fn(bars_15m, bars_1h, i)
        except Exception as exc:
            raise StrategyExecError(
                f"strategy {strategy_name} crashed at bar {i}: {exc}",
                bar_index=i, symbol="?", strategy=strategy_name,
            )
        if signal is None:
            continue
        entry_ts = bars_15m[i]["t"]
        regime = _regime_at_entry(entry_ts, bars_1h, states_1h)
        if regime is None:
            continue
        pnl, reason = _resolve_trade(bars_15m, signal, i)
        all_trades.append((pnl, reason, regime))

    rows: list[RegimeBacktest] = []
    n_total_1h = len(bars_1h)

    # GLOBAL row
    n, wr, pf, net, mdd = _aggregate_trades([(t[0], t[1]) for t in all_trades])
    rows.append(RegimeBacktest(
        regime_label="GLOBAL",
        n_bars=n_total_1h,
        pct_time=1.0,
        trades=n, wr=wr, pf=pf, net_pnl_pct=net, max_dd_pct=mdd,
        low_trade_count=False,
    ))

    # Per-regime rows
    for sid, info in labels.items():
        regime_trades = [(t[0], t[1]) for t in all_trades if t[2] == sid]
        n_bars_regime = int((states_1h == sid).sum())
        pct = n_bars_regime / n_total_1h if n_total_1h > 0 else 0.0
        n, wr, pf, net, mdd = _aggregate_trades(regime_trades)
        rows.append(RegimeBacktest(
            regime_label=info.get("label", f"STATE_{sid}"),
            n_bars=n_bars_regime,
            pct_time=pct,
            trades=n, wr=wr, pf=pf, net_pnl_pct=net, max_dd_pct=mdd,
            low_trade_count=(n < LOW_TRADE_THRESHOLD),
        ))

    return rows
