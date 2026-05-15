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


def test_schema_type_ref() -> None:
    assert gs._schema_type({"$ref": "#/$defs/SignalSide"}) == "SignalSide"


def test_schema_type_allof_with_ref() -> None:
    assert gs._schema_type({"allOf": [{"$ref": "#/$defs/LLMProvider"}]}) == "LLMProvider"


def test_schema_type_allof_empty() -> None:
    assert gs._schema_type({"allOf": []}) == "any"


def test_schema_type_anyof_nullable() -> None:
    out = gs._schema_type({"anyOf": [{"type": "string"}, {"type": "null"}]})
    assert out == "string \\| null"


def test_schema_type_enum() -> None:
    assert gs._schema_type({"enum": ["a", "b"]}) == "enum: `a`, `b`"


def test_schema_type_array() -> None:
    assert gs._schema_type({"type": "array", "items": {"type": "string"}}) == "array<string>"


def test_schema_type_string_with_format() -> None:
    assert gs._schema_type({"type": "string", "format": "uuid"}) == "string (uuid)"


def test_schema_type_fallback_empty() -> None:
    assert gs._schema_type({}) == "any"


def test_apply_blocks_preserves_handwritten_sections(tmp_path: Path) -> None:
    """Hand-written sections OUTSIDE markers must be preserved verbatim."""
    f = tmp_path / "signals.md"
    f.write_text(
        "# Signals router\n\n"
        "## POST /api/v1/signals\n\n"
        "<!-- AUTOGEN:START name=POST-api-v1-signals -->\n"
        "OLD AUTO CONTENT\n"
        "<!-- AUTOGEN:END name=POST-api-v1-signals -->\n\n"
        "**Cuándo usar:**\n"
        "- Después de /signal CLI\n"
        "- Hand-written stuff that must survive\n"
    )

    new_block = (
        "<!-- AUTOGEN:START name=POST-api-v1-signals -->\n"
        "NEW AUTO CONTENT\n"
        "<!-- AUTOGEN:END name=POST-api-v1-signals -->"
    )
    gs.apply_blocks(f, {"POST-api-v1-signals": new_block})

    out = f.read_text()
    assert "NEW AUTO CONTENT" in out
    assert "OLD AUTO CONTENT" not in out
    assert "Hand-written stuff that must survive" in out
    assert "Después de /signal CLI" in out


def test_apply_blocks_appends_missing_endpoint_stub(tmp_path: Path) -> None:
    """If the router file has no marker for a route, append a fresh stub at the bottom
    with empty hand-write sections so the human knows to fill them in."""
    f = tmp_path / "signals.md"
    f.write_text("# Signals router\n\nExisting content.\n")

    new_block = (
        "<!-- AUTOGEN:START name=POST-api-v1-signals -->\n"
        "FRESH AUTO CONTENT\n"
        "<!-- AUTOGEN:END name=POST-api-v1-signals -->"
    )
    gs.apply_blocks(f, {"POST-api-v1-signals": new_block})

    out = f.read_text()
    assert "Existing content." in out
    assert "FRESH AUTO CONTENT" in out
    # The fresh stub must include empty hand-write sections so the writer fills them
    assert "**Cuándo usar:**" in out
    assert "**Ejemplo curl:**" in out
    assert "**Ejemplo TypeScript" in out


def test_apply_blocks_aborts_on_orphan_marker(tmp_path: Path) -> None:
    """A marker in the file with NO matching block in the dict is an orphan
    (probably an endpoint was deleted). The script must raise."""
    f = tmp_path / "signals.md"
    f.write_text(
        "<!-- AUTOGEN:START name=POST-api-v1-signals -->\n"
        "x\n"
        "<!-- AUTOGEN:END name=POST-api-v1-signals -->\n"
    )
    import pytest

    with pytest.raises(gs.OrphanBlockError) as exc:
        gs.apply_blocks(f, {})  # no blocks supplied → marker is orphaned
    assert "POST-api-v1-signals" in str(exc.value)


def test_apply_blocks_raises_on_mismatched_start_end_ids(tmp_path: Path) -> None:
    """A START with name=X paired to an END with name=Y is malformed.
    Must raise MismatchedBlockError so silent corruption can't happen."""
    f = tmp_path / "signals.md"
    f.write_text(
        "<!-- AUTOGEN:START name=POST-api-v1-signals -->\n"
        "body\n"
        "<!-- AUTOGEN:END name=GET-healthz -->\n"
    )
    import pytest

    with pytest.raises(gs.MismatchedBlockError) as exc:
        # Even passing the right block doesn't help — markers are malformed
        gs.apply_blocks(f, {"POST-api-v1-signals": "x"})
    assert "POST-api-v1-signals" in str(exc.value)


def test_main_writes_six_router_files(tmp_path: Path, monkeypatch) -> None:
    """Run main() with output redirected to a temp dir; expect 6 router files."""
    target_dir = tmp_path / "routers"
    target_dir.mkdir()
    monkeypatch.setattr(gs, "ROUTERS_DIR", target_dir)

    rc = gs.main(argv=[])  # default mode = write
    assert rc == 0

    expected = {"meta.md", "agents.md", "keys.md", "profiles.md", "signals.md", "equity.md"}
    actual = {p.name for p in target_dir.iterdir()}
    assert expected.issubset(actual), f"Missing: {expected - actual}"


def test_check_mode_returns_0_when_idempotent(tmp_path: Path, monkeypatch) -> None:
    target_dir = tmp_path / "routers"
    target_dir.mkdir()
    monkeypatch.setattr(gs, "ROUTERS_DIR", target_dir)

    assert gs.main(argv=[]) == 0
    assert gs.main(argv=["--check"]) == 0  # second run with --check: no diff


def test_check_mode_returns_1_when_diff(tmp_path: Path, monkeypatch) -> None:
    target_dir = tmp_path / "routers"
    target_dir.mkdir()
    monkeypatch.setattr(gs, "ROUTERS_DIR", target_dir)

    # Pre-write a stale signals.md missing one route
    (target_dir / "signals.md").write_text("# Stale, missing routes\n")

    assert gs.main(argv=["--check"]) == 1


def test_router_filter_writes_only_named_file(tmp_path: Path, monkeypatch) -> None:
    target_dir = tmp_path / "routers"
    target_dir.mkdir()
    monkeypatch.setattr(gs, "ROUTERS_DIR", target_dir)

    rc = gs.main(argv=["--router", "signals"])
    assert rc == 0
    files = {p.name for p in target_dir.iterdir()}
    assert files == {"signals.md"}, f"Should only have signals.md, got {files}"


def test_main_returns_4_on_mismatched_marker(tmp_path: Path, monkeypatch) -> None:
    """If a router .md file has malformed AUTOGEN markers, main returns exit code 4."""
    target_dir = tmp_path / "routers"
    target_dir.mkdir()
    monkeypatch.setattr(gs, "ROUTERS_DIR", target_dir)

    # signals.md has START with one id paired to END with a different id
    (target_dir / "signals.md").write_text(
        "<!-- AUTOGEN:START name=POST-api-v1-signals -->\n"
        "body\n"
        "<!-- AUTOGEN:END name=GET-healthz -->\n"
    )

    rc = gs.main(argv=["--router", "signals"])
    assert rc == 4
