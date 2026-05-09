#!/usr/bin/env python3
"""liq_heatmap.py — Estimate liquidation cluster levels for futures perpetuals.

Inspired by "Cloud Code + TradingView" YT video where the host uses a paid
liquidation heatmap (Coinglass-style). We approximate without paid APIs by
combining:

  - Binance Futures public data (OI history, L/S retail+smart, funding)
  - Recent price swings (where stops are likely placed)
  - Standard leverage assumption distribution (5x/10x/20x/50x/100x)

Output: ranked list of price levels with "heat score" (0-100), separated for
LONG-side liquidations (price moves DOWN to trigger) and SHORT-side
(price moves UP to trigger).

Use cases:
  - Pre-trade: see if your TP/SL is near a likely liquidation cluster
  - Mid-trade: identify where the next move is likely magnetized to
  - Risk: avoid placing SL in a "liquidation honeypot" where MMs hunt stops

Output JSON to stdout. CLI:
  python3 liq_heatmap.py --symbol BTCUSDT
  python3 liq_heatmap.py --symbol TONUSDT --quick     # human-readable summary
  python3 liq_heatmap.py --symbol ETHUSDT --top 5     # top 5 clusters each side
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from typing import Any

# Common leverage tiers used in retail crypto perp trading
# Weighting reflects typical distribution (most use 10-25x)
LEVERAGE_TIERS: list[tuple[int, float]] = [
    (5, 0.05),    # 5% of OI at 5x
    (10, 0.20),   # 20% at 10x
    (15, 0.20),   # 20% at 15x
    (20, 0.25),   # 25% at 20x (most popular)
    (25, 0.15),   # 15% at 25x
    (50, 0.10),   # 10% at 50x
    (100, 0.05),  # 5% at 100x (degens)
]

# Maintenance margin (Binance default for ETH/BTC; TON/alts are similar)
MAINTENANCE_MARGIN = 0.005  # 0.5%


def _http_get(url: str, timeout: int = 5) -> Any:
    """Wrapper for safe HTTP GET with proper headers."""
    req = urllib.request.Request(url, headers={"User-Agent": "wally-trader/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_market_state(symbol: str) -> dict[str, Any]:
    """Fetch current price + OI + L/S + recent swings for symbol."""
    s = symbol.upper()

    # Spot price
    price = float(_http_get(f"https://api.binance.com/api/v3/ticker/price?symbol={s}")["price"])

    # 24h stats for swings
    stats = _http_get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={s}")
    high_24h = float(stats["highPrice"])
    low_24h = float(stats["lowPrice"])

    # Open Interest (Futures)
    oi_data = _http_get(
        f"https://fapi.binance.com/futures/data/openInterestHist"
        f"?symbol={s}&period=1h&limit=24"
    )
    oi_now_usd = float(oi_data[-1]["sumOpenInterestValue"]) if oi_data else 0.0

    # Top traders POSITION ratio (smart money)
    pos_data = _http_get(
        f"https://fapi.binance.com/futures/data/topLongShortPositionRatio"
        f"?symbol={s}&period=1h&limit=12"
    )
    pos_ls = float(pos_data[-1]["longShortRatio"]) if pos_data else 1.0

    # Retail accounts ratio
    retail_data = _http_get(
        f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
        f"?symbol={s}&period=1h&limit=12"
    )
    retail_ls = float(retail_data[-1]["longShortRatio"]) if retail_data else 1.0

    return {
        "price": price,
        "high_24h": high_24h,
        "low_24h": low_24h,
        "oi_now_usd": oi_now_usd,
        "smart_money_ls": pos_ls,
        "retail_ls": retail_ls,
    }


def estimate_clusters(
    market: dict[str, Any], top_n: int = 7
) -> dict[str, list[dict[str, Any]]]:
    """Estimate liquidation cluster prices and heat scores.

    For each leverage tier, calculate the price at which positions opened at
    recent reference points (24h high for shorts, 24h low for longs) would be
    liquidated. Cluster nearby prices and weight by:
      - tier weight (more popular leverage = more concentrated stops)
      - L/S ratio bias (heavy long → more long-side stops to hunt)
    """
    price = market["price"]
    h24 = market["high_24h"]
    l24 = market["low_24h"]

    # Reference entry prices (where positions are likely loaded)
    # Use multiple anchor points for both sides
    long_anchors = [
        l24,                    # Bought near 24h low
        l24 + (price - l24) * 0.30,  # Bought on 30% retracement up
        l24 + (price - l24) * 0.60,  # Bought near current
        price,                  # Just opened
    ]
    short_anchors = [
        h24,                    # Sold near 24h high
        h24 - (h24 - price) * 0.30,  # Sold on 30% retracement down
        h24 - (h24 - price) * 0.60,  # Sold near current
        price,                  # Just opened
    ]

    # L/S bias amplifier
    long_bias = market["smart_money_ls"]
    short_bias = 1.0 / long_bias if long_bias > 0 else 1.0

    # Normalize to amplifier in [0.5, 2.0]
    def _amp(ratio: float) -> float:
        return max(0.5, min(2.0, ratio))

    long_amp = _amp(long_bias)
    short_amp = _amp(short_bias)

    long_clusters: dict[float, float] = {}
    short_clusters: dict[float, float] = {}

    for tier, weight in LEVERAGE_TIERS:
        # Liquidation distance: 1/leverage minus maintenance margin
        liq_pct = (1.0 / tier) - MAINTENANCE_MARGIN
        if liq_pct <= 0:
            continue

        # LONG liquidations (price drops below entry by liq_pct)
        for anchor in long_anchors:
            liq_price = anchor * (1 - liq_pct)
            if liq_price < price * 0.5 or liq_price > price:
                continue  # Out of relevant range
            # Round to ~0.1% precision for clustering
            bucket = round(liq_price / price, 4) * price
            long_clusters[bucket] = long_clusters.get(bucket, 0.0) + (weight * long_amp)

        # SHORT liquidations (price rises above entry by liq_pct)
        for anchor in short_anchors:
            liq_price = anchor * (1 + liq_pct)
            if liq_price > price * 1.5 or liq_price < price:
                continue
            bucket = round(liq_price / price, 4) * price
            short_clusters[bucket] = short_clusters.get(bucket, 0.0) + (weight * short_amp)

    # Convert to sorted list with heat score 0-100
    def _format(clusters: dict[float, float], side: str) -> list[dict[str, Any]]:
        if not clusters:
            return []
        max_heat = max(clusters.values())
        result = []
        for level, raw_heat in sorted(clusters.items(), key=lambda x: -x[1]):
            heat = round((raw_heat / max_heat) * 100, 1)
            distance = (level - price) / price * 100
            result.append({
                "price": round(level, 6),
                "heat_score": heat,
                "distance_pct": round(distance, 3),
                "side": side,
            })
        return result[:top_n]

    return {
        "longs": _format(long_clusters, "LONG_LIQ"),
        "shorts": _format(short_clusters, "SHORT_LIQ"),
    }


def assess_heatmap(symbol: str, top_n: int = 7) -> dict[str, Any]:
    """Full assessment: market + clusters + interpretation."""
    try:
        market = fetch_market_state(symbol)
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

    clusters = estimate_clusters(market, top_n=top_n)

    # Find the magnet level (closest high-heat cluster)
    all_clusters = clusters["longs"] + clusters["shorts"]
    magnet = None
    if all_clusters:
        # Closest cluster with heat >= 50
        candidates = [c for c in all_clusters if c["heat_score"] >= 50]
        if candidates:
            magnet = min(candidates, key=lambda c: abs(c["distance_pct"]))

    # Bias inference
    long_total_heat = sum(c["heat_score"] for c in clusters["longs"])
    short_total_heat = sum(c["heat_score"] for c in clusters["shorts"])
    if long_total_heat > short_total_heat * 1.3:
        bias = "LONG_LIQ_DOMINANT"
        bias_note = (
            f"Long liquidations dominate ({long_total_heat:.0f} vs {short_total_heat:.0f}). "
            "Heavy long pile-up — fade into longs (SHORT) is favored if price stalls."
        )
    elif short_total_heat > long_total_heat * 1.3:
        bias = "SHORT_LIQ_DOMINANT"
        bias_note = (
            f"Short liquidations dominate ({short_total_heat:.0f} vs {long_total_heat:.0f}). "
            "Heavy short pile-up — squeeze setup if price breaks resistance (LONG favored)."
        )
    else:
        bias = "BALANCED"
        bias_note = (
            f"L/S clusters balanced ({long_total_heat:.0f} vs {short_total_heat:.0f}). "
            "No clear magnet bias — directional moves driven by other factors."
        )

    return {
        "symbol": symbol,
        "price_now": market["price"],
        "high_24h": market["high_24h"],
        "low_24h": market["low_24h"],
        "oi_usd": round(market["oi_now_usd"], 0),
        "smart_money_ls": round(market["smart_money_ls"], 3),
        "retail_ls": round(market["retail_ls"], 3),
        "bias": bias,
        "bias_note": bias_note,
        "magnet": magnet,
        "longs_liq": clusters["longs"],
        "shorts_liq": clusters["shorts"],
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def format_summary(result: dict[str, Any]) -> str:
    """Human-readable summary for --quick mode."""
    if "error" in result:
        return f"❌ {result['symbol']}: {result['error']}"

    lines = [
        f"=== LIQ HEATMAP {result['symbol']} ===",
        f"Price: ${result['price_now']:.6g}  |  OI: ${result['oi_usd']/1e6:.1f}M  |  Smart L/S: {result['smart_money_ls']:.2f}",
        f"Bias: {result['bias']}",
        f"  → {result['bias_note']}",
    ]

    if result["magnet"]:
        m = result["magnet"]
        lines.append(
            f"\n🧲 Magnet: ${m['price']:.6g} ({m['distance_pct']:+.2f}%) "
            f"side={m['side']} heat={m['heat_score']}"
        )

    lines.append("\n🔴 SHORT-side liq (price UP to trigger):")
    for c in result["shorts_liq"][:5]:
        bar = "█" * int(c["heat_score"] / 10)
        lines.append(f"  ${c['price']:.6g}  ({c['distance_pct']:+.2f}%)  heat={c['heat_score']:>5.1f}  {bar}")

    lines.append("\n🟢 LONG-side liq (price DOWN to trigger):")
    for c in result["longs_liq"][:5]:
        bar = "█" * int(c["heat_score"] / 10)
        lines.append(f"  ${c['price']:.6g}  ({c['distance_pct']:+.2f}%)  heat={c['heat_score']:>5.1f}  {bar}")

    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="Liquidation cluster heatmap estimator")
    p.add_argument("--symbol", required=True, help="Asset symbol (e.g. BTCUSDT)")
    p.add_argument("--top", type=int, default=7, help="Top N clusters per side")
    p.add_argument("--quick", action="store_true", help="Human-readable summary")
    args = p.parse_args()

    result = assess_heatmap(args.symbol, top_n=args.top)

    if args.quick:
        print(format_summary(result), file=sys.stderr)

    print(json.dumps(result, indent=2))
    return 0 if "error" not in result else 1


if __name__ == "__main__":
    sys.exit(main())
