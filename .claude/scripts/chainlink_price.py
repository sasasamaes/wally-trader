#!/usr/bin/env python3
"""Cross-platform port of chainlink_price.sh.

Usage:
  python chainlink_price.py <PAIR> [--compare <tv_price>] [--json]

PAIR: BTC | ETH | LINK | EUR | GBP | XAU

Cache 30s en /tmp (Linux/macOS) o %TEMP% (Windows) para evitar hammear RPCs.
Fallback automático entre 4 RPCs públicos sin auth.
"""
import argparse
import json
import os
import sys
import tempfile
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Tuple

# Chainlink Data Feeds — Ethereum mainnet, AggregatorV3 contracts
FEEDS = {
    "BTC":  ("0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c", 8),
    "ETH":  ("0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419", 8),
    "LINK": ("0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c", 8),
    "EUR":  ("0xb49f677943BC038e9857d61E7d053CaA2C1734C1", 8),
    "GBP":  ("0x5c0Ab2d9b5a7ed9f470386e82BB36A3613cDd4b5", 8),
    "XAU":  ("0x214eD9Da11D2fbe465a6fc601a91E62EbEc1a0D6", 8),
}

RPCS = [
    "https://1rpc.io/eth",
    "https://eth.llamarpc.com",
    "https://eth-mainnet.public.blastapi.io",
    "https://ethereum.publicnode.com",
]

CACHE_TTL_SECONDS = 30


def get_cache_path(pair: str) -> Path:
    """Cross-platform temp cache: /tmp on Unix, %TEMP% on Windows."""
    return Path(tempfile.gettempdir()) / f"wally_chainlink_{pair.upper()}.cache"


def fetch_price(addr: str, decimals: int) -> Optional[float]:
    """Try each RPC in sequence until one succeeds. Returns price or None."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": addr, "data": "0x50d25bcd"}, "latest"],  # latestAnswer()
        "id": 1,
    }).encode()

    for rpc in RPCS:
        try:
            req = urllib.request.Request(
                rpc, data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            hex_result = data.get("result", "")
            if not hex_result or hex_result == "0x0":
                continue
            price = int(hex_result, 16) / (10 ** decimals)
            if price <= 0:
                continue
            return round(price, 4)
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError, TimeoutError):
            continue
    return None


def get_price(pair: str) -> Tuple[float, bool]:
    """Returns (price, from_cache_stale). Raises SystemExit on total failure."""
    pair = pair.upper()
    if pair not in FEEDS:
        print(f"ERROR: par no soportado: {pair} (BTC|ETH|LINK|EUR|GBP|XAU)", file=sys.stderr)
        sys.exit(2)
    addr, decimals = FEEDS[pair]
    cache = get_cache_path(pair)

    # Cache hit (fresh)
    if cache.exists():
        age = time.time() - cache.stat().st_mtime
        if age < CACHE_TTL_SECONDS:
            return float(cache.read_text().strip()), False

    # Fetch fresh
    price = fetch_price(addr, decimals)
    if price is not None:
        cache.write_text(f"{price:.4f}")
        return price, False

    # Fallback to stale cache
    if cache.exists():
        print("chainlink: usando cache stale (todos los RPCs fallaron)", file=sys.stderr)
        return float(cache.read_text().strip()), True

    print(f"ERROR: no se pudo obtener precio Chainlink para {pair}", file=sys.stderr)
    sys.exit(1)


def compare_verdict(delta_pct: float) -> str:
    abs_delta = abs(delta_pct)
    if abs_delta >= 1.0:
        return "ALERT"
    elif abs_delta >= 0.3:
        return "WARN"
    else:
        return "OK"


def main():
    parser = argparse.ArgumentParser(description="Chainlink price feed reader (cross-platform)")
    parser.add_argument("pair", help="BTC | ETH | LINK | EUR | GBP | XAU")
    parser.add_argument("--compare", type=float, help="TV price for delta comparison")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    price, stale = get_price(args.pair)

    # Simple mode: just price
    if args.compare is None and not args.json:
        print(f"{price:.4f}")
        return 0

    # Compare or JSON mode
    delta_pct = None
    verdict = None
    if args.compare is not None:
        delta_pct = (price - args.compare) / args.compare * 100
        verdict = compare_verdict(delta_pct)

    if args.json:
        out = {"pair": args.pair.upper(), "chainlink": price}
        if args.compare is not None:
            out["tv"] = args.compare
            out["delta_pct"] = round(delta_pct, 4)
            out["verdict"] = verdict
        if stale:
            out["cache_stale"] = True
        print(json.dumps(out))
    else:
        # compare mode, table output
        if args.compare is not None:
            print(f"{'Pair':<8} {'Chainlink':>14} {'TradingView':>14} {'Delta %':>10} {'Verdict':>8}")
            print(f"{args.pair.upper():<8} {price:>14.4f} {args.compare:>14.4f} {delta_pct:>10.4f} {verdict:>8}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
