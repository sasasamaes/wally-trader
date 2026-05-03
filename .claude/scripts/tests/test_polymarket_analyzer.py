"""Tests for polymarket.analyzer — deltas, composite, report."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Ensure .claude/scripts is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from polymarket import analyzer  # noqa: E402

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------
NOW_REF = datetime(2026, 5, 2, 13, 5, 0, tzinfo=timezone.utc)

FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "polymarket" / "snapshots_sample.jsonl"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def all_snapshots():
    return analyzer.load_snapshots(FIXTURE_PATH)


@pytest.fixture()
def aaa_snapshots(all_snapshots):
    return [s for s in all_snapshots if s["id"] == "0xaaa"]


@pytest.fixture()
def tmp_snapshots(tmp_path):
    """Write a single fresh snapshot to a temp JSONL file."""
    p = tmp_path / "snaps.jsonl"
    row = {
        "ts": NOW_REF.isoformat(),
        "id": "0xccc",
        "slug": "fed-cut-rates-in-may-2026",
        "prob": 0.60,
        "vol_24h": 1_000_000,
        "last_trade": 0.60,
    }
    p.write_text(json.dumps(row) + "\n")
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_load_snapshots_returns_dicts(all_snapshots):
    """load_snapshots returns a list of dicts with expected keys."""
    assert len(all_snapshots) == 6
    for snap in all_snapshots:
        assert isinstance(snap, dict)
        assert "ts" in snap
        assert "prob" in snap
        assert "id" in snap


def test_load_snapshots_skips_malformed(tmp_path):
    """load_snapshots silently skips non-JSON and JSON-without-required-keys."""
    p = tmp_path / "mixed.jsonl"
    good = json.dumps(
        {"ts": "2026-05-02T13:00:00+00:00", "id": "0xgood", "slug": "x", "prob": 0.5,
         "vol_24h": 100, "last_trade": 0.5}
    )
    bad_json = "not json at all"
    bad_keys = json.dumps({"ts": "2026-05-02T13:00:00+00:00"})  # missing required keys
    p.write_text("\n".join([good, bad_json, bad_keys]) + "\n")

    result = analyzer.load_snapshots(p)
    assert len(result) == 1
    assert result[0]["id"] == "0xgood"


def test_compute_deltas_for_market(aaa_snapshots):
    """compute_deltas picks closest snapshot within tolerance window.

    NOW_REF = 2026-05-02T13:05Z
    - prob_now  = 0.62  (latest snapshot 2026-05-02T13:00)
    - delta_1h  = 0.62 - 0.55 = 0.07  (2026-05-02T12:00, 5min off 1h target, within 30min tol)
    - delta_24h = 0.62 - 0.54 = 0.08  (2026-05-01T13:00, 5min off 24h target, within 2h tol)
    - delta_7d  = 0.62 - 0.48 = 0.14  (2026-04-25T13:00, 5min off 7d target, within 24h tol)
    """
    out = analyzer.compute_deltas(aaa_snapshots, now=NOW_REF)

    assert out["prob_now"] == pytest.approx(0.62, abs=0.001)
    assert out["delta_1h"] == pytest.approx(0.07, abs=0.001)
    # Plan noted 0.07 was a typo — correct value is 0.08 (0.62 - 0.54, snapshot at 2026-05-01T13:00)
    assert out["delta_24h"] == pytest.approx(0.08, abs=0.001)
    assert out["delta_7d"] == pytest.approx(0.14, abs=0.001)


def test_compute_composite_demeaned(all_snapshots):
    """composite uses (prob - 0.5) * weight, divided by sum(|w|), scaled ×200.

    Markets:
      0xaaa slug=fed-cut-rates-in-may-2026 → weight +0.30, prob_now=0.62
      0xbbb slug=us-recession-2026         → weight -0.25, prob_now=0.28

    per_market = {
      "0xaaa": {"prob_now": 0.62, ...},
      "0xbbb": {"prob_now": 0.28, ...},
    }

    numerator   = (0.62 - 0.5) * 0.30  +  (0.28 - 0.5) * (-0.25)
                = 0.12 * 0.30           +  (-0.22) * (-0.25)
                = 0.036 + 0.055 = 0.091
    total_weight = |0.30| + |-0.25| = 0.55
    composite    = (0.091 / 0.55) * 200 ≈ 33.09
    """
    per_market = {}
    for market_id in ("0xaaa", "0xbbb"):
        snaps = [s for s in all_snapshots if s["id"] == market_id]
        per_market[market_id] = analyzer.compute_deltas(snaps, now=NOW_REF)

    result = analyzer.composite(per_market)
    assert result is not None
    assert result == pytest.approx(33.09, abs=0.1)


def test_composite_undefined_when_no_weights():
    """composite returns None when no market has a matching weight."""
    per_market = {
        "0xzzz": {
            "slug": "totally-unknown-slug",
            "prob_now": 0.55,
            "delta_1h": 0.01,
            "delta_24h": 0.02,
            "delta_7d": 0.03,
        }
    }
    assert analyzer.composite(per_market) is None


def test_status_stale_when_snapshot_too_old(tmp_path):
    """report() returns STALE when the latest snapshot is older than STALE_AFTER_SECONDS."""
    p = tmp_path / "old.jsonl"
    old_ts = "2026-05-01T00:00:00+00:00"  # >2h before NOW_REF
    row = {
        "ts": old_ts,
        "id": "0xold",
        "slug": "fed-cut-rates-in-may-2026",
        "prob": 0.55,
        "vol_24h": 500_000,
        "last_trade": 0.55,
    }
    p.write_text(json.dumps(row) + "\n")

    result = analyzer.report(snapshots_path=p, now=NOW_REF)
    assert result["status"] == "STALE"


def test_status_fresh_when_recent(tmp_snapshots):
    """report() returns FRESH when the latest snapshot is within STALE_AFTER_SECONDS."""
    result = analyzer.report(snapshots_path=tmp_snapshots, now=NOW_REF)
    assert result["status"] == "FRESH"
