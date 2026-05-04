"""Tests for polymarket.discovery."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from polymarket import config, discovery
from polymarket.client import Market


def _mk_market(slug, prob, vol, days_out=30, tags=("fed",)):
    end_date = (datetime.now(timezone.utc) + timedelta(days=days_out)).isoformat()
    return Market(
        id=f"id-{slug}",
        slug=slug,
        question=slug,
        prob_yes=prob,
        volume_24h=vol,
        end_date=end_date,
        tags=tags,
    )


def test_filter_drops_low_volume():
    markets = [
        _mk_market("a", 0.5, 600_000),
        _mk_market("b", 0.5, 100_000),  # below threshold
    ]
    out = discovery.filter_markets(markets)
    assert {m.slug for m in out} == {"a"}


def test_filter_drops_no_tag_match():
    markets = [
        _mk_market("a", 0.5, 600_000, tags=("fed",)),
        _mk_market("b", 0.5, 600_000, tags=("sports",)),  # tag not whitelisted
    ]
    out = discovery.filter_markets(markets)
    assert {m.slug for m in out} == {"a"}


def test_filter_drops_too_close_to_resolution():
    markets = [
        _mk_market("a", 0.5, 600_000, days_out=30),
        _mk_market("b", 0.5, 600_000, days_out=2),  # < MIN_DAYS_TO_RESOLUTION
    ]
    out = discovery.filter_markets(markets)
    assert {m.slug for m in out} == {"a"}


def test_rank_prefers_50_50():
    markets = [
        _mk_market("a", 0.10, 600_000),  # far from 50/50
        _mk_market("b", 0.50, 600_000),  # exactly 50/50
        _mk_market("c", 0.45, 600_000),  # close to 50/50
    ]
    ranked = discovery.rank_markets(markets)
    assert [m.slug for m in ranked] == ["b", "c", "a"]


def test_atomic_write(tmp_path, monkeypatch):
    target = tmp_path / "tracked.json"
    monkeypatch.setattr(config, "TRACKED_MARKETS_PATH", target)
    markets = [_mk_market("a", 0.5, 600_000)]
    discovery.write_tracked_markets(markets)
    data = json.loads(target.read_text())
    assert data["markets"][0]["slug"] == "a"
    assert "generated_at" in data


def test_run_discovery_keeps_previous_when_zero_results(tmp_path, monkeypatch, mocker):
    target = tmp_path / "tracked.json"
    target.write_text(json.dumps({"markets": [{"slug": "old"}], "generated_at": "old"}))
    monkeypatch.setattr(config, "TRACKED_MARKETS_PATH", target)
    mocker.patch.object(discovery, "list_markets", return_value=[])

    n = discovery.run()
    assert n == 0
    data = json.loads(target.read_text())
    assert data["markets"][0]["slug"] == "old"  # unchanged


def test_run_discovery_writes_empty_on_first_run_zero(tmp_path, monkeypatch, mocker):
    target = tmp_path / "tracked.json"
    monkeypatch.setattr(config, "TRACKED_MARKETS_PATH", target)
    mocker.patch.object(discovery, "list_markets", return_value=[])

    n = discovery.run()
    assert n == 0
    data = json.loads(target.read_text())
    assert data["markets"] == []


def test_filter_drops_malformed_end_date():
    """Markets with unparseable end_date must be dropped (fail-closed)."""
    bad_market = Market(
        id="id-bad",
        slug="bad-date",
        question="bad date",
        prob_yes=0.5,
        volume_24h=600_000,
        end_date="not-an-iso-date",
        tags=("fed",),
    )
    good_market = _mk_market("good", 0.5, 600_000)
    out = discovery.filter_markets([bad_market, good_market])
    assert {m.slug for m in out} == {"good"}


def test_filter_accepts_markets_with_no_tags_when_slug_matches_weight():
    """Real Gamma API returns tags=None; slug-weight fallback must accept these."""
    m = Market(
        id="id-fed",
        slug="will-the-fed-cut-rates-in-may-2026",
        question="Fed cut May?",
        prob_yes=0.5,
        volume_24h=600_000,
        end_date=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        tags=(),  # empty — like real API response with tags=None coerced
    )
    out = discovery.filter_markets([m])
    assert {x.slug for x in out} == {"will-the-fed-cut-rates-in-may-2026"}


def test_filter_drops_markets_with_no_tags_and_no_weight_match():
    """Without tags AND without slug-weight match → dropped."""
    m = Market(
        id="id-noise",
        slug="completely-random-market",
        question="?",
        prob_yes=0.5,
        volume_24h=600_000,
        end_date=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        tags=(),
    )
    out = discovery.filter_markets([m])
    assert out == []
