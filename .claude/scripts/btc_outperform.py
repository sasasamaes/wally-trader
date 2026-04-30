#!/usr/bin/env python3
"""
btc_outperform.py — calcula outperformance vs HODL para profile quantfury.

Lee equity_curve.csv (con columna equity_btc) y compara performance trading
vs simplemente mantener el BTC.

Outperformance % = (your_btc_return) - (hodl_btc_return)
                 = (final_btc_stack / initial_btc_stack - 1) × 100

NOTA: HODL benchmark en BTC denomination = 0% por definición (los sats no
cambian si no operas). Outperformance = tu BTC return absoluto.

Si quieres comparación en USD:
  USD outperformance = your_usd_return - btc_spot_return_usd

Usage:
  python3 btc_outperform.py --equity-csv .claude/profiles/quantfury/memory/equity_curve.csv
  python3 btc_outperform.py --equity-csv <path> --period 30d
  python3 btc_outperform.py --equity-csv <path> --json
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def parse_period(s):
    """Parse '30d', '7d', '4w' to timedelta."""
    s = s.lower().strip()
    if s.endswith('d'):
        return timedelta(days=int(s[:-1]))
    if s.endswith('w'):
        return timedelta(weeks=int(s[:-1]))
    if s.endswith('h'):
        return timedelta(hours=int(s[:-1]))
    raise ValueError(f"Unknown period format: {s}")


def parse_iso(s):
    """Parse ISO timestamp tolerant to format variations."""
    s = s.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M",
                "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse timestamp: {s}")


def load_equity(csv_path):
    """Returns list of (datetime, equity_btc, equity_usd, btc_usd_price) tuples."""
    rows = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            ts_str = r.get("timestamp", "").strip()
            if not ts_str:
                continue
            try:
                ts = parse_iso(ts_str)
            except ValueError:
                continue
            try:
                eq_btc = float(r.get("equity_btc", "0") or 0)
                eq_usd = float(r.get("equity_usd", "0") or 0)
                btc_usd = float(r.get("btc_usd_price", "0") or 0)
            except ValueError:
                continue
            rows.append((ts, eq_btc, eq_usd, btc_usd))
    return sorted(rows)


def main():
    p = argparse.ArgumentParser(description="BTC outperformance vs HODL benchmark")
    p.add_argument("--equity-csv", required=True, help="Path to quantfury equity_curve.csv")
    p.add_argument("--period", default="all",
                   help="Lookback period (e.g. 7d, 30d, 4w, 'all')")
    p.add_argument("--json", action="store_true", help="JSON output")
    args = p.parse_args()

    csv_path = Path(args.equity_csv)
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found", file=sys.stderr)
        sys.exit(1)

    rows = load_equity(csv_path)
    if len(rows) < 2:
        result = {
            "status": "INSUFFICIENT_DATA",
            "message": f"Need 2+ rows in equity_curve.csv, found {len(rows)}",
            "rows_found": len(rows),
        }
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"⚠️  {result['message']}")
        sys.exit(0 if len(rows) > 0 else 2)

    # Filter by period
    if args.period != "all":
        try:
            delta = parse_period(args.period)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(2)
        cutoff = rows[-1][0] - delta
        rows = [r for r in rows if r[0] >= cutoff]
        if len(rows) < 2:
            print(f"⚠️  Solo {len(rows)} rows en período {args.period}, "
                  f"necesito 2+", file=sys.stderr)
            sys.exit(0)

    first = rows[0]
    last = rows[-1]
    ts_first, btc_first, usd_first, price_first = first
    ts_last, btc_last, usd_last, price_last = last

    btc_return_pct = (btc_last / btc_first - 1) * 100 if btc_first > 0 else 0
    usd_return_pct = (usd_last / usd_first - 1) * 100 if usd_first > 0 else 0
    btc_spot_change_pct = (price_last / price_first - 1) * 100 if price_first > 0 else 0

    # HODL benchmark in BTC denomination = 0% (no change in stack)
    # In USD: HODL value would change with spot price
    hodl_btc_return = 0.0
    hodl_usd_return = btc_spot_change_pct

    # Outperformance:
    outperform_btc = btc_return_pct - hodl_btc_return  # essentially btc_return_pct
    outperform_usd = usd_return_pct - hodl_usd_return  # vs spot

    # Verdict según rules.md
    if outperform_btc >= 5:
        verdict = "EXCELENTE"
        recommendation = "Continuar normal — sistema agrega valor real"
    elif outperform_btc >= 0:
        verdict = "OK"
        recommendation = "Edge ligero, sigue iterando, evaluar a 60d"
    elif outperform_btc >= -2:
        verdict = "WARNING"
        recommendation = "Modo conservador (risk 1%), revisa filtros"
    else:
        verdict = "PAUSE_PROFILE"
        recommendation = "PAUSAR PROFILE 30 días, pasar a HODL, review fundamental"

    result = {
        "period": args.period,
        "rows_used": len(rows),
        "ts_first": ts_first.isoformat(),
        "ts_last": ts_last.isoformat(),
        "btc_initial": btc_first,
        "btc_final": btc_last,
        "btc_return_pct": round(btc_return_pct, 4),
        "usd_initial": usd_first,
        "usd_final": usd_last,
        "usd_return_pct": round(usd_return_pct, 4),
        "btc_spot_start": price_first,
        "btc_spot_end": price_last,
        "btc_spot_change_pct": round(btc_spot_change_pct, 4),
        "hodl_btc_return": hodl_btc_return,
        "hodl_usd_return": round(hodl_usd_return, 4),
        "outperformance_btc_pct": round(outperform_btc, 4),
        "outperformance_usd_pct": round(outperform_usd, 4),
        "verdict": verdict,
        "recommendation": recommendation,
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"╔══════════════════════════════════════════════════════════════════╗")
    print(f"║  BTC Outperformance vs HODL — período {args.period:<28}║")
    print(f"╚══════════════════════════════════════════════════════════════════╝")
    print(f"")
    print(f"Período:")
    print(f"  Desde   : {ts_first.isoformat()}")
    print(f"  Hasta   : {ts_last.isoformat()}")
    print(f"  Rows    : {len(rows)}")
    print(f"")
    print(f"Tu cuenta:")
    print(f"  BTC inicio  : ₿{btc_first:.8f}")
    print(f"  BTC final   : ₿{btc_last:.8f}")
    print(f"  BTC return  : {btc_return_pct:+.4f}%")
    print(f"  USD inicio  : ${usd_first:,.2f}")
    print(f"  USD final   : ${usd_last:,.2f}")
    print(f"  USD return  : {usd_return_pct:+.4f}%")
    print(f"")
    print(f"Spot BTC en mismo período:")
    print(f"  ${price_first:,.2f} → ${price_last:,.2f}  ({btc_spot_change_pct:+.4f}%)")
    print(f"")
    print(f"HODL benchmark:")
    print(f"  BTC return (sin tradear) : {hodl_btc_return:+.4f}%  (siempre 0% por definición)")
    print(f"  USD return HODL          : {hodl_usd_return:+.4f}%")
    print(f"")
    print(f"OUTPERFORMANCE:")
    print(f"  vs HODL en BTC : {outperform_btc:+.4f}%   ← métrica clave")
    print(f"  vs HODL en USD : {outperform_usd:+.4f}%")
    print(f"")
    print(f"Veredicto: {verdict}")
    print(f"Recomendación: {recommendation}")


if __name__ == "__main__":
    main()
