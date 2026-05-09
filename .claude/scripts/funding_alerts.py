#!/usr/bin/env python3
"""Alert when funding rate is extreme (potential squeeze setup)."""
import sys
import argparse
import json
import urllib.request
from pathlib import Path


def fetch_funding_binance(symbol: str) -> dict:
    """Get current funding from Binance perp."""
    url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT,DOGEUSDT,LDOUSDT,DYDXUSDT",
                   help="Comma-separated symbols")
    p.add_argument("--threshold", type=float, default=0.05,
                   help="Funding %% per 8h (0.05 = 0.05%%)")
    p.add_argument("--once", action="store_true")
    p.add_argument("--notify", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",")]
    alerts = []

    for sym in symbols:
        data = fetch_funding_binance(sym)
        if data.get("error"):
            continue
        funding_pct = float(data.get("lastFundingRate", 0)) * 100
        mark = float(data.get("markPrice", 0))

        is_extreme = abs(funding_pct) >= args.threshold
        record = {
            "symbol": sym,
            "funding_pct": round(funding_pct, 4),
            "mark": mark,
            "extreme": is_extreme,
            "implication": (
                "SHORT_SQUEEZE_SETUP" if funding_pct <= -args.threshold else
                "LONG_SQUEEZE_SETUP" if funding_pct >= args.threshold else
                "neutral"
            ),
        }
        if is_extreme:
            alerts.append(record)

    if args.json:
        print(json.dumps({"threshold": args.threshold, "alerts": alerts}, indent=2))
    else:
        if not alerts:
            print(f"No funding extremes (threshold +/-{args.threshold}%)")
        else:
            print(f"{len(alerts)} funding extreme(s):")
            for a in alerts:
                direction = "down" if a["funding_pct"] < 0 else "up"
                print(f"  [{direction}] {a['symbol']}: {a['funding_pct']:+.4f}% per 8h -> {a['implication']}")

    if args.notify and alerts:
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from notify_hub import macos_notify
            macos_notify(
                title="Funding extreme",
                body=f"{len(alerts)} symbol(s) with funding >= +/-{args.threshold}%",
            )
        except Exception:
            pass


if __name__ == "__main__":
    main()
