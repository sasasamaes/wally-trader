"""Tests for polymarket.poller."""
import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from polymarket import config, poller
from polymarket.client import Market, PolymarketError


def _mk_market(slug, prob, vol):
    return Market(
        id=f"id-{slug}",
        slug=slug,
        question=slug,
        prob_yes=prob,
        volume_24h=vol,
        end_date="2026-12-31T00:00:00Z",
        last_trade=prob,
    )


@pytest.fixture
def tmp_paths(tmp_path, monkeypatch):
    tracked = tmp_path / "tracked.json"
    snaps = tmp_path / "snaps.jsonl"
    monkeypatch.setattr(config, "TRACKED_MARKETS_PATH", tracked)
    monkeypatch.setattr(config, "SNAPSHOTS_PATH", snaps)
    return tracked, snaps


def test_poller_appends_one_line_per_tracked_market(tmp_paths, mocker):
    tracked, snaps = tmp_paths
    tracked.write_text(json.dumps({"markets": [{"id": "0xaaa", "slug": "fed-cut-may"}, {"id": "0xbbb", "slug": "us-recession"}]}))

    def fake_get(market_id):
        return _mk_market("fed-cut-may", 0.62, 2_400_000) if market_id == "0xaaa" else _mk_market("us-recession", 0.28, 890_000)

    mocker.patch.object(poller, "get_market_with_fallback", side_effect=fake_get)

    n = poller.run_once()
    assert n == 2
    lines = snaps.read_text().splitlines()
    assert len(lines) == 2
    parsed = [json.loads(line) for line in lines]
    slugs = {p["slug"] for p in parsed}
    assert slugs == {"fed-cut-may", "us-recession"}
    for p in parsed:
        assert "ts" in p and "prob" in p and "vol_24h" in p


def test_poller_skips_market_on_error_and_continues(tmp_paths, mocker):
    tracked, snaps = tmp_paths
    tracked.write_text(json.dumps({"markets": [{"id": "0xaaa", "slug": "fed-cut-may"}, {"id": "0xbbb", "slug": "us-recession"}]}))

    def fake_get(market_id):
        if market_id == "0xaaa":
            raise PolymarketError("simulated")
        return _mk_market("us-recession", 0.28, 890_000)

    mocker.patch.object(poller, "get_market_with_fallback", side_effect=fake_get)

    n = poller.run_once()
    assert n == 1  # only one written
    lines = snaps.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["slug"] == "us-recession"


def test_poller_no_tracked_file_returns_zero(tmp_paths):
    tracked, snaps = tmp_paths  # tracked file does not exist
    n = poller.run_once()
    assert n == 0
    assert not snaps.exists()
