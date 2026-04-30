#!/usr/bin/env python3
"""
journal_metrics.py — Sharpe, Sortino, Max DD, Profit Factor, IC desde trading_log.md.

Parsea el log markdown del profile activo (formato tabla) y calcula:
  - Win Rate
  - Avg win / Avg loss
  - Profit Factor (sum_wins / sum_losses)
  - Expectancy
  - Sharpe ratio anualizado (asume 252 trading days)
  - Sortino ratio (downside deviation only)
  - Max Drawdown (peak-to-trough en equity curve)
  - Information Coefficient (correlación Pearson entre ML score y PnL realizado, si log tiene columna ml_score)

Usage:
    python3 journal_metrics.py --log .claude/profiles/retail/memory/trading_log.md
    python3 journal_metrics.py --log <path> --since 2026-04-01
    python3 journal_metrics.py --log <path> --json

Soporta logs en formato:
    | Date | Asset | Dir | Entry | Exit | PnL$ | PnL% | ML | Notes |
    |---|---|---|---|---|---|---|---|---|
    | 2026-04-29 | BTCUSDT.P | LONG | 75000 | 76000 | +5.20 | +1.33 | 72 | TP1 |

Tolerante: si faltan columnas (ML, %), las omite.
"""
import argparse
import json
import math
import re
import statistics
import sys
from pathlib import Path


def parse_markdown_table(text):
    """Extract table rows as list of dicts. Reads the FIRST table with headers."""
    lines = text.splitlines()
    rows = []
    headers = None
    in_table = False
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells:
            continue
        # Separator row (---|---|---) → marks end of header
        if all(re.match(r"^:?-+:?$", c) for c in cells if c):
            in_table = True
            continue
        if not in_table:
            # Header row
            headers = [h.lower() for h in cells]
            continue
        if headers and len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def parse_pnl(value):
    """Extract numeric PnL from cell. Strips $, +, %, spaces."""
    if not value:
        return None
    cleaned = value.replace("$", "").replace("%", "").replace("+", "").replace(",", "").strip()
    if cleaned in ("-", "N/A", "n/a", ""):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def find_col(row, candidates):
    """Return first column value matching one of `candidates` (case-insensitive)."""
    for c in candidates:
        c = c.lower()
        for k in row.keys():
            if c in k:
                return row[k]
    return None


def max_drawdown(equity_curve):
    """Peak-to-trough max DD %."""
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd * 100  # %


def sharpe(returns, periods_per_year=252):
    if len(returns) < 2:
        return 0.0
    mu = statistics.mean(returns)
    sigma = statistics.stdev(returns)
    if sigma == 0:
        return 0.0
    return (mu / sigma) * math.sqrt(periods_per_year)


def sortino(returns, periods_per_year=252):
    """Like Sharpe but only penalizes downside volatility."""
    if len(returns) < 2:
        return 0.0
    mu = statistics.mean(returns)
    downside = [r for r in returns if r < 0]
    if len(downside) < 2:
        return float("inf") if mu > 0 else 0.0
    dd_std = statistics.pstdev(downside)
    if dd_std == 0:
        return 0.0
    return (mu / dd_std) * math.sqrt(periods_per_year)


def pearson_corr(xs, ys):
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(len(xs)))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def main():
    p = argparse.ArgumentParser(description="Trading metrics from journal log")
    p.add_argument("--log", required=True, help="Path to trading_log.md")
    p.add_argument("--since", help="ISO date (e.g. 2026-04-01) — filtra trades >= esta fecha")
    p.add_argument("--initial-capital", type=float, default=None,
                   help="Para calcular equity curve. Default: lee del primer trade.")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    text = Path(args.log).read_text()
    rows = parse_markdown_table(text)
    if not rows:
        raise SystemExit(f"ERROR: no encontré tabla parseable en {args.log}")

    # Filter
    if args.since:
        rows = [r for r in rows if (find_col(r, ["date", "fecha"]) or "") >= args.since]

    # Extract PnL per trade
    trades = []
    for r in rows:
        pnl_str = find_col(r, ["pnl $", "pnl$", "pnl_usd", "pnl"])
        pnl = parse_pnl(pnl_str)
        if pnl is None:
            continue
        ml_str = find_col(r, ["ml ", "ml_", "score"])
        ml = parse_pnl(ml_str)
        date = find_col(r, ["date", "fecha"]) or ""
        trades.append({"date": date, "pnl_usd": pnl, "ml_score": ml})

    if not trades:
        raise SystemExit("ERROR: no parseé trades con PnL del log")

    pnls = [t["pnl_usd"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    n = len(pnls)
    n_w = len(wins)
    n_l = len(losses)

    wr = (n_w / n) * 100 if n else 0
    avg_win = sum(wins) / n_w if n_w else 0
    avg_loss = sum(losses) / n_l if n_l else 0  # negativo
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("inf") if wins else 0
    expectancy = (wr / 100) * avg_win + ((1 - wr / 100) * avg_loss)

    # Equity curve
    init_cap = args.initial_capital or 10.0
    equity = [init_cap]
    for p_v in pnls:
        equity.append(equity[-1] + p_v)
    max_dd = max_drawdown(equity)
    final_eq = equity[-1]
    total_return_pct = ((final_eq - init_cap) / init_cap * 100) if init_cap > 0 else 0

    # Returns per trade (%) for Sharpe/Sortino
    rets_pct = []
    for i in range(1, len(equity)):
        if equity[i-1] > 0:
            rets_pct.append((equity[i] - equity[i-1]) / equity[i-1])
    sh = sharpe(rets_pct) if rets_pct else 0
    so = sortino(rets_pct) if rets_pct else 0

    # Information Coefficient: correlación entre ML score y PnL realizado
    paired = [(t["ml_score"], t["pnl_usd"]) for t in trades if t["ml_score"] is not None]
    ic = None
    if len(paired) >= 3:
        ic = pearson_corr([p[0] for p in paired], [p[1] for p in paired])

    result = {
        "trades_total": n,
        "wins": n_w,
        "losses": n_l,
        "win_rate_pct": round(wr, 2),
        "avg_win_usd": round(avg_win, 2),
        "avg_loss_usd": round(avg_loss, 2),
        "profit_factor": round(pf, 3) if pf != float("inf") else "inf",
        "expectancy_usd": round(expectancy, 4),
        "initial_capital": init_cap,
        "final_equity": round(final_eq, 2),
        "total_return_pct": round(total_return_pct, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe_annualized": round(sh, 3) if sh != float("inf") else "inf",
        "sortino_annualized": round(so, 3) if so != float("inf") else "inf",
        "information_coefficient": round(ic, 3) if ic is not None else None,
        "ic_sample_size": len(paired),
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"╔══════════════════════════════════════════════════════════════════╗")
    print(f"║  Trading Metrics — {n} trades                                       ║")
    print(f"╚══════════════════════════════════════════════════════════════════╝")
    print(f"")
    print(f"P&L:")
    print(f"  Wins / Losses    : {n_w} / {n_l}")
    print(f"  Win Rate         : {wr:.2f}%")
    print(f"  Avg Win / Loss   : ${avg_win:+.2f} / ${avg_loss:+.2f}")
    print(f"  Profit Factor    : {pf if pf != float('inf') else '∞':.3f}" if isinstance(pf, float) else f"  Profit Factor    : {pf}")
    print(f"  Expectancy/trade : ${expectancy:+.4f}")
    print(f"")
    print(f"Equity:")
    print(f"  Capital Inicial  : ${init_cap:.2f}")
    print(f"  Capital Final    : ${final_eq:.2f}")
    print(f"  Total Return     : {total_return_pct:+.2f}%")
    print(f"  Max Drawdown     : {max_dd:.2f}%")
    print(f"")
    print(f"Risk-adjusted:")
    print(f"  Sharpe (annual)  : {sh:.3f}    (>1.0 OK, >2.0 bueno, >3.0 excelente)")
    print(f"  Sortino (annual) : {so:.3f}    (mejor que Sharpe en estrategias asimétricas)")
    if ic is not None:
        ic_label = "BAJO" if abs(ic) < 0.1 else ("MEDIO" if abs(ic) < 0.3 else "FUERTE")
        print(f"  IC (ML vs PnL)   : {ic:.3f}    [{ic_label}, n={len(paired)}]")
    else:
        print(f"  IC (ML vs PnL)   : N/A (no hay columna ML score o sample <3)")
    print(f"")
    print(f"Interpretación rápida:")
    if sh < 1.0:
        print(f"  ⚠️  Sharpe <1: estrategia con riesgo desproporcionado. Revisa SL distance/sizing.")
    if max_dd > 20:
        print(f"  ⚠️  Max DD >20%: drawdown grande. Considera reducir size o agregar filtros.")
    if isinstance(pf, float) and pf < 1.5:
        print(f"  ⚠️  Profit Factor <1.5: edge marginal. Esperar más samples antes de scaling.")


if __name__ == "__main__":
    main()
