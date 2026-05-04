"""Hourly poller that appends snapshots for every tracked market."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from polymarket import config
from polymarket.client import PolymarketError, get_market_with_fallback

log = logging.getLogger(__name__)


def _load_tracked(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        log.error("tracked_markets.json is malformed; aborting cycle")
        return []
    return data.get("markets", [])


def _append_snapshot(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(payload, separators=(",", ":")) + "\n")


def run_once() -> int:
    """Run a single poll cycle. Returns number of snapshots written."""
    tracked = _load_tracked(config.TRACKED_MARKETS_PATH)
    if not tracked:
        log.info("No tracked markets; skipping cycle")
        return 0

    written = 0
    ts = datetime.now(timezone.utc).isoformat()
    for entry in tracked:
        market_id = entry.get("id") or entry.get("slug")
        if not market_id:
            continue
        try:
            m = get_market_with_fallback(market_id)
        except PolymarketError as exc:
            log.warning("Skipping %s: %s", market_id, exc)
            continue
        payload = {
            "ts": ts,
            "id": m.id,
            "slug": m.slug,
            "prob": m.prob_yes,
            "vol_24h": m.volume_24h,
            "last_trade": m.last_trade,
        }
        _append_snapshot(config.SNAPSHOTS_PATH, payload)
        written += 1
    log.info("Poller wrote %d snapshots", written)
    return written


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [poller] %(message)s")
    if "--once" in sys.argv:
        n = run_once()
        print(f"Wrote {n} snapshot(s).")
        return 0
    # Default: also a single shot — launchd handles cadence
    n = run_once()
    return 0 if n >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
