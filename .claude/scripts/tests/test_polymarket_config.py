"""Tests for polymarket.config."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from polymarket import config


def test_defaults_present():
    assert config.GAMMA_BASE_URL.startswith("https://")
    assert config.CLOB_BASE_URL.startswith("https://")
    assert config.VOLUME_THRESHOLD_USD == 500_000
    assert config.TOP_N_MARKETS == 12
    assert config.POLL_INTERVAL_SECONDS == 3600
    assert config.STALE_AFTER_SECONDS == 7200
    assert isinstance(config.TAGS_WHITELIST, tuple)
    assert "fed" in config.TAGS_WHITELIST


def test_weight_mapping_first_match_wins():
    assert config.match_weight("will-the-fed-cut-rates-in-may-2026") == 0.30
    assert config.match_weight("us-recession-2026") == -0.25
    assert config.match_weight("trump-tariffs-q2") == -0.20
    assert config.match_weight("totally-unmapped-market") is None


def test_weight_mapping_case_insensitive():
    assert config.match_weight("Fed-Cut-Rates-May") == 0.30
    assert config.match_weight("US-RECESSION-2026") == -0.25


def test_data_paths_under_polymarket_dir():
    assert config.DATA_DIR.name == "data"
    assert config.SNAPSHOTS_PATH.name == "snapshots.jsonl"
    assert config.TRACKED_MARKETS_PATH.name == "tracked_markets.json"
