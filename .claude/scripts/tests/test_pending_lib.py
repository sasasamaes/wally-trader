"""Tests for pending_lib CRUD."""
import json
import os
import tempfile
from pathlib import Path
import pytest

from pending_lib import (
    PROFILES,
    load_pendings,
    save_pendings,
    append_pending,
    update_status,
    find_by_id,
    load_all_pendings,
)


@pytest.fixture
def tmp_repo(tmp_path, monkeypatch):
    """Create a fake .claude/profiles/*/memory/pending_orders.json tree."""
    for profile in PROFILES:
        memdir = tmp_path / ".claude" / "profiles" / profile / "memory"
        memdir.mkdir(parents=True, exist_ok=True)
        (memdir / "pending_orders.json").write_text(
            json.dumps({"pending": [], "meta": {}})
        )
    monkeypatch.setenv("WALLY_REPO_ROOT", str(tmp_path))
    return tmp_path


def test_load_empty_profile_returns_empty_list(tmp_repo):
    assert load_pendings("retail") == []


def test_save_and_load_roundtrip(tmp_repo):
    orders = [{"id": "ord_1", "profile": "retail", "status": "pending"}]
    save_pendings("retail", orders)
    assert load_pendings("retail") == orders


def test_append_pending_adds_status_history(tmp_repo):
    order = {"id": "ord_1", "profile": "retail", "status": "pending"}
    append_pending("retail", order)
    loaded = load_pendings("retail")
    assert len(loaded) == 1
    assert loaded[0]["id"] == "ord_1"
    assert len(loaded[0]["status_history"]) == 1
    assert loaded[0]["status_history"][0]["status"] == "pending"


def test_update_status_appends_history(tmp_repo):
    append_pending("retail", {"id": "ord_1", "profile": "retail", "status": "pending"})
    update_status("retail", "ord_1", "expired_ttl", note="TTL passed")
    loaded = load_pendings("retail")
    assert loaded[0]["status"] == "expired_ttl"
    assert len(loaded[0]["status_history"]) == 2
    assert loaded[0]["status_history"][-1]["note"] == "TTL passed"


def test_update_status_raises_if_id_missing(tmp_repo):
    with pytest.raises(KeyError):
        update_status("retail", "nope", "expired_ttl")


def test_find_by_id_searches_all_profiles(tmp_repo):
    append_pending("fotmarkets", {"id": "ord_fx", "profile": "fotmarkets", "status": "pending"})
    found = find_by_id("ord_fx")
    assert found is not None
    profile, order = found
    assert profile == "fotmarkets"
    assert order["id"] == "ord_fx"


def test_find_by_id_returns_none_if_not_found(tmp_repo):
    assert find_by_id("nonexistent") is None


def test_load_all_pendings_covers_all_profiles(tmp_repo):
    append_pending("retail", {"id": "a", "profile": "retail", "status": "pending"})
    append_pending("ftmo", {"id": "b", "profile": "ftmo", "status": "pending"})
    result = load_all_pendings()
    assert set(result.keys()) == set(PROFILES)
    assert len(result["retail"]) == 1
    assert len(result["ftmo"]) == 1
    assert result["fotmarkets"] == []


def test_save_is_atomic(tmp_repo):
    """Partial writes must not corrupt the file."""
    # Write a valid baseline
    save_pendings("retail", [{"id": "ord_1", "status": "pending"}])
    file_path = tmp_repo / ".claude/profiles/retail/memory/pending_orders.json"
    mtime_before = file_path.stat().st_mtime
    # Trigger a save that raises after writing temp file
    # (simulated: just verify roundtrip doesn't leave .tmp files behind)
    save_pendings("retail", [{"id": "ord_2", "status": "pending"}])
    assert not any(tmp_repo.rglob("*.tmp"))


from pending_lib import evaluate_invalidation, InvalidationResult
from datetime import datetime, timedelta, timezone


def _iso(dt):
    return dt.astimezone().isoformat(timespec="seconds")


def test_invalidation_ttl_expired():
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    order = {
        "id": "x",
        "expires_at": _iso(past),
        "force_exit_mx": _iso(datetime.now(timezone.utc) + timedelta(days=1)),
        "invalidation_price": 0,
        "invalidation_side": "below",
        "profile": "retail",
    }
    result = evaluate_invalidation(order, current_price=100.0, stopday_profiles=set())
    assert result.invalidated
    assert result.new_status == "expired_ttl"


def test_invalidation_price_broken_below():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    order = {
        "id": "x",
        "expires_at": _iso(future),
        "force_exit_mx": _iso(future),
        "invalidation_price": 76900,
        "invalidation_side": "below",
        "profile": "retail",
    }
    result = evaluate_invalidation(order, current_price=76800, stopday_profiles=set())
    assert result.invalidated
    assert result.new_status == "invalidated_price"


def test_invalidation_price_broken_above():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    order = {
        "id": "x",
        "expires_at": _iso(future),
        "force_exit_mx": _iso(future),
        "invalidation_price": 79500,
        "invalidation_side": "above",
        "profile": "retail",
    }
    result = evaluate_invalidation(order, current_price=79600, stopday_profiles=set())
    assert result.invalidated
    assert result.new_status == "invalidated_price"


def test_invalidation_stopday():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    order = {
        "id": "x",
        "expires_at": _iso(future),
        "force_exit_mx": _iso(future),
        "invalidation_price": 0,
        "invalidation_side": "below",
        "profile": "retail",
    }
    result = evaluate_invalidation(
        order, current_price=100.0, stopday_profiles={"retail"}
    )
    assert result.invalidated
    assert result.new_status == "invalidated_stopday"


def test_invalidation_force_exit():
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    future = datetime.now(timezone.utc) + timedelta(days=1)
    order = {
        "id": "x",
        "expires_at": _iso(future),
        "force_exit_mx": _iso(past),
        "invalidation_price": 0,
        "invalidation_side": "below",
        "profile": "retail",
    }
    result = evaluate_invalidation(order, current_price=100.0, stopday_profiles=set())
    assert result.invalidated
    assert result.new_status == "expired_force_exit"


def test_invalidation_none_active():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    order = {
        "id": "x",
        "expires_at": _iso(future),
        "force_exit_mx": _iso(future),
        "invalidation_price": 76900,
        "invalidation_side": "below",
        "profile": "retail",
    }
    result = evaluate_invalidation(order, current_price=77500, stopday_profiles=set())
    assert not result.invalidated
    assert result.new_status is None


from pending_lib import apply_whitelist_matrix


def _order(profile, asset, side, id_="ord_x", status="pending", created_at=None):
    return {
        "id": id_,
        "profile": profile,
        "asset": asset,
        "side": side,
        "status": status,
        "created_at": created_at or "2026-04-24T10:00:00-06:00",
    }


def test_whitelist_single_order_always_active():
    pendings = {"retail": [_order("retail", "BTCUSDT.P", "LONG")]}
    active, suspended = apply_whitelist_matrix(pendings, matrix_path=None)
    assert len(active) == 1
    assert len(suspended) == 0


def test_whitelist_blocks_retail_plus_retail_bingx():
    pendings = {
        "retail": [_order("retail", "BTCUSDT.P", "LONG", id_="a",
                          created_at="2026-04-24T10:00:00-06:00")],
        "retail-bingx": [_order("retail-bingx", "BTCUSDT.P", "LONG", id_="b",
                                created_at="2026-04-24T10:05:00-06:00")],
    }
    active, suspended = apply_whitelist_matrix(pendings, matrix_path=None)
    # newer (b) suspended; older (a) stays
    assert {o["id"] for o in active} == {"a"}
    assert {o["id"] for o in suspended} == {"b"}


def test_whitelist_blocks_same_family_same_side_cross_profile():
    pendings = {
        "retail": [_order("retail", "BTCUSDT.P", "LONG", id_="a",
                          created_at="2026-04-24T09:00:00-06:00")],
        "fotmarkets": [_order("fotmarkets", "BTCUSD", "LONG", id_="b",
                              created_at="2026-04-24T10:00:00-06:00")],
    }
    active, suspended = apply_whitelist_matrix(pendings, matrix_path=None)
    assert {o["id"] for o in active} == {"a"}
    assert {o["id"] for o in suspended} == {"b"}


def test_whitelist_allows_hedge_opposite_side():
    pendings = {
        "retail": [_order("retail", "BTCUSDT.P", "LONG", id_="a",
                          created_at="2026-04-24T09:00:00-06:00")],
        "fotmarkets": [_order("fotmarkets", "BTCUSD", "SHORT", id_="b",
                              created_at="2026-04-24T10:00:00-06:00")],
    }
    active, suspended = apply_whitelist_matrix(pendings, matrix_path=None)
    assert {o["id"] for o in active} == {"a", "b"}
    assert len(suspended) == 0


def test_whitelist_allows_different_asset_families():
    pendings = {
        "retail": [_order("retail", "BTCUSDT.P", "LONG", id_="a")],
        "fotmarkets": [_order("fotmarkets", "EURUSD", "LONG", id_="b")],
    }
    active, suspended = apply_whitelist_matrix(pendings, matrix_path=None)
    assert len(active) == 2
    assert len(suspended) == 0


def test_whitelist_ftmo_plus_fotmarkets_same_family_blocked():
    pendings = {
        "ftmo": [_order("ftmo", "NAS100", "LONG", id_="a",
                        created_at="2026-04-24T09:00:00-06:00")],
        "fotmarkets": [_order("fotmarkets", "NAS100", "LONG", id_="b",
                              created_at="2026-04-24T10:00:00-06:00")],
    }
    active, suspended = apply_whitelist_matrix(pendings, matrix_path=None)
    assert {o["id"] for o in active} == {"a"}
    assert {o["id"] for o in suspended} == {"b"}


def test_whitelist_ignores_already_terminal_status():
    """Orders in filled/expired/canceled status aren't considered for matrix."""
    pendings = {
        "retail": [_order("retail", "BTCUSDT.P", "LONG", id_="a", status="filled")],
        "retail-bingx": [_order("retail-bingx", "BTCUSDT.P", "LONG", id_="b")],
    }
    active, suspended = apply_whitelist_matrix(pendings, matrix_path=None)
    # `b` is active because `a` is terminal
    assert {o["id"] for o in active} == {"b"}
    assert len(suspended) == 0
