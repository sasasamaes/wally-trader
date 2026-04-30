"""Tests for chainlink_price.py canonical."""
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import chainlink_price as cp


def test_feeds_includes_btc():
    assert "BTC" in cp.FEEDS
    addr, dec = cp.FEEDS["BTC"]
    assert addr.startswith("0x") and len(addr) == 42
    assert dec == 8


def test_unknown_pair_exits(capsys):
    with pytest.raises(SystemExit) as exc:
        cp.get_price("UNKNOWN_PAIR")
    assert exc.value.code == 2


def test_compare_verdict_thresholds():
    assert cp.compare_verdict(0.0) == "OK"
    assert cp.compare_verdict(0.2) == "OK"
    assert cp.compare_verdict(-0.29) == "OK"
    assert cp.compare_verdict(0.3) == "WARN"
    assert cp.compare_verdict(-0.5) == "WARN"
    assert cp.compare_verdict(0.99) == "WARN"
    assert cp.compare_verdict(1.0) == "ALERT"
    assert cp.compare_verdict(-1.5) == "ALERT"
    assert cp.compare_verdict(5.0) == "ALERT"


def test_get_price_uses_fresh_cache(tmp_chainlink_cache, monkeypatch):
    """Fresh cache → no RPC call."""
    cache = cp.get_cache_path("BTC")
    cache.write_text("75000.50")

    monkeypatch.setattr(cp, "fetch_price", lambda a, d: pytest.fail("should use cache"))

    price, stale = cp.get_price("BTC")
    assert price == 75000.50
    assert stale is False


def test_get_price_fetches_when_no_cache(tmp_chainlink_cache, monkeypatch):
    """No cache → fetch from RPC. Mocked."""
    monkeypatch.setattr(cp, "fetch_price", lambda addr, dec: 75100.25)

    price, stale = cp.get_price("BTC")
    assert price == 75100.25
    assert stale is False
    # Verify cache was written
    cache = cp.get_cache_path("BTC")
    assert cache.exists()
    assert "75100.25" in cache.read_text()


def test_get_price_stale_cache_when_rpc_fails(tmp_chainlink_cache, monkeypatch):
    """RPC fails AND old cache exists → use stale cache."""
    cache = cp.get_cache_path("BTC")
    cache.write_text("70000.00")
    # Make stale
    import os
    old = time.time() - (cp.CACHE_TTL_SECONDS + 100)
    os.utime(cache, (old, old))

    monkeypatch.setattr(cp, "fetch_price", lambda a, d: None)

    price, stale = cp.get_price("BTC")
    assert price == 70000.00
    assert stale is True


def test_get_price_total_failure(tmp_chainlink_cache, monkeypatch, capsys):
    """No cache AND RPC fails → SystemExit 1."""
    monkeypatch.setattr(cp, "fetch_price", lambda a, d: None)

    with pytest.raises(SystemExit) as exc:
        cp.get_price("BTC")
    assert exc.value.code == 1


def test_compare_mode_negative_delta(tmp_chainlink_cache, monkeypatch, capsys):
    """Compare mode computes negative delta correctly."""
    monkeypatch.setattr(cp, "fetch_price", lambda a, d: 100.0)
    monkeypatch.setattr(sys, "argv", ["chainlink_price.py", "BTC", "--compare", "101.0", "--json"])
    rc = cp.main()
    captured = capsys.readouterr()
    assert rc == 0
    import json as j
    data = j.loads(captured.out)
    assert data["chainlink"] == 100.0
    assert data["tv"] == 101.0
    assert abs(data["delta_pct"] - (-0.9901)) < 0.01
    assert data["verdict"] == "WARN"
