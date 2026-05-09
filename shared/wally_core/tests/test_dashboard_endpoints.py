import pytest
import os
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Create fake profile dir
    profiles_dir = tmp_path / "profiles"
    bitunix_mem = profiles_dir / "bitunix" / "memory"
    bitunix_mem.mkdir(parents=True)
    (bitunix_mem / "signals_received.csv").write_text(
        "ts,symbol,side,entry,sl,tp,outcome,pnl_usd\n"
        "2026-05-08T12:00:00+00:00,BTC,LONG,100000,99000,102000,pending,\n"
        "2026-05-08T11:00:00+00:00,ETH,SHORT,3000,3050,2900,TP1,15.5\n"
    )
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(profiles_dir))

    # Lazy import (after env var set)
    from wally_core.dashboard_server import app
    return TestClient(app)


def test_health_endpoint(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_profiles_endpoint(client):
    r = client.get("/api/profiles")
    assert r.status_code == 200
    body = r.json()
    assert "profiles" in body
    assert any(p["name"] == "bitunix" for p in body["profiles"])


def test_profile_state_endpoint(client):
    r = client.get("/api/profile/bitunix/state")
    assert r.status_code == 200
    body = r.json()
    assert body["profile"] == "bitunix"
    assert "open_positions" in body
    assert body["n_open"] >= 1


def test_profile_state_404_on_unknown(client):
    r = client.get("/api/profile/nonexistent/state")
    assert r.status_code == 404


def test_positions_endpoint(client):
    r = client.get("/api/positions")
    assert r.status_code == 200
    body = r.json()
    assert "positions" in body
    assert "count" in body


def test_portfolio_heat_endpoint(client):
    r = client.get("/api/portfolio/heat")
    assert r.status_code == 200
    body = r.json()
    assert "total_heat_pct" in body
    assert "n_positions" in body


def test_discipline_tilt_endpoint(client):
    r = client.get("/api/discipline/tilt/bitunix")
    assert r.status_code == 200
    body = r.json()
    assert "score" in body
    assert "level" in body


def test_calibration_endpoint_no_baseline(client):
    r = client.get("/api/calibration/divergence/bitunix?window_days=30")
    assert r.status_code == 200
    body = r.json()
    # No baseline -> info field
    assert "info" in body or "severity" in body
