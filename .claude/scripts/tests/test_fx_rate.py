"""Tests for fx_rate.py canonical."""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import fx_rate


def test_get_cache_path(tmp_fx_cache):
    """Cache path is OS-temp / wally_fx_cache_X_Y.json."""
    p = fx_rate.get_cache_path("USD", "CRC")
    assert p.parent == tmp_fx_cache
    assert "wally_fx_cache_usd_crc" in p.name


def test_read_rate_from_cache_valid(tmp_fx_cache):
    cache = tmp_fx_cache / "wally_fx_cache_usd_crc.json"
    cache.write_text(json.dumps({"rates": {"CRC": 510.50}}))
    assert fx_rate.read_rate_from_cache(cache, "CRC") == 510.50


def test_read_rate_from_cache_missing_field(tmp_fx_cache):
    cache = tmp_fx_cache / "test.json"
    cache.write_text(json.dumps({"rates": {"EUR": 0.92}}))
    assert fx_rate.read_rate_from_cache(cache, "CRC") is None


def test_read_rate_from_cache_corrupted(tmp_fx_cache):
    cache = tmp_fx_cache / "test.json"
    cache.write_text("not valid json")
    assert fx_rate.read_rate_from_cache(cache, "CRC") is None


def test_get_rate_uses_fresh_cache(tmp_fx_cache, monkeypatch):
    cache = fx_rate.get_cache_path("USD", "CRC")
    cache.write_text(json.dumps({"rates": {"CRC": 500.0}}))

    # Mock fetch to ensure it's NOT called
    monkeypatch.setattr(fx_rate, "fetch_rates", lambda *a, **k: pytest.fail("should use cache"))

    rate, source = fx_rate.get_rate("USD", "CRC")
    assert rate == 500.0
    assert source == "cache_fresh"


def test_get_rate_falls_back_to_api(tmp_fx_cache, monkeypatch):
    """No cache → API fetch."""
    monkeypatch.setattr(fx_rate, "fetch_rates", lambda *a, **k: {"rates": {"CRC": 555.55}})
    rate, source = fx_rate.get_rate("USD", "CRC")
    assert rate == 555.55
    assert source == "api"


def test_get_rate_falls_back_to_stale_cache(tmp_fx_cache, monkeypatch):
    """API fails AND cache exists (stale) → use stale cache."""
    cache = fx_rate.get_cache_path("USD", "CRC")
    cache.write_text(json.dumps({"rates": {"CRC": 480.0}}))
    # Force cache stale by setting old mtime
    old = time.time() - (fx_rate.CACHE_TTL_SECONDS + 100)
    import os
    os.utime(cache, (old, old))

    monkeypatch.setattr(fx_rate, "fetch_rates", lambda *a, **k: None)

    rate, source = fx_rate.get_rate("USD", "CRC")
    assert rate == 480.0
    assert source == "cache_stale"


def test_get_rate_hardcode_fallback(tmp_fx_cache, monkeypatch):
    """No cache + API fail → hardcode 510."""
    monkeypatch.setattr(fx_rate, "fetch_rates", lambda *a, **k: None)
    rate, source = fx_rate.get_rate("USD", "CRC")
    assert rate == fx_rate.HARDCODE_USD_CRC
    assert source == "hardcode"
