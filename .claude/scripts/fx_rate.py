#!/usr/bin/env python3
"""Cross-platform port of fx_rate.sh — USD→CRC rate with 1h cache.

Usage:
  python fx_rate.py             — print rate to stdout (no newline), exit 0/1
  python fx_rate.py --pair USD CRC  — explicit pair (default USD→CRC)

Output stdout: rate only (e.g. "455.53"). Stderr: status messages.
Exit codes: 0 OK (live or cached), 1 hardcode fallback.
"""
import json
import sys
import tempfile
import time
import urllib.request
import urllib.error
from pathlib import Path

CACHE_TTL_SECONDS = 3600  # 1h
HARDCODE_USD_CRC = 510.0  # ~average 2024-2026


def get_cache_path(base: str, quote: str) -> Path:
    return Path(tempfile.gettempdir()) / f"wally_fx_cache_{base.lower()}_{quote.lower()}.json"


def read_rate_from_cache(cache: Path, quote: str):
    """Returns rate or None."""
    if not cache.exists():
        return None
    try:
        data = json.loads(cache.read_text())
        rates = data.get("rates", {})
        return rates.get(quote.upper())
    except (json.JSONDecodeError, OSError):
        return None


def fetch_rates(base: str = "USD"):
    """Fetch from open.er-api.com. Returns dict of rates or None."""
    url = f"https://open.er-api.com/v6/latest/{base}"
    try:
        with urllib.request.urlopen(url, timeout=4) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError, TimeoutError):
        return None


def get_rate(base: str = "USD", quote: str = "CRC") -> tuple:
    """Returns (rate, source). source ∈ ('cache_fresh', 'api', 'cache_stale', 'hardcode')."""
    cache = get_cache_path(base, quote)

    # 1) Fresh cache
    if cache.exists():
        age = time.time() - cache.stat().st_mtime
        if age < CACHE_TTL_SECONDS:
            rate = read_rate_from_cache(cache, quote)
            if rate is not None:
                return float(rate), "cache_fresh"

    # 2) Refresh API
    data = fetch_rates(base)
    if data and "rates" in data and quote.upper() in data["rates"]:
        cache.write_text(json.dumps(data))
        return float(data["rates"][quote.upper()]), "api"

    # 3) Stale cache
    rate = read_rate_from_cache(cache, quote)
    if rate is not None:
        print("fx_rate: usando cache stale (API offline)", file=sys.stderr)
        return float(rate), "cache_stale"

    # 4) Hardcode
    print(f"fx_rate: API offline y sin cache, usando hardcode {HARDCODE_USD_CRC}", file=sys.stderr)
    return HARDCODE_USD_CRC, "hardcode"


def main(argv):
    base, quote = "USD", "CRC"
    args = argv[1:]
    if "--pair" in args:
        idx = args.index("--pair")
        if len(args) >= idx + 3:
            base, quote = args[idx + 1], args[idx + 2]
    rate, source = get_rate(base, quote)
    sys.stdout.write(f"{rate}")
    sys.stdout.flush()
    return 0 if source != "hardcode" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
