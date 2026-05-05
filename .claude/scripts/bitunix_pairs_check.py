#!/usr/bin/env python3
"""bitunix_pairs_check.py — validate which symbols are listed on Bitunix Perpetuals.

Hits the public ticker endpoint (no auth) and reports listing status + 24h volume
for a set of candidate symbols. Useful before adding new tokens to the watchlist.

Examples:
    python3 .claude/scripts/bitunix_pairs_check.py --tier 0
    python3 .claude/scripts/bitunix_pairs_check.py --symbols DASH,BIO,AI

Exit codes:
    0  — endpoint reachable, table printed
    2  — endpoint unreachable / response malformed
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

CR_OFFSET = timezone(timedelta(hours=-6))
ENDPOINT = "https://fapi.bitunix.com/api/v1/futures/market/tickers"
TIMEOUT = 10

# TIER 0 mugre-signals (punkchainer's TIER 0 monitoring list, captured 2026-05-05)
TIER_0_MUGRE = [
    "DASH", "BIO", "AI", "PENDLE", "RAVE", "BSB",
    "B3", "BASED", "OPG", "BROCCOLI", "BANANA", "POWR",
]

# Volume thresholds for "operable" classification (24h quote volume in USD)
VOL_HEALTHY = 1_000_000     # >$1M/24h — confidence the perp is liquid enough
VOL_THIN = 100_000          # $100k–$1M — operable but slippage risk
# below VOL_THIN → essentially un-tradeable for our sizing


def fetch_tickers() -> dict[str, dict]:
    req = urllib.request.Request(ENDPOINT, headers={"User-Agent": "wally-trader/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            payload = json.load(resp)
    except urllib.error.URLError as e:
        sys.stderr.write(f"❌ network error reaching {ENDPOINT}: {e}\n")
        sys.exit(2)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"❌ malformed JSON from {ENDPOINT}: {e}\n")
        sys.exit(2)

    if not isinstance(payload, dict) or "data" not in payload:
        sys.stderr.write(f"❌ unexpected response shape: {list(payload)[:5]}\n")
        sys.exit(2)

    return {it["symbol"]: it for it in payload["data"] if "symbol" in it}


def classify(quote_vol: float) -> str:
    if quote_vol >= VOL_HEALTHY:
        return "✅ HEALTHY"
    if quote_vol >= VOL_THIN:
        return "⚠️  THIN"
    if quote_vol > 0:
        return "❌ DEAD"
    return "❌ ZERO_VOL"


def render_table(rows: list[dict], title: str) -> None:
    print(f"\n## {title}\n")
    print(f"_Checked {datetime.now(CR_OFFSET).strftime('%Y-%m-%d %H:%M CR')} via `{ENDPOINT}`_\n")
    print("| # | Symbol | Listed | Vol 24h (quote) | Last | Status | TV Symbol |")
    print("|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        sym = r["symbol"]
        listed = "YES" if r["listed"] else "NO"
        vol = f"${r['quote_vol']:,.0f}" if r["listed"] else "—"
        last = r["last"] if r["listed"] else "—"
        status = r["status"] if r["listed"] else "❌ NOT LISTED"
        tv = f"`Bitunix:{sym}USDT.P`" if r["listed"] else "—"
        print(f"| {i} | {sym} | {listed} | {vol} | {last} | {status} | {tv} |")
    print()


def render_watchlist_block(rows: list[dict]) -> None:
    operable = [r for r in rows if r["listed"] and r["quote_vol"] >= VOL_THIN]
    print(f"\n### Lista para pegar en `MUGRE_WATCHLIST` ({len(operable)}/{len(rows)} pasan VOL_THIN)\n")
    print("```python")
    print("MUGRE_WATCHLIST = [")
    for r in operable:
        sym = r["symbol"]
        vol_m = r["quote_vol"] / 1_000_000
        flag = "HEALTHY" if r["quote_vol"] >= VOL_HEALTHY else "THIN"
        print(f'    ("{sym}USDT.P", "Bitunix:{sym}USDT.P", True),  # {flag} ${vol_m:.2f}M/24h')
    print("]")
    print("```")
    skipped = [r for r in rows if not r["listed"] or r["quote_vol"] < VOL_THIN]
    if skipped:
        print(f"\n_Excluidos del watchlist por low/zero volume:_ {', '.join(r['symbol'] for r in skipped)}")
    print()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--tier", type=int, choices=[0], help="Use built-in TIER 0 mugre list")
    g.add_argument("--symbols", help="Comma-separated symbols (e.g. DASH,BIO,AI)")
    p.add_argument("--json", action="store_true", help="Output JSON instead of markdown table")
    args = p.parse_args()

    if args.tier == 0:
        candidates = TIER_0_MUGRE
        title = f"TIER 0 MUGRE — {len(candidates)} candidates"
    else:
        candidates = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        title = f"Custom check — {len(candidates)} candidates"

    tickers = fetch_tickers()
    rows = []
    for cand in candidates:
        # Bitunix uses {SYMBOL}USDT (no .P suffix in API, but TV uses .P)
        api_sym = f"{cand}USDT"
        if api_sym in tickers:
            t = tickers[api_sym]
            try:
                quote_vol = float(t.get("quoteVol", 0) or 0)
            except (TypeError, ValueError):
                quote_vol = 0.0
            rows.append({
                "symbol": cand,
                "listed": True,
                "quote_vol": quote_vol,
                "last": t.get("lastPrice", "—"),
                "status": classify(quote_vol),
            })
        else:
            rows.append({
                "symbol": cand,
                "listed": False,
                "quote_vol": 0.0,
                "last": "—",
                "status": "NOT LISTED",
            })

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    render_table(rows, title)
    render_watchlist_block(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
