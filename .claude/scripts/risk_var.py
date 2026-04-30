#!/usr/bin/env python3
"""
risk_var.py — VaR/CVaR-based position sizing.

Calcula Value-at-Risk histórico (95% / 99%) y Conditional VaR sobre los retornos
recientes del asset, y propone un position size que limita la pérdida del peor
5% (VaR 95%) a un porcentaje configurable del capital.

VaR 95% = umbral tal que en el 95% de los días la pérdida es menor; en el 5%
peor de los días será mayor o igual a este nivel.
CVaR 95% = pérdida promedio condicional al estar en ese 5% peor (más conservador).

Más adaptativo que el "2% flat" — cuando el ATR explota, el VaR se ensancha y
el sizing recomendado se reduce automáticamente.

Usage:
    python3 risk_var.py --bars-file /tmp/bars1h.json --capital 18.09 \\
        --leverage 10 --target-var-pct 1.5 --confidence 95

    # Alternativa con bars JSON inline:
    python3 risk_var.py --closes "75500,75200,75800,..." --capital 18.09

Output JSON o tabla. Standalone, sin dependencias extra (solo stdlib).
"""
import argparse
import json
import math
import statistics
import sys
from pathlib import Path


def parse_closes(args):
    """Extract closes list from --bars-file (JSON OHLCV) or --closes CSV."""
    if args.closes:
        return [float(x.strip()) for x in args.closes.split(",") if x.strip()]
    if args.bars_file:
        path = Path(args.bars_file)
        data = json.loads(path.read_text())
        # Soporta varios shapes:
        #   {"bars":[{"close":X}, ...]}
        #   [{"close":X}, ...]
        #   {"summary":{...},"bars":[...]}
        if isinstance(data, dict) and "bars" in data:
            data = data["bars"]
        elif isinstance(data, dict) and "ohlcv" in data:
            data = data["ohlcv"]
        if not isinstance(data, list):
            raise ValueError(f"Unexpected bars shape in {path}")
        closes = []
        for bar in data:
            if isinstance(bar, dict):
                c = bar.get("close") or bar.get("c") or bar.get("Close")
                if c is None:
                    continue
                closes.append(float(c))
            elif isinstance(bar, (list, tuple)) and len(bar) >= 5:
                closes.append(float(bar[4]))  # OHLCV order, index 4 = close
        return closes
    raise SystemExit("ERROR: pasa --bars-file o --closes")


def returns_from_closes(closes):
    out = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        if prev <= 0:
            continue
        out.append((closes[i] - prev) / prev)
    return out


def historical_var(returns, confidence_pct):
    """Returns (VaR, CVaR) as negative decimals. confidence_pct in (0,100)."""
    if not returns:
        return 0.0, 0.0
    sorted_ret = sorted(returns)
    q = 1.0 - confidence_pct / 100.0  # e.g. 95% conf → q=0.05
    idx = max(0, int(math.floor(q * len(sorted_ret))))
    var = sorted_ret[idx]
    tail = sorted_ret[: idx + 1]
    cvar = sum(tail) / len(tail) if tail else var
    return var, cvar


def main():
    p = argparse.ArgumentParser(description="VaR/CVaR-based position sizing")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--bars-file", help="JSON OHLCV (TV MCP format or list)")
    src.add_argument("--closes", help="CSV de closes: 75500,75200,...")
    p.add_argument("--capital", type=float, required=True, help="Capital actual USD")
    p.add_argument("--leverage", type=float, default=1.0, help="Leverage (1=spot)")
    p.add_argument("--confidence", type=float, default=95.0, help="VaR confidence % (90/95/99)")
    p.add_argument("--target-var-pct", type=float, default=1.5,
                   help="Max VaR loss as %% of capital (default 1.5%%)")
    p.add_argument("--json", action="store_true", help="Output JSON")
    p.add_argument("--quick", action="store_true", help="Solo recomendación de size")
    args = p.parse_args()

    closes = parse_closes(args)
    if len(closes) < 30:
        print(f"⚠️  Sample size {len(closes)} < 30, VaR poco confiable. Usar más bars.",
              file=sys.stderr)

    rets = returns_from_closes(closes)
    if len(rets) < 20:
        raise SystemExit("ERROR: necesito al menos 20 retornos para VaR estable")

    var, cvar = historical_var(rets, args.confidence)
    var_99, cvar_99 = historical_var(rets, 99.0)

    mean_r = statistics.mean(rets)
    std_r = statistics.stdev(rets) if len(rets) > 1 else 0

    # Sizing: limitar VaR loss a target_var_pct% del capital
    target_loss_usd = args.capital * (args.target_var_pct / 100.0)
    var_pct_abs = abs(var)  # decimal, e.g. 0.0078

    if var_pct_abs <= 0:
        raise SystemExit("ERROR: VaR no negativo (returns all positive?), revisa data")

    # Notional that produces VaR loss = target_loss_usd
    # loss = notional * var_pct_abs (en el VaR percentile worst-case sin leverage)
    # con leverage: position size USD = notional, margin used = notional/leverage
    notional_max = target_loss_usd / var_pct_abs
    margin_used = notional_max / args.leverage if args.leverage > 0 else notional_max
    margin_pct_capital = (margin_used / args.capital * 100) if args.capital > 0 else 0

    # Comparación con flat-2%: cuánto sería la size con regla flat
    flat_2pct_usd = args.capital * 0.02
    last_close = closes[-1] if closes else 0
    flat_qty = flat_2pct_usd / abs(var) if var != 0 else 0  # qty under flat assumption
    var_qty = notional_max / last_close if last_close > 0 else 0

    result = {
        "sample_size": len(rets),
        "lookback_bars": len(closes),
        "last_close": last_close,
        "stats": {
            "mean_return": round(mean_r * 100, 4),
            "stdev_return": round(std_r * 100, 4),
        },
        "var": {
            f"var_{int(args.confidence)}_pct": round(var * 100, 4),
            f"cvar_{int(args.confidence)}_pct": round(cvar * 100, 4),
            "var_99_pct": round(var_99 * 100, 4),
            "cvar_99_pct": round(cvar_99 * 100, 4),
        },
        "sizing": {
            "capital_usd": args.capital,
            "leverage": args.leverage,
            "target_var_pct": args.target_var_pct,
            "target_loss_usd": round(target_loss_usd, 2),
            "max_notional_usd": round(notional_max, 2),
            "margin_used_usd": round(margin_used, 2),
            "margin_pct_of_capital": round(margin_pct_capital, 2),
            "qty_units": round(var_qty, 6),
        },
        "comparison_flat_2pct": {
            "flat_target_loss_usd": round(flat_2pct_usd, 2),
            "delta_vs_var": "MORE_CONSERVATIVE" if target_loss_usd < flat_2pct_usd else "LESS_CONSERVATIVE",
        }
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return

    if args.quick:
        print(f"VaR{int(args.confidence)}: {result['var'][f'var_{int(args.confidence)}_pct']}%  "
              f"→ Notional max: ${result['sizing']['max_notional_usd']}  "
              f"(margin ${result['sizing']['margin_used_usd']} = "
              f"{result['sizing']['margin_pct_of_capital']}% capital)")
        return

    # Tabla
    c = args.confidence
    print(f"╔════════════════════════════════════════════════════════════╗")
    print(f"║  VaR/CVaR Position Sizing — Last {len(rets)} returns                ║")
    print(f"╚════════════════════════════════════════════════════════════╝")
    print(f"")
    print(f"Stats:")
    print(f"  Mean return    : {mean_r*100:+.4f}%")
    print(f"  StdDev         : {std_r*100:.4f}%")
    print(f"")
    print(f"Risk metrics:")
    print(f"  VaR  {int(c)}%       : {var*100:+.4f}%   (en {int(100-c)}% peor casos, perderás >= esto)")
    print(f"  CVaR {int(c)}%       : {cvar*100:+.4f}%   (avg loss en cola — más conservador)")
    print(f"  VaR  99%       : {var_99*100:+.4f}%")
    print(f"  CVaR 99%       : {cvar_99*100:+.4f}%")
    print(f"")
    print(f"Sizing recommendation (limit VaR loss to {args.target_var_pct}% of capital):")
    print(f"  Capital              : ${args.capital:.2f}")
    print(f"  Target loss (95%)    : ${target_loss_usd:.2f}")
    print(f"  Leverage             : {args.leverage}x")
    print(f"  Max notional         : ${notional_max:.2f}")
    print(f"  Margin used          : ${margin_used:.2f}  ({margin_pct_capital:.1f}% capital)")
    if last_close > 0:
        print(f"  Qty @ ${last_close:,.2f}  : {var_qty:.6f} units")
    print(f"")
    print(f"Comparison vs flat-2% rule:")
    delta = "MÁS CONSERVADOR" if target_loss_usd < flat_2pct_usd else "MENOS CONSERVADOR"
    print(f"  Flat 2% target loss  : ${flat_2pct_usd:.2f}")
    print(f"  VaR {int(args.target_var_pct*100/100)}% target loss : ${target_loss_usd:.2f}  → {delta}")


if __name__ == "__main__":
    main()
