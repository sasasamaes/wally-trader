#!/usr/bin/env python3
"""
risk_parity.py — Equal Risk Contribution (ERC) sizing across multi-asset.

En profile FTMO/fotmarkets el universo es multi-asset (BTC, ETH, EURUSD, GBPUSD,
NAS100, SPX500). Estos assets tienen volatilidades muy distintas — NAS100 5x
EURUSD. Si decides un trade y le pones el mismo size USD, NO estás tomando el
mismo riesgo: el NAS100 te puede mover 5x más.

Risk Parity asigna pesos inverse-vol: cada asset contribuye igual riesgo total.
Útil para:
  - Filtrar selección de A-grade (asset con vol fuera de rango → skip)
  - Comparar setups equivalentes de distintos assets
  - Limitar exposición a asset volátil cuando ATR explota

Usage:
    # Con ATRs precomputados (formato CSV)
    python3 risk_parity.py --vols "BTC:0.023,ETH:0.031,EURUSD:0.004,NAS100:0.015"

    # Con bars per asset (varios JSON)
    python3 risk_parity.py --bars-dir /tmp/bars/ --window 20

Output: tabla de weights + risk contribution + sizing recommendations.
"""
import argparse
import json
import math
import statistics
import sys
from pathlib import Path


def realized_vol(closes, window=None):
    """Daily realized vol = stdev of log returns. Anualización opcional."""
    if window:
        closes = closes[-window-1:]
    if len(closes) < 2:
        return 0.0
    rets = []
    for i in range(1, len(closes)):
        if closes[i-1] > 0:
            rets.append(math.log(closes[i] / closes[i-1]))
    if len(rets) < 2:
        return 0.0
    return statistics.stdev(rets)


def parse_vols_arg(s):
    out = {}
    for token in s.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" not in token:
            raise ValueError(f"Bad vol token: {token} (expected NAME:vol)")
        name, vol = token.split(":", 1)
        out[name.strip()] = float(vol)
    return out


def load_vols_from_dir(bars_dir, window):
    """Each *.json in bars_dir is one asset's OHLCV. Filename stem = asset name."""
    out = {}
    for path in sorted(Path(bars_dir).glob("*.json")):
        try:
            data = json.loads(path.read_text())
            if isinstance(data, dict) and "bars" in data:
                data = data["bars"]
            elif isinstance(data, dict) and "ohlcv" in data:
                data = data["ohlcv"]
            closes = []
            for bar in data:
                if isinstance(bar, dict):
                    c = bar.get("close") or bar.get("c")
                    if c is not None:
                        closes.append(float(c))
                elif isinstance(bar, (list, tuple)) and len(bar) >= 5:
                    closes.append(float(bar[4]))
            if len(closes) >= 5:
                out[path.stem] = realized_vol(closes, window)
        except Exception as e:
            print(f"⚠️  {path.name}: {e}", file=sys.stderr)
    return out


def risk_parity_weights(vols):
    """Equal Risk Contribution: weight_i ∝ 1/vol_i. Normalize sum=1."""
    inv = {k: (1.0 / v) for k, v in vols.items() if v > 0}
    s = sum(inv.values())
    if s == 0:
        raise ValueError("All vols zero or invalid")
    return {k: v / s for k, v in inv.items()}


def main():
    p = argparse.ArgumentParser(description="Risk Parity multi-asset sizing")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--vols", help="CSV: BTC:0.023,ETH:0.031,...")
    src.add_argument("--bars-dir", help="Dir con N JSONs (uno por asset)")
    p.add_argument("--window", type=int, default=20, help="Lookback bars (default 20)")
    p.add_argument("--capital", type=float, default=10000.0, help="Capital total ($)")
    p.add_argument("--target-portfolio-vol", type=float, default=None,
                   help="Volatilidad target del portafolio anualizada (e.g. 0.10 = 10%%)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.vols:
        vols = parse_vols_arg(args.vols)
    else:
        vols = load_vols_from_dir(args.bars_dir, args.window)

    if not vols:
        raise SystemExit("ERROR: no se obtuvieron vols")

    weights = risk_parity_weights(vols)

    # Risk contribution = w_i * vol_i (igual para todos = parity)
    contribs = {k: weights[k] * vols[k] for k in vols}
    total_contrib = sum(contribs.values())
    contrib_pct = {k: (v / total_contrib * 100) if total_contrib else 0 for k, v in contribs.items()}

    # Sizing en USD (notional asignado por asset)
    sizing = {k: round(weights[k] * args.capital, 2) for k in vols}

    # Optional: scale por target portfolio vol
    portfolio_vol_estimate = total_contrib  # naive (asume independencia)
    scale = 1.0
    if args.target_portfolio_vol and portfolio_vol_estimate > 0:
        scale = args.target_portfolio_vol / portfolio_vol_estimate
        sizing = {k: round(v * scale, 2) for k, v in sizing.items()}

    result = {
        "vols": {k: round(v, 6) for k, v in vols.items()},
        "weights": {k: round(v, 4) for k, v in weights.items()},
        "risk_contribution_pct": {k: round(v, 2) for k, v in contrib_pct.items()},
        "sizing_usd": sizing,
        "capital": args.capital,
        "portfolio_vol_estimate": round(portfolio_vol_estimate, 4),
        "scale_factor": round(scale, 4),
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"╔══════════════════════════════════════════════════════════════════╗")
    print(f"║  Risk Parity (Equal Risk Contribution) — N={len(vols)} assets               ║")
    print(f"╚══════════════════════════════════════════════════════════════════╝")
    print(f"")
    print(f"{'Asset':<10} {'Vol':<10} {'Weight':<10} {'Risk Contrib':<15} {'Notional ($)':<15}")
    print(f"{'-'*10} {'-'*10} {'-'*10} {'-'*15} {'-'*15}")
    for k in sorted(vols.keys()):
        v = vols[k]
        w = weights[k]
        rc = contrib_pct[k]
        s = sizing[k]
        print(f"{k:<10} {v*100:.3f}%   {w*100:.2f}%    {rc:.2f}%         ${s:,.2f}")
    print(f"")
    print(f"Capital total              : ${args.capital:,.2f}")
    print(f"Portfolio vol estimate     : {portfolio_vol_estimate*100:.3f}% (per-bar)")
    if args.target_portfolio_vol:
        print(f"Target portfolio vol       : {args.target_portfolio_vol*100:.2f}%")
        print(f"Scale factor               : {scale:.3f}")
    print(f"")
    print(f"Interpretación:")
    print(f"  - Weight inverso a vol → asset más volátil recibe MENOS notional.")
    print(f"  - Risk contribution igual para todos = parity (target del método).")
    print(f"  - Útil para filtrar A-grade: asset cuyo size RP es <30% del fixed → skip.")


if __name__ == "__main__":
    main()
