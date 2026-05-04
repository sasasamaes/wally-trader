"""Market selection: tag/volume filter + rank by |p − 0.5| + atomic write."""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from polymarket import config
from polymarket.client import Market, list_markets

log = logging.getLogger(__name__)


def _parse_iso(s: str) -> datetime:
    """Tolerant ISO parser; treat naive as UTC. On parse failure, return
    datetime.min so malformed dates fail the min-days-to-resolution filter
    rather than silently passing it.
    """
    s = s.replace("Z", "+00:00") if s.endswith("Z") else s
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def filter_markets(markets: list[Market]) -> list[Market]:
    """Apply volume, tag (or slug-weight fallback), and end-date filters.

    Polymarket's /markets endpoint returns tags=None for most markets in
    practice; the rich tag metadata lives on /events. To keep V1 working
    against the real API we accept either:
      - a market whose tags overlap TAGS_WHITELIST, OR
      - a market whose slug matches an entry in WEIGHT_MAPPING (i.e. a
        market we already know how to interpret).
    Markets matching neither path are dropped.
    """
    now = datetime.now(timezone.utc)
    out: list[Market] = []
    for m in markets:
        if m.closed:
            continue
        if m.volume_24h < config.VOLUME_THRESHOLD_USD:
            continue
        tag_match = bool(m.tags) and any(t.lower() in config.TAGS_WHITELIST for t in m.tags)
        slug_match = config.match_weight(m.slug) is not None
        if not (tag_match or slug_match):
            continue
        end = _parse_iso(m.end_date)
        days_out = (end - now).days
        if days_out < config.MIN_DAYS_TO_RESOLUTION:
            continue
        out.append(m)
    return out


def rank_markets(markets: list[Market]) -> list[Market]:
    """Sort by |prob_yes - 0.5| ascending (closest to 50/50 first)."""
    return sorted(markets, key=lambda m: abs(m.prob_yes - 0.5))


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        finally:
            raise


def write_tracked_markets(markets: list[Market]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(markets),
        "markets": [asdict(m) for m in markets],
    }
    _atomic_write(config.TRACKED_MARKETS_PATH, payload)


def run(*, dry_run: bool = False) -> int:
    """Run a discovery cycle. Returns the number of markets selected."""
    raw = list_markets(active=True, closed=False, limit=200)
    filtered = filter_markets(raw)
    ranked = rank_markets(filtered)[: config.TOP_N_MARKETS]

    if not ranked and config.TRACKED_MARKETS_PATH.exists():
        log.warning("Discovery returned 0 markets — keeping previous tracked file.")
        return 0

    if dry_run:
        for m in ranked:
            print(f"{m.slug}\t{m.prob_yes:.2f}\t${m.volume_24h:,.0f}")
        return len(ranked)

    write_tracked_markets(ranked)
    return len(ranked)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [discovery] %(message)s")
    dry = "--dry-run" in sys.argv
    n = run(dry_run=dry)
    print(f"Discovery completed: {n} market(s) selected.")
    return 0 if n >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
