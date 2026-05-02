"""Static configuration for the Polymarket macro sentiment integration.

Patterns are matched case-insensitively as substrings of the market slug.
First match wins; ordering of WEIGHT_MAPPING matters.
"""
from __future__ import annotations

from pathlib import Path

GAMMA_BASE_URL = "https://gamma-api.polymarket.com"
CLOB_BASE_URL = "https://clob.polymarket.com"

# Selection thresholds
VOLUME_THRESHOLD_USD = 500_000
TOP_N_MARKETS = 12
MIN_DAYS_TO_RESOLUTION = 7

# Operations
POLL_INTERVAL_SECONDS = 3600
STALE_AFTER_SECONDS = 7200  # 2h
HTTP_TIMEOUT_SECONDS = 5
HTTP_RETRIES = 2

# Tags accepted at discovery time (any match qualifies)
TAGS_WHITELIST = ("politics", "economics", "fed", "crypto")

# Composite scoring buckets (composite already in [-100, +100])
BUCKET_THRESHOLDS = (
    (-40.0, "STRONG-BEAR"),
    (-15.0, "MILD-BEAR"),
    (15.0, "NEUTRAL"),
    (40.0, "MILD-BULL"),
    (float("inf"), "STRONG-BULL"),
)

# Market slug substring → weight. First match wins.
# Convention: weight = how much YES probability moves BTC sentiment.
# Positive weight = YES is bullish for BTC; negative = YES is bearish.
WEIGHT_MAPPING: tuple[tuple[str, float], ...] = (
    ("fed-cut", 0.30),
    ("fed-rate-cut", 0.30),
    ("us-recession", -0.25),
    ("recession-2026", -0.25),
    ("trump-tariffs", -0.20),
    ("tariff-trigger", -0.20),
    ("stablecoin-pass", 0.20),
    ("crypto-regulation-pass", 0.20),
    ("debt-ceiling-crisis", -0.15),
    ("btc-etf-net-inflows", 0.10),
)


# Paths
_THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = _THIS_DIR / "data"
SNAPSHOTS_PATH = DATA_DIR / "snapshots.jsonl"
TRACKED_MARKETS_PATH = DATA_DIR / "tracked_markets.json"
RESOLUTIONS_PATH = DATA_DIR / "resolutions.jsonl"


def match_weight(slug: str) -> float | None:
    """Return the weight for a market slug, or None if unmapped."""
    s = slug.lower()
    for pattern, weight in WEIGHT_MAPPING:
        if pattern in s:
            return weight
    return None


def bucket_for(composite: float) -> str:
    """Map a composite score to its qualitative label."""
    for threshold, label in BUCKET_THRESHOLDS:
        if composite <= threshold:
            return label
    return BUCKET_THRESHOLDS[-1][1]
