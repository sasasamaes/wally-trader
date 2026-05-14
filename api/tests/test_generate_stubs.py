"""Tests for docs/api/_generate_stubs.py."""

from __future__ import annotations

import sys
from pathlib import Path

# Add docs/api to import path so we can import _generate_stubs as a module
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "docs" / "api"))

import _generate_stubs as gs  # noqa: E402


def test_discover_routes_returns_19_v1_routes_grouped_by_tag() -> None:
    """The current API has exactly these 19 v1 routes across 6 tags."""
    routes = gs.discover_routes()
    by_tag: dict[str, list[gs.RouteInfo]] = {}
    for r in routes:
        by_tag.setdefault(r.tag, []).append(r)

    # Six tags as documented in spec
    assert set(by_tag.keys()) == {"meta", "agents", "keys", "profiles", "signals", "equity"}, (
        f"Unexpected tags: {sorted(by_tag.keys())}"
    )

    # Per-tag counts as audited in the spec
    counts = {tag: len(rs) for tag, rs in by_tag.items()}
    assert counts == {
        "meta": 2,        # GET /healthz, GET /api/v1/ping
        "agents": 3,      # GET /agents, POST /agents/{name}/run, GET /agents/runs/{run_id}
        "keys": 3,        # GET/POST/DELETE /keys/llm
        "profiles": 5,    # CRUD
        "signals": 4,     # GET list, POST, PATCH outcome, GET one
        "equity": 2,      # GET series, POST upsert
    }, f"Unexpected counts: {counts}"


def test_route_info_has_required_fields() -> None:
    routes = gs.discover_routes()
    sample = next(r for r in routes if r.path == "/api/v1/signals" and r.method == "POST")
    assert sample.tag == "signals"
    assert sample.name  # operation_id or function name
    assert sample.success_status == 201
    assert sample.requires_auth is True  # uses Depends(get_current_user)


def test_render_route_block_for_post_signals() -> None:
    """The rendered markdown block must contain the canonical AUTOGEN markers
    + a request body table + the response model + status codes + auth indicator."""
    routes = gs.discover_routes()
    post_signals = next(
        r for r in routes if r.path == "/api/v1/signals" and r.method == "POST"
    )
    md = gs.render_route_block(post_signals)

    assert "<!-- AUTOGEN:START name=POST-api-v1-signals -->" in md
    assert "<!-- AUTOGEN:END name=POST-api-v1-signals -->" in md
    assert "**Method**" in md and "POST" in md
    assert "/api/v1/signals" in md
    assert "**Auth**" in md and "X-User-Id" in md
    assert "**Status codes**" in md and "201" in md
    # Request body table must mention some required fields
    assert "profile_id" in md
    assert "symbol" in md
    assert "side" in md
    # Response model name appears
    assert "SignalView" in md
