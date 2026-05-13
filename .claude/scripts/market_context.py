#!/usr/bin/env python3
"""market_context.py — Multi-source market discovery + per-asset context.

Sources (todos public, sin auth):
- Binance Futures: top volume / top movers / 24h ticker / funding rate
- CoinGecko: trending coins / global dominance (USDT.D, BTC.D)
- alternative.me: Fear & Greed Index
- Bitunix Futures: tradeable pairs + 24h volume (filter)

Cache:
- Discovery (top lists): 1h TTL — alineado con la cadencia de /punk-smart
- Global context (F&G, dominance): 10 min TTL
- Per-asset context: 5 min TTL

Graceful degradation: si una API falla, el campo correspondiente queda en None
en vez de tirar excepción. El consumidor decide qué hacer con None.

CLI:
    python3 market_context.py --discover volume --top 10 --tradeable bitunix
    python3 market_context.py --global-context
    python3 market_context.py --asset-context BTCUSDT
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

CR_OFFSET = timezone(timedelta(hours=-6))
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

DISCOVERY_TTL_SEC = 3600   # 1h — matches /punk-smart hourly cadence
GLOBAL_TTL_SEC = 600       # 10 min
ASSET_TTL_SEC = 300        # 5 min

UA = "wally-trader/1.0"
TIMEOUT = 8

BINANCE_FUTURES_24HR = "https://fapi.binance.com/fapi/v1/ticker/24hr"
BINANCE_FUTURES_FUNDING = "https://fapi.binance.com/fapi/v1/premiumIndex"
COINGECKO_GLOBAL = "https://api.coingecko.com/api/v3/global"
COINGECKO_TRENDING = "https://api.coingecko.com/api/v3/search/trending"
FNG_URL = "https://api.alternative.me/fng/?limit=1"
BITUNIX_TICKERS = "https://fapi.bitunix.com/api/v1/futures/market/tickers"


# ─── Generic cache helpers ────────────────────────────────────────────────────

def _cache_path(name: str) -> Path:
    return CACHE_DIR / f"market_{name}.json"


def _read_cache(name: str, ttl: int) -> dict | None:
    p = _cache_path(name)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        if time.time() - data.get("ts", 0) > ttl:
            return None
        return data["payload"]
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def _write_cache(name: str, payload: dict | list) -> None:
    p = _cache_path(name)
    try:
        p.write_text(json.dumps({"ts": time.time(), "payload": payload}))
    except OSError:
        pass  # cache write is best-effort


def _http_json(url: str, timeout: int = TIMEOUT) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


# ─── Discovery: top tradeable lists ───────────────────────────────────────────

def _binance_24hr_all() -> list[dict] | None:
    """All Binance Futures 24hr tickers — single call, ~150 pairs."""
    cached = _read_cache("binance_24hr_all", ASSET_TTL_SEC)
    if cached is not None:
        return cached
    try:
        data = _http_json(BINANCE_FUTURES_24HR)
        if not isinstance(data, list):
            return None
        _write_cache("binance_24hr_all", data)
        return data
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def fetch_top_volume_binance(n: int = 10) -> list[dict] | None:
    """Top N Binance Futures pairs by 24h quote volume USDT-denominated only."""
    tickers = _binance_24hr_all()
    if tickers is None:
        return None
    usdt = [
        {
            "symbol": t["symbol"],
            "vol_24h_usd": float(t["quoteVolume"]),
            "change_24h_pct": float(t["priceChangePercent"]),
            "last_price": float(t["lastPrice"]),
        }
        for t in tickers
        if t.get("symbol", "").endswith("USDT")
    ]
    usdt.sort(key=lambda x: -x["vol_24h_usd"])
    return usdt[:n]


def fetch_top_movers_binance(n: int = 10, min_volume_usd: float = 50_000_000) -> list[dict] | None:
    """Top N Binance Futures pairs by absolute 24h % change.

    Filtered by min_volume_usd to exclude pump-and-dump on illiquid pairs.
    """
    tickers = _binance_24hr_all()
    if tickers is None:
        return None
    candidates = [
        {
            "symbol": t["symbol"],
            "vol_24h_usd": float(t["quoteVolume"]),
            "change_24h_pct": float(t["priceChangePercent"]),
            "last_price": float(t["lastPrice"]),
        }
        for t in tickers
        if t.get("symbol", "").endswith("USDT")
    ]
    liquid = [c for c in candidates if c["vol_24h_usd"] >= min_volume_usd]
    liquid.sort(key=lambda x: -abs(x["change_24h_pct"]))
    return liquid[:n]


def fetch_trending_coingecko(n: int = 10) -> list[dict] | None:
    """CoinGecko trending coins (search-based momentum)."""
    cached = _read_cache("coingecko_trending", DISCOVERY_TTL_SEC)
    if cached is not None:
        return cached[:n]
    try:
        data = _http_json(COINGECKO_TRENDING)
        coins = data.get("coins", []) if isinstance(data, dict) else []
        result = [
            {
                "symbol": c["item"]["symbol"].upper() + "USDT",
                "name": c["item"]["name"],
                "rank_market_cap": c["item"].get("market_cap_rank"),
                "score_trending": c["item"].get("score"),
            }
            for c in coins[:n]
            if "item" in c and "symbol" in c["item"]
        ]
        _write_cache("coingecko_trending", result)
        return result
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        return None


# ─── Bitunix tradeable filter ─────────────────────────────────────────────────

def _bitunix_tickers() -> dict | None:
    cached = _read_cache("bitunix_tickers", ASSET_TTL_SEC)
    if cached is not None:
        return cached
    try:
        data = _http_json(BITUNIX_TICKERS)
        if not isinstance(data, dict) or "data" not in data:
            return None
        # Bitunix returns symbol without USDT suffix (e.g. "BTC", "ETH")
        result = {it["symbol"]: it for it in data["data"] if "symbol" in it}
        _write_cache("bitunix_tickers", result)
        return result
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def filter_tradeable_bitunix(symbols: list[str], min_vol_usd: float = 1_000_000) -> list[dict]:
    """Intersect a list of Binance-style USDT symbols with Bitunix listings.

    Returns list of {symbol, bitunix_vol_24h_usd, listed} sorted by bitunix vol desc.
    Symbols not listed in Bitunix are dropped (with a `listed: False` if min_vol_usd=0
    is requested via show_unlisted=True flag — keeping API simple for now).
    """
    bx = _bitunix_tickers()
    if bx is None:
        # Bitunix down → return empty (caller sees no tradeable result, fail-safe)
        return []
    out: list[dict] = []
    for sym in symbols:
        # Bitunix uses BTCUSDT (with suffix), same as Binance
        if sym not in bx:
            continue
        ticker = bx[sym]
        vol_field = ticker.get("quoteVol") or ticker.get("quote_vol") or 0
        try:
            vol = float(vol_field)
        except (TypeError, ValueError):
            vol = 0.0
        if vol < min_vol_usd:
            continue
        out.append({
            "symbol": sym,
            "bitunix_vol_24h_usd": round(vol, 2),
            "bitunix_last_price": float(ticker.get("last", 0) or 0),
        })
    out.sort(key=lambda x: -x["bitunix_vol_24h_usd"])
    return out


# ─── Global context ───────────────────────────────────────────────────────────

def _fetch_fng() -> int | None:
    try:
        data = _http_json(FNG_URL, timeout=5)
        return int(data["data"][0]["value"])
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError, IndexError):
        return None


def _fetch_dominance() -> dict | None:
    try:
        data = _http_json(COINGECKO_GLOBAL, timeout=10)
        dom = data["data"]["market_cap_percentage"]
        return {
            "btc_dominance": round(dom.get("btc", 0.0), 3),
            "usdt_dominance": round(dom.get("usdt", 0.0), 3),
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        return None


def fetch_global_context() -> dict:
    """One-shot global context. Cached 10 min. Always returns a dict (None values on failure)."""
    cached = _read_cache("global_context", GLOBAL_TTL_SEC)
    if cached is not None:
        return cached
    payload = {
        "fng": _fetch_fng(),
        "dominance": _fetch_dominance(),
        "fetched_at": datetime.now(CR_OFFSET).isoformat(),
    }
    _write_cache("global_context", payload)
    return payload


# ─── Per-asset context ────────────────────────────────────────────────────────

def _binance_funding(symbol: str) -> float | None:
    """Funding rate as decimal (e.g. 0.0001 = 0.01% per 8h)."""
    try:
        data = _http_json(f"{BINANCE_FUTURES_FUNDING}?symbol={symbol}", timeout=5)
        return float(data["lastFundingRate"])
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError):
        return None


def _binance_24hr_one(symbol: str) -> dict | None:
    """24h ticker for a single symbol (uses cached all-tickers if available)."""
    all_tickers = _binance_24hr_all()
    if all_tickers is None:
        return None
    for t in all_tickers:
        if t.get("symbol") == symbol:
            try:
                return {
                    "vol_24h_usd": float(t["quoteVolume"]),
                    "change_24h_pct": float(t["priceChangePercent"]),
                    "high_24h": float(t["highPrice"]),
                    "low_24h": float(t["lowPrice"]),
                    "last_price": float(t["lastPrice"]),
                }
            except (KeyError, ValueError):
                return None
    return None


def fetch_asset_context(symbol: str) -> dict:
    """Per-asset context: Binance 24h ticker + funding rate. Always returns a dict."""
    ticker = _binance_24hr_one(symbol)
    funding = _binance_funding(symbol)
    return {
        "symbol": symbol,
        "binance_24h": ticker,
        "funding_rate_8h": funding,
        "funding_pct_8h": round(funding * 100, 4) if funding is not None else None,
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _print_table(rows: list[dict], title: str) -> None:
    if not rows:
        print(f"\n{title}\n  (no data — source unreachable or filter excluded all)")
        return
    print(f"\n{title}")
    keys = list(rows[0].keys())
    widths = {k: max(len(k), max(len(str(r.get(k, ""))) for r in rows)) for k in keys}
    header = "  " + "  ".join(k.ljust(widths[k]) for k in keys)
    sep = "  " + "  ".join("-" * widths[k] for k in keys)
    print(header)
    print(sep)
    for r in rows:
        print("  " + "  ".join(str(r.get(k, "")).ljust(widths[k]) for k in keys))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--discover", choices=["volume", "movers", "trending"],
                   help="Pull a top-N tradeable list from a source")
    p.add_argument("--top", type=int, default=10, help="N for --discover (default 10)")
    p.add_argument("--tradeable", choices=["bitunix"], default=None,
                   help="Filter discovery output by exchange tradeability")
    p.add_argument("--min-vol", type=float, default=1_000_000,
                   help="Min Bitunix 24h volume USD for tradeable filter (default $1M)")
    p.add_argument("--global-context", action="store_true",
                   help="Print global context (F&G + BTC.D + USDT.D)")
    p.add_argument("--asset-context", help="Print asset-specific context for SYMBOL")
    p.add_argument("--json", action="store_true", help="Output as JSON")
    args = p.parse_args()

    out: dict = {}

    if args.discover:
        if args.discover == "volume":
            raw = fetch_top_volume_binance(n=args.top)
        elif args.discover == "movers":
            raw = fetch_top_movers_binance(n=args.top)
        else:  # trending
            raw = fetch_trending_coingecko(n=args.top)
        if raw is None:
            print(f"❌ Discovery source '{args.discover}' unreachable", file=sys.stderr)
            return 2
        if args.tradeable == "bitunix":
            symbols = [r["symbol"] for r in raw]
            tradeable = filter_tradeable_bitunix(symbols, min_vol_usd=args.min_vol)
            # Merge: enrich tradeable rows with discovery metadata
            disc_by_sym = {r["symbol"]: r for r in raw}
            for t in tradeable:
                disc = disc_by_sym.get(t["symbol"], {})
                t.update({k: v for k, v in disc.items() if k != "symbol"})
            out["discovery"] = tradeable
            out["discovery_source"] = args.discover
            out["filtered_by"] = "bitunix"
            out["original_count"] = len(raw)
            out["tradeable_count"] = len(tradeable)
        else:
            out["discovery"] = raw
            out["discovery_source"] = args.discover

    if args.global_context:
        out["global_context"] = fetch_global_context()

    if args.asset_context:
        out["asset_context"] = fetch_asset_context(args.asset_context)

    if not out:
        p.print_help()
        return 1

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        if "discovery" in out:
            _print_table(
                out["discovery"],
                f"Discovery [{out['discovery_source']}]"
                + (f" → tradeable on {out['filtered_by']}: {out['tradeable_count']}/{out['original_count']}"
                   if "filtered_by" in out else ""),
            )
        if "global_context" in out:
            g = out["global_context"]
            print(f"\nGlobal context  (fetched {g['fetched_at']})")
            print(f"  F&G index:        {g['fng']}/100" if g['fng'] is not None else "  F&G index:        unavailable")
            if g['dominance']:
                print(f"  BTC dominance:    {g['dominance']['btc_dominance']}%")
                print(f"  USDT dominance:   {g['dominance']['usdt_dominance']}%")
            else:
                print("  Dominance:        unavailable (CoinGecko down)")
        if "asset_context" in out:
            a = out["asset_context"]
            print(f"\nAsset context  [{a['symbol']}]")
            if a["binance_24h"]:
                bn = a["binance_24h"]
                print(f"  Binance 24h vol:  ${bn['vol_24h_usd']:,.0f}")
                print(f"  24h change:       {bn['change_24h_pct']:+.2f}%")
                print(f"  Range:            ${bn['low_24h']:,.4f} → ${bn['high_24h']:,.4f}")
            if a["funding_pct_8h"] is not None:
                print(f"  Funding 8h:       {a['funding_pct_8h']:+.4f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
