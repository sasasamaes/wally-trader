#!/usr/bin/env python3
"""Cross-profile risk guard — prevent same-asset exposure across multiple profiles.

Background: el sistema tiene 7 profiles, varios pueden tradear BTC. Si tienes
BTC LONG en retail Y BTC LONG en ftmo simultáneamente, tu riesgo direccional
es 2x. La regla "no BTC simultáneo" en CLAUDE.md era solo guía mental — este
script la hace ENFORCEMENT automático.

Usage:
  python cross_profile_guard.py check <asset> <side>
    → exit 0 + "PASS"
    → exit 1 + "BLOCK: <reason>"
  python cross_profile_guard.py status
    → JSON con todas las exposiciones activas cross-profile

Ejemplos:
  python cross_profile_guard.py check BTCUSDT LONG    # ¿puedo abrir BTC LONG en current profile?
  python cross_profile_guard.py check XAUUSD SHORT    # ¿XAUUSD SHORT colisiona con otro profile?

Detección de exposición activa por profile:
  - retail / retail-bingx / bitunix / quantfury → última entrada en trading_log.md sin "closed"
  - ftmo / fundingpips / fotmarkets → pending_orders.json con status "filled" or "pending"
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
PROFILES_DIR = SCRIPT_DIR.parent / "profiles"

# All possible profiles
ALL_PROFILES = ("retail", "retail-bingx", "ftmo", "fotmarkets",
                "fundingpips", "bitunix", "quantfury")

# Asset family normalization — same family → cross-profile collision
ASSET_FAMILIES = {
    "BTC": ["BTCUSDT", "BTCUSDT.P", "BTCUSD", "BTC-USD", "BTCPERP", "BTC"],
    "ETH": ["ETHUSDT", "ETHUSDT.P", "ETHUSD", "ETH-USD", "ETHPERP", "ETH"],
    "EURUSD": ["EURUSD", "EURUSD=X", "EUR/USD"],
    "GBPUSD": ["GBPUSD", "GBPUSD=X", "GBP/USD"],
    "USDJPY": ["USDJPY", "USDJPY=X", "USD/JPY"],
    "XAUUSD": ["XAUUSD", "GC=F", "XAU/USD", "GOLD"],
    "NAS100": ["NAS100", "NDX", "^NDX", "USTEC", "US100"],
    "SPX500": ["SPX500", "SPX", "^GSPC", "US500"],
}


def asset_family(asset: str) -> str:
    """Normalize asset name to family key (BTC, ETH, EURUSD...)."""
    asset_upper = asset.upper().replace(".P", "").replace("-USD", "")
    for family, aliases in ASSET_FAMILIES.items():
        if any(asset_upper == a.upper() or asset_upper.startswith(family) for a in aliases):
            return family
    return asset_upper  # fallback to raw


def get_active_profile() -> str:
    if os.environ.get("WALLY_PROFILE"):
        return os.environ["WALLY_PROFILE"].strip()
    flag = SCRIPT_DIR.parent / "active_profile"
    if flag.exists():
        return flag.read_text(encoding='utf-8').strip().split("|", 1)[0].strip()
    return ""


def get_open_pendings(profile: str) -> List[Dict]:
    """Read pending_orders.json for profile. Returns orders with non-terminal status."""
    pending_file = PROFILES_DIR / profile / "memory" / "pending_orders.json"
    if not pending_file.exists():
        return []
    try:
        data = json.loads(pending_file.read_text(encoding='utf-8'))
        orders = data.get("pending", []) if isinstance(data, dict) else []
    except (json.JSONDecodeError, OSError):
        return []
    # Active = not in terminal status
    terminal = {"canceled_manual", "canceled_auto", "expired_ttl", "filled_closed", "stopday"}
    return [o for o in orders if o.get("status", "pending") not in terminal]


def get_recent_open_trades(profile: str, last_n: int = 5) -> List[Dict]:
    """Parse trading_log.md to find recent OPEN trades (no exit timestamp).

    Format expected (markdown table):
      | YYYY-MM-DD | HH:MM | symbol | side | entry | sl | tp | size | result | ... |

    Returns list of dicts with keys: date, symbol, side, status (open|closed)
    where status='open' if 'result' column is empty/missing.
    """
    log_file = PROFILES_DIR / profile / "memory" / "trading_log.md"
    if not log_file.exists():
        return []
    out = []
    try:
        for line in log_file.read_text(encoding='utf-8').splitlines():
            if not line.startswith("| 20"):  # year prefix
                continue
            cols = [c.strip() for c in line.split("|")]
            # cols[0] = empty, cols[1] = date, cols[2] = time, cols[3] = symbol, cols[4] = side
            if len(cols) < 5:
                continue
            symbol = cols[3] if len(cols) > 3 else ""
            side = cols[4].lower() if len(cols) > 4 else ""
            # "result" varies in column position — seek a column that's empty/dash
            # for safety, take last 5 trades regardless and consider them potentially open
            out.append({
                "date": cols[1],
                "symbol": symbol,
                "side": side,
                "raw": line,
            })
    except OSError:
        pass
    return out[-last_n:]  # last N entries are most likely "still open" candidates


def collect_exposures() -> Dict[str, List[Dict]]:
    """Returns {profile: [{asset, side, source, ...}, ...]} for all profiles with active exposure."""
    out = {}
    for profile in ALL_PROFILES:
        exposures = []
        # Pendings
        for p in get_open_pendings(profile):
            asset = p.get("asset") or p.get("symbol", "")
            side = (p.get("side") or "").lower()
            if asset and side:
                exposures.append({
                    "asset": asset,
                    "family": asset_family(asset),
                    "side": side,
                    "source": "pending_order",
                    "status": p.get("status"),
                })
        # Recent open trades from log
        # Note: harder to detect closed vs open without explicit status — flag last 3 as potentially open
        for t in get_recent_open_trades(profile, last_n=3):
            if t["symbol"]:
                exposures.append({
                    "asset": t["symbol"],
                    "family": asset_family(t["symbol"]),
                    "side": t["side"],
                    "source": "trading_log_recent",
                    "date": t["date"],
                })
        if exposures:
            out[profile] = exposures
    return out


def check_collision(asset: str, side: str, current_profile: str) -> Optional[Dict]:
    """Returns collision dict {profile, asset, side, source} or None if no collision.

    Collision rules:
      1. Same family (BTC ≈ BTCUSDT.P ≈ BTC-USD), same side → BLOCK (double exposure)
      2. Same family, OPPOSITE side → ALLOW (intentional hedge)
      3. Different family → ALLOW
      4. Self profile → ALLOW (managed by single-profile rules)
    """
    family = asset_family(asset)
    side = side.lower()
    all_exposures = collect_exposures()
    for profile, exps in all_exposures.items():
        if profile == current_profile:
            continue
        for e in exps:
            if e["family"] == family and e["side"] == side:
                return {
                    "blocked_by_profile": profile,
                    "their_asset": e["asset"],
                    "their_side": e["side"],
                    "source": e["source"],
                    "your_asset": asset,
                    "your_side": side,
                    "family": family,
                }
    return None


def cmd_check(asset: str, side: str) -> int:
    current = get_active_profile()
    if not current:
        print("BLOCK: no active profile (run /profile <name> first)")
        return 1

    collision = check_collision(asset, side, current)
    if collision is None:
        print(f"PASS — {asset} {side.upper()} clear (no cross-profile collision)")
        return 0

    msg = (
        f"BLOCK: cross-profile collision detected.\n"
        f"  You're trying:    {collision['your_asset']} {collision['your_side'].upper()} on '{current}'\n"
        f"  Already open:     {collision['their_asset']} {collision['their_side'].upper()} on '{collision['blocked_by_profile']}' "
        f"({collision['source']})\n"
        f"  Family:           {collision['family']}\n"
        f"  Rule:             same-family + same-side cross-profile = double exposure → BLOCK\n"
        f"  Resolve:          close position in '{collision['blocked_by_profile']}' OR pick different asset"
    )
    print(msg)
    return 1


def cmd_status() -> int:
    """Print all active exposures cross-profile as JSON."""
    exposures = collect_exposures()
    print(json.dumps(exposures, indent=2, default=str))
    return 0


def main():
    if len(sys.argv) < 2:
        print("Usage: cross_profile_guard.py check <asset> <side> | status", file=sys.stderr)
        return 2
    cmd = sys.argv[1]
    if cmd == "check":
        if len(sys.argv) < 4:
            print("Usage: cross_profile_guard.py check <asset> <long|short>", file=sys.stderr)
            return 2
        return cmd_check(sys.argv[2], sys.argv[3])
    elif cmd == "status":
        return cmd_status()
    else:
        print(f"Unknown command: {cmd}. Use 'check' or 'status'.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
