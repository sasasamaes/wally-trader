# API Manual + Audit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a complete Spanish manual for the 5 routers already implemented in `api/`, with curl + TypeScript examples, mapped to concrete Wally Trader scenarios. Auto-regenerate the schema sections from FastAPI introspection. Wire CI gate so the manual cannot drift.

**Architecture:** `docs/api/_generate_stubs.py` introspects `app.api.v1` via FastAPI's `app.routes`, walks each `APIRoute`, renders schema/method/status-code tables as markdown, and writes them between `<!-- AUTOGEN:START name=<id> -->` ... `<!-- AUTOGEN:END name=<id> -->` markers in the per-router `.md` files. Hand-written sections ("Cuándo usar", curl/TS examples, scenarios) sit OUTSIDE those markers and are never touched. CI runs the script in `--check` mode and fails on any diff.

**Tech Stack:** Python 3.13 + uv + FastAPI 0.115+ (via `api/pyproject.toml`), Pydantic v2 (`model_json_schema()`), pytest, GitHub Actions.

---

## File Structure

**Files created (16 new):**

```
docs/api/
├── README.md                     # entry point + quick start + index
├── MANUAL.md                     # one-table master view of 19 endpoints
├── routers/
│   ├── meta.md                   # GET /healthz, GET /api/v1/ping
│   ├── agents.md                 # 3 endpoints
│   ├── keys.md                   # 3 endpoints
│   ├── profiles.md               # 5 endpoints
│   ├── signals.md                # 4 endpoints
│   └── equity.md                 # 2 endpoints
├── SCENARIOS.md                  # 8 flujos Wally Trader → endpoints
├── CLI_TO_API.md                 # 10 slash commands → API mapping
├── AUTH.md                       # X-User-Id today + Clerk roadmap
├── ERRORS.md                     # status codes + JSON examples
└── _generate_stubs.py            # introspection + write script

api/tests/
└── test_docs_in_sync.py          # asserts the script is idempotent

.github/workflows/
└── api-docs-ci.yml               # new workflow: Python 3.13 + uv + run script --check
```

**Files modified (1):**

```
api/README.md                     # remove false claims; add roadmap section
```

---

## Task 1: Create `docs/api/` skeleton + entry README

**Files:**
- Create: `docs/api/README.md`
- Create: `docs/api/routers/.gitkeep`

- [ ] **Step 1: Create the directory and entry README**

```bash
mkdir -p docs/api/routers
touch docs/api/routers/.gitkeep
```

Then write `docs/api/README.md`:

```markdown
# Wally Trader API — Manual

Manual del backend FastAPI en `api/`. **Estado:** Phase 1 — auth via header `X-User-Id` (no Clerk JWT todavía), no exponer a internet pública.

## Quick start

```bash
cd api
uv sync
cp .env.example .env                    # rellena DATABASE_URL, MASTER_KEK
uv run alembic upgrade head
uv run uvicorn app.main:app --reload    # http://localhost:8000
```

Swagger UI: http://localhost:8000/docs (solo en dev/staging, no en producción).

## Documentación

- **[MANUAL.md](MANUAL.md)** — Tabla de los 19 endpoints implementados con 1-line "cuándo usar"
- **[routers/](routers/)** — Detalle de cada endpoint (request/response/ejemplos curl + TypeScript)
- **[SCENARIOS.md](SCENARIOS.md)** — 8 flujos típicos Wally Trader
- **[CLI_TO_API.md](CLI_TO_API.md)** — Mapeo `/comando` CLI → endpoints API
- **[AUTH.md](AUTH.md)** — Cómo funciona el header `X-User-Id` hoy
- **[ERRORS.md](ERRORS.md)** — Status codes y ejemplos de cuerpo JSON

## Mantenimiento

Las secciones marcadas `<!-- AUTOGEN:START -->` ... `<!-- AUTOGEN:END -->` se regeneran con:

```bash
python docs/api/_generate_stubs.py
```

CI corre `--check` y falla si los .md están out of sync. Si tu PR cambia un endpoint, regenera y comitea los .md también.
```

- [ ] **Step 2: Commit**

```bash
git add docs/api/README.md docs/api/routers/.gitkeep
git commit -m "docs(api): scaffold docs/api/ with entry README"
```

---

## Task 2: `_generate_stubs.py` — discover routes (TDD)

**Files:**
- Create: `docs/api/_generate_stubs.py`
- Create: `api/tests/test_generate_stubs.py`

- [ ] **Step 1: Write the failing test for route discovery**

Create `api/tests/test_generate_stubs.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd api && uv run pytest tests/test_generate_stubs.py -v
```

Expected: `ModuleNotFoundError: No module named '_generate_stubs'`

- [ ] **Step 3: Write minimal `_generate_stubs.py` with route discovery**

Create `docs/api/_generate_stubs.py`:

```python
"""Regenerate AUTOGEN sections in docs/api/routers/*.md from FastAPI introspection.

Modes:
    python docs/api/_generate_stubs.py             # write changes
    python docs/api/_generate_stubs.py --check     # exit 1 if any file would change
    python docs/api/_generate_stubs.py --router signals   # only one file

Run from repo root.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Make `app` importable without uv sync needing to install us as a package.
REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "api"
sys.path.insert(0, str(API_ROOT))

from fastapi.routing import APIRoute  # noqa: E402

from app.main import app  # noqa: E402


@dataclass
class RouteInfo:
    method: str
    path: str
    tag: str
    name: str
    summary: str
    description: str
    success_status: int
    requires_auth: bool
    request_schema: dict[str, Any] | None
    response_schema: dict[str, Any] | None
    error_responses: dict[int, str] = field(default_factory=dict)


def _route_tag(route: APIRoute) -> str:
    """Derive the tag for a route. Defaults to 'meta' if none."""
    if route.tags:
        return route.tags[0]
    return "meta"


def _route_requires_auth(route: APIRoute) -> bool:
    """True if the route depends on get_current_user."""
    for dep in route.dependant.dependencies:
        if dep.call is not None and dep.call.__name__ == "get_current_user":
            return True
    return False


def _route_success_status(route: APIRoute) -> int:
    return route.status_code or 200


def discover_routes() -> list[RouteInfo]:
    """Walk app.routes and return only the v1 + meta routes we document."""
    out: list[RouteInfo] = []
    for r in app.routes:
        if not isinstance(r, APIRoute):
            continue
        # Skip OpenAPI internals
        if r.path in {"/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"}:
            continue
        # Skip non-v1 routes EXCEPT /healthz (which is at root)
        if not r.path.startswith("/api/v1") and r.path != "/healthz":
            continue
        for method in sorted(r.methods or {"GET"}):
            if method == "HEAD":
                continue
            req_schema = None
            if r.body_field is not None:
                req_schema = r.body_field.field_info.annotation.model_json_schema()
            resp_schema = None
            if r.response_model is not None:
                # response_model can be `list[X]` etc.; try the simple case first
                model = r.response_model
                if hasattr(model, "model_json_schema"):
                    resp_schema = model.model_json_schema()
            out.append(
                RouteInfo(
                    method=method,
                    path=r.path,
                    tag=_route_tag(r),
                    name=r.name or r.unique_id,
                    summary=(r.summary or "").strip(),
                    description=(r.description or "").strip(),
                    success_status=_route_success_status(r),
                    requires_auth=_route_requires_auth(r),
                    request_schema=req_schema,
                    response_schema=resp_schema,
                    error_responses={
                        int(k): (v.get("description", "") if isinstance(v, dict) else "")
                        for k, v in (r.responses or {}).items()
                        if str(k).isdigit()
                    },
                )
            )
    return out


if __name__ == "__main__":
    routes = discover_routes()
    print(f"Discovered {len(routes)} routes:")
    for r in routes:
        print(f"  {r.method:6} {r.path}   [tag={r.tag}, auth={r.requires_auth}]")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd api && uv run pytest tests/test_generate_stubs.py -v
```

Expected: both tests PASS. If one of the route counts is wrong, that means the audit in the spec missed something — re-run `python docs/api/_generate_stubs.py` to see the actual list, update the spec + the test together, and re-commit.

- [ ] **Step 5: Commit**

```bash
git add docs/api/_generate_stubs.py api/tests/test_generate_stubs.py
git commit -m "feat(docs): _generate_stubs.py route discovery + tests"
```

---

## Task 3: `_generate_stubs.py` — render one route as markdown (TDD)

**Files:**
- Modify: `docs/api/_generate_stubs.py`
- Modify: `api/tests/test_generate_stubs.py`

- [ ] **Step 1: Write the failing test for the renderer**

Append to `api/tests/test_generate_stubs.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd api && uv run pytest tests/test_generate_stubs.py::test_render_route_block_for_post_signals -v
```

Expected: `AttributeError: module '_generate_stubs' has no attribute 'render_route_block'`

- [ ] **Step 3: Implement `render_route_block` + helpers in `_generate_stubs.py`**

Add to `docs/api/_generate_stubs.py` (above the `if __name__ == "__main__":` block):

```python
def _block_id(route: RouteInfo) -> str:
    """Stable id for the AUTOGEN block. Path slashes → dashes, leading dash dropped."""
    slug = route.path.strip("/").replace("/", "-").replace("{", "").replace("}", "")
    return f"{route.method}-{slug}"


def _render_request_table(schema: dict[str, Any] | None) -> str:
    if schema is None:
        return "_No request body._"
    props = schema.get("properties", {}) or {}
    required = set(schema.get("required", []) or [])
    if not props:
        return "_No request body._"
    rows = ["| Campo | Tipo | Required | Default | Descripción |", "|---|---|---|---|---|"]
    for name, p in props.items():
        type_str = _schema_type(p)
        req = "✓" if name in required else "—"
        default = p.get("default", "")
        if default is None:
            default = "null"
        elif default == "":
            default = "—"
        desc = p.get("description", "") or p.get("title", "")
        rows.append(f"| `{name}` | {type_str} | {req} | `{default}` | {desc} |")
    return "\n".join(rows)


def _schema_type(p: dict[str, Any]) -> str:
    """Compact type label for a JSON Schema fragment."""
    if "$ref" in p:
        return p["$ref"].split("/")[-1]
    if "anyOf" in p:
        types = [_schema_type(s) for s in p["anyOf"]]
        return " \\| ".join(types)
    if "enum" in p:
        return "enum: " + ", ".join(f"`{v}`" for v in p["enum"])
    t = p.get("type", "any")
    if t == "array":
        return f"array<{_schema_type(p.get('items', {}))}>"
    if t == "string" and p.get("format"):
        return f"string ({p['format']})"
    return t


def _response_model_name(schema: dict[str, Any] | None) -> str:
    if schema is None:
        return "_(no body)_"
    return schema.get("title", "Object")


def render_route_block(route: RouteInfo) -> str:
    """Render the AUTOGEN portion (between START/END markers) for one route."""
    bid = _block_id(route)
    auth = "Requiere `X-User-Id: <uuid>` header" if route.requires_auth else "Pública"
    statuses = [str(route.success_status)]
    for code in sorted(route.error_responses.keys()):
        statuses.append(str(code))
    statuses_str = ", ".join(statuses)
    req_table = _render_request_table(route.request_schema)
    resp_name = _response_model_name(route.response_schema)
    summary_line = f"_{route.summary}_" if route.summary else ""

    return (
        f"<!-- AUTOGEN:START name={bid} -->\n"
        f"{summary_line}\n\n"
        f"- **Method:** `{route.method}`\n"
        f"- **Path:** `{route.path}`\n"
        f"- **Auth:** {auth}\n"
        f"- **Status codes:** {statuses_str}\n\n"
        f"**Request body:**\n\n{req_table}\n\n"
        f"**Response:** `{resp_name}`\n"
        f"<!-- AUTOGEN:END name={bid} -->"
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd api && uv run pytest tests/test_generate_stubs.py::test_render_route_block_for_post_signals -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/api/_generate_stubs.py api/tests/test_generate_stubs.py
git commit -m "feat(docs): render AUTOGEN block for one route"
```

---

## Task 4: `_generate_stubs.py` — read/write per-router file with marker preservation (TDD)

**Files:**
- Modify: `docs/api/_generate_stubs.py`
- Modify: `api/tests/test_generate_stubs.py`

- [ ] **Step 1: Write the failing test for marker preservation**

Append to `api/tests/test_generate_stubs.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd api && uv run pytest tests/test_generate_stubs.py -v -k apply_blocks
```

Expected: 3 failures (`AttributeError: module has no attribute 'apply_blocks'` / `OrphanBlockError`).

- [ ] **Step 3: Implement `apply_blocks` + `OrphanBlockError` + stub appender**

Add to `docs/api/_generate_stubs.py`:

```python
import re

START_RE = re.compile(r"<!-- AUTOGEN:START name=([\w\-]+) -->")
END_RE_TPL = "<!-- AUTOGEN:END name={bid} -->"

EMPTY_HANDWRITE = """
**Cuándo usar:**
- _(rellenar — escenarios concretos Wally Trader)_

**Reglas Wally Trader que aplican:**
- _(rellenar — caps por profile, rate limits, etc.)_

**Ejemplo curl:**

```bash
# (rellenar)
```

**Ejemplo TypeScript (fetch):**

```typescript
// (rellenar)
```

**Errores típicos en este endpoint:**
- _(rellenar)_

**Ver también:**
- _(rellenar)_
"""


class OrphanBlockError(RuntimeError):
    """A file has an AUTOGEN marker for a block that no longer exists."""


def apply_blocks(path: Path, blocks: dict[str, str]) -> None:
    """Replace each AUTOGEN block in `path` with the matching string in `blocks`.

    - Existing markers whose id IS in `blocks` get replaced.
    - Markers whose id is NOT in `blocks` raise OrphanBlockError.
    - Block ids in `blocks` that are NOT in the file get appended as a fresh
      stub (with empty hand-write sections).
    """
    text = path.read_text() if path.exists() else ""
    found_ids: set[str] = set()

    def _replace(match: re.Match[str]) -> str:
        bid = match.group(1)
        found_ids.add(bid)
        if bid not in blocks:
            raise OrphanBlockError(
                f"File {path} has an AUTOGEN marker for '{bid}' but no matching "
                f"route exists. Either delete the marker + hand-written sections "
                f"below it, or restore the route."
            )
        return blocks[bid]

    # Match a full block (start + body + end) greedily-but-bounded
    block_re = re.compile(
        r"<!-- AUTOGEN:START name=([\w\-]+) -->.*?<!-- AUTOGEN:END name=\1 -->",
        re.DOTALL,
    )
    new_text = block_re.sub(_replace, text)

    # Append fresh stubs for blocks that didn't exist in the file
    missing = [bid for bid in blocks if bid not in found_ids]
    if missing:
        if not new_text.endswith("\n"):
            new_text += "\n"
        for bid in missing:
            method, _path = bid.split("-", 1)
            new_text += f"\n## `{method} /{_path.replace('-', '/')}`\n\n"
            new_text += blocks[bid] + "\n"
            new_text += EMPTY_HANDWRITE + "\n"

    path.write_text(new_text)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd api && uv run pytest tests/test_generate_stubs.py -v -k apply_blocks
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/api/_generate_stubs.py api/tests/test_generate_stubs.py
git commit -m "feat(docs): preserve hand-written sections, append stubs, detect orphans"
```

---

## Task 5: `_generate_stubs.py` — write all router files + `--check` + `--router` modes (TDD)

**Files:**
- Modify: `docs/api/_generate_stubs.py`
- Modify: `api/tests/test_generate_stubs.py`

- [ ] **Step 1: Write the failing tests**

Append to `api/tests/test_generate_stubs.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd api && uv run pytest tests/test_generate_stubs.py -v -k "main or check_mode or router_filter"
```

Expected: 4 failures (`AttributeError: module has no attribute 'main'` / `ROUTERS_DIR`).

- [ ] **Step 3: Implement `main()` + `--check` + `--router` filter**

Add to `docs/api/_generate_stubs.py`:

```python
import argparse

ROUTERS_DIR = REPO_ROOT / "docs" / "api" / "routers"


def _group_blocks_by_tag(routes: list[RouteInfo]) -> dict[str, dict[str, str]]:
    """Returns {tag: {block_id: rendered_block}}."""
    out: dict[str, dict[str, str]] = {}
    for r in routes:
        out.setdefault(r.tag, {})[_block_id(r)] = render_route_block(r)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any file would change. Does not modify files.",
    )
    parser.add_argument(
        "--router",
        help="Only regenerate the named router (e.g. 'signals').",
    )
    args = parser.parse_args(argv)

    routes = discover_routes()
    grouped = _group_blocks_by_tag(routes)

    if args.router:
        if args.router not in grouped:
            print(f"Unknown router: {args.router}. Known: {sorted(grouped)}", file=sys.stderr)
            return 2
        grouped = {args.router: grouped[args.router]}

    ROUTERS_DIR.mkdir(parents=True, exist_ok=True)

    diffs = 0
    for tag, blocks in grouped.items():
        f = ROUTERS_DIR / f"{tag}.md"
        before = f.read_text() if f.exists() else ""
        # Write to a scratch buffer first to support --check semantics
        if not f.exists():
            f.write_text(f"# {tag.capitalize()} router\n\n")
        try:
            apply_blocks(f, blocks)
        except OrphanBlockError as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return 3
        after = f.read_text()
        if before != after:
            diffs += 1
            if args.check:
                # In --check mode, restore the original
                if before:
                    f.write_text(before)
                else:
                    f.unlink(missing_ok=True)
                print(f"DRIFT: {f.relative_to(REPO_ROOT)}", file=sys.stderr)

    if args.check and diffs > 0:
        print(
            f"\n{diffs} file(s) out of sync. Run `python docs/api/_generate_stubs.py` and commit.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Replace the previous `if __name__ == "__main__":` block at the bottom with the new one above (the `main()`-based one).

- [ ] **Step 4: Run all tests to verify everything still passes**

```bash
cd api && uv run pytest tests/test_generate_stubs.py -v
```

Expected: all PASS (8 tests total: discover + render + 3 apply_blocks + 4 main).

- [ ] **Step 5: Commit**

```bash
git add docs/api/_generate_stubs.py api/tests/test_generate_stubs.py
git commit -m "feat(docs): main() with --check and --router modes"
```

---

## Task 6: Generate the 6 router files for the first time + commit auto sections

**Files:**
- Modify: `docs/api/routers/meta.md` (auto-created)
- Modify: `docs/api/routers/agents.md` (auto-created)
- Modify: `docs/api/routers/keys.md` (auto-created)
- Modify: `docs/api/routers/profiles.md` (auto-created)
- Modify: `docs/api/routers/signals.md` (auto-created)
- Modify: `docs/api/routers/equity.md` (auto-created)

- [ ] **Step 1: Run the script**

```bash
cd "$(git rev-parse --show-toplevel)"
python docs/api/_generate_stubs.py
```

Expected output (no errors):
```
(no output on success — files written to docs/api/routers/)
```

If it errors with `OrphanBlockError`, the markers are wrong — fix and re-run.
If it errors with `ImportError: app.main`, you forgot to `cd api && uv sync` first.

- [ ] **Step 2: Verify the 6 files exist and contain markers**

```bash
ls docs/api/routers/
grep -l "AUTOGEN:START" docs/api/routers/*.md | wc -l
```

Expected: `6` (one for each router).

- [ ] **Step 3: Verify the script is idempotent**

```bash
python docs/api/_generate_stubs.py --check
echo "Exit: $?"
```

Expected: `Exit: 0` (no diff after a fresh write).

- [ ] **Step 4: Commit the auto-generated stubs**

These will have the 🤖 sections filled (request tables, response model, status codes) and the ✍️ sections as `_(rellenar)_` placeholders. Subsequent tasks fill those in one router at a time.

```bash
git add docs/api/routers/
git commit -m "docs(api): generate initial AUTOGEN stubs for 6 routers"
```

---

## Task 7: Hand-fill ✍️ sections — `meta.md`

**Files:**
- Modify: `docs/api/routers/meta.md`

The 🤖 sections are already there. Replace the `_(rellenar)_` placeholders with real content. There are 2 endpoints: `GET /healthz` and `GET /api/v1/ping`.

- [ ] **Step 1: Edit `docs/api/routers/meta.md` — fill `GET /healthz`**

Replace the empty hand-write block under `GET /healthz` with:

```markdown
**Cuándo usar:**
- Liveness probe en Kubernetes / Fly.io / Render — debe responder `{"status":"ok"}` en <100ms
- Cliente quiere saber qué versión del API está corriendo (campo `version`)
- Smoke test post-deploy: `curl https://api.wallytrader.com/healthz` debe dar 200

**Reglas Wally Trader que aplican:**
- _Ninguna._ Es público y no requiere auth.

**Ejemplo curl:**

```bash
curl -s http://localhost:8000/healthz
# {"status":"ok","version":"0.1.0"}
```

**Ejemplo TypeScript (fetch):**

```typescript
const r = await fetch(`${API_URL}/healthz`);
const { status, version } = await r.json();
console.log(`API ${version} → ${status}`);
```

**Errores típicos en este endpoint:**
- `503` no lo emite el handler hoy, pero un proxy upstream puede devolverlo si el contenedor está down

**Ver también:**
- `GET /api/v1/ping` — variante v1 que confirma que el router está montado
```

- [ ] **Step 2: Edit `docs/api/routers/meta.md` — fill `GET /api/v1/ping`**

Replace the empty hand-write block under `GET /api/v1/ping`:

```markdown
**Cuándo usar:**
- Test de "el router v1 está montado y mi proxy/CORS funciona" (más específico que `/healthz`, que es root)
- Frontend lo llama al boot para confirmar conectividad antes de mostrar el dashboard

**Reglas Wally Trader que aplican:**
- _Ninguna._

**Ejemplo curl:**

```bash
curl -s http://localhost:8000/api/v1/ping
# {"pong":"ok"}
```

**Ejemplo TypeScript (fetch):**

```typescript
const ok = (await fetch(`${API_URL}/api/v1/ping`)).ok;
```

**Errores típicos en este endpoint:**
- `404` si el prefijo `/api/v1` cambió en `core/config.py` y tu cliente está hard-coded

**Ver también:**
- `GET /healthz` — root liveness
```

- [ ] **Step 3: Verify --check still passes (we only changed hand-write sections, not auto)**

```bash
python docs/api/_generate_stubs.py --check
```

Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
git add docs/api/routers/meta.md
git commit -m "docs(api): meta.md — cuándo usar /healthz + /ping"
```

---

## Task 8: Hand-fill ✍️ sections — `agents.md`

**Files:**
- Modify: `docs/api/routers/agents.md`

3 endpoints: `GET /api/v1/agents`, `POST /api/v1/agents/{name}/run` (SSE), `GET /api/v1/agents/runs/{run_id}`.

- [ ] **Step 1: Edit `agents.md` — fill `GET /api/v1/agents`**

```markdown
**Cuándo usar:**
- Frontend descubre dinámicamente qué agentes existen sin hardcodear nombres
- Antes de llamar `POST /agents/{name}/run`, validar que el nombre existe (evita 404)
- Onboarding: mostrar al usuario qué agentes tiene disponibles + qué inputs requiere cada uno

**Reglas Wally Trader que aplican:**
- 6 agentes registrados hoy: `regime`, `risk`, `signal_validator`, `multifactor`, `journal`, `sentiment`
- `requires_profile=true` significa que el endpoint `run` necesita `profile_id` en el body

**Ejemplo curl:**

```bash
curl -s -H "X-User-Id: 550e8400-e29b-41d4-a716-446655440000" \
  http://localhost:8000/api/v1/agents
# [{"name":"regime","description":"...","input_schema":{...},"requires_profile":false}, ...]
```

**Ejemplo TypeScript (fetch):**

```typescript
type AgentMeta = { name: string; description: string; input_schema: object; requires_profile: boolean };

const agents: AgentMeta[] = await (await fetch(`${API}/api/v1/agents`, {
  headers: { "X-User-Id": userId },
})).json();
```

**Errores típicos en este endpoint:**
- `401` si te falta `X-User-Id`
- Lista vacía nunca debería pasar — significa que `app.agents.AGENTS` quedó sin entradas

**Ver también:**
- `POST /api/v1/agents/{name}/run` — para correr uno
- [SCENARIOS.md#1-morning-routine](../SCENARIOS.md) — usa `regime` para detectar régimen del día
```

- [ ] **Step 2: Edit `agents.md` — fill `POST /api/v1/agents/{name}/run` (el más complejo)**

```markdown
**Cuándo usar:**
- Disparar el análisis de uno de los 6 agentes y consumir su salida en streaming (SSE)
- Reemplazo programático del slash command equivalente: `/regime`, `/risk`, `/signal`, `/multifactor`, `/journal`, `/sentiment`
- Frontend de chat o dashboard: muestra tokens en vivo a medida que el LLM los emite

**Reglas Wally Trader que aplican:**
- Requiere que el usuario tenga una LLM key registrada (`POST /keys/llm`) para el `provider` solicitado, salvo `ollama`
- Cada run consume tokens y graba un row en `agent_run` (cost_usd se calcula via `app/llm_gateway/pricing.py`)
- `profile_id` es obligatorio para agentes con `requires_profile=true` (ver `GET /api/v1/agents`)

**Eventos SSE emitidos (en orden):**

| `event` | `data.type` | Payload |
|---|---|---|
| `run_started` | `run_started` | `{"run_id": "<uuid>", "agent": "<name>"}` |
| `text` | `text` | `{"delta": "<incremental text chunk>"}` (puede llegar muchos) |
| `usage` | `usage` | `{"prompt_tokens":N, "completion_tokens":N, "cost_usd":F}` |
| `done` | `done` | `{}` (terminal exitoso) |
| `error` | `error` | `{"error": "<msg>"}` (terminal con falla) |

Guarda el `run_id` del primer evento — si el stream se corta puedes recuperar el resultado vía `GET /api/v1/agents/runs/{run_id}`.

**Ejemplo curl:**

```bash
curl -N -X POST http://localhost:8000/api/v1/agents/regime/run \
  -H "X-User-Id: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "anthropic",
    "model": "claude-sonnet-4-6",
    "input": {"symbol": "BTCUSDT", "timeframe": "1h"},
    "temperature": 0.2,
    "max_tokens": 1024
  }'
# Stream:
# event: run_started
# data: {"type":"run_started","run_id":"..."}
#
# event: text
# data: {"type":"text","delta":"Régimen actual: RANGE_CHOP..."}
# ...
# event: done
# data: {"type":"done"}
```

**Ejemplo TypeScript (fetch + SSE manual):**

```typescript
const r = await fetch(`${API}/api/v1/agents/regime/run`, {
  method: "POST",
  headers: { "X-User-Id": userId, "Content-Type": "application/json" },
  body: JSON.stringify({
    provider: "anthropic",
    model: "claude-sonnet-4-6",
    input: { symbol: "BTCUSDT", timeframe: "1h" },
  }),
});
const reader = r.body!.getReader();
const decoder = new TextDecoder();
let runId: string | undefined;
let buffer = "";
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  for (const line of buffer.split("\n\n")) {
    if (!line.startsWith("data: ")) continue;
    const event = JSON.parse(line.slice(6));
    if (event.type === "run_started") runId = event.run_id;
    if (event.type === "text") process.stdout.write(event.delta);
    if (event.type === "done") return;
    if (event.type === "error") throw new Error(event.error);
  }
  buffer = buffer.endsWith("\n\n") ? "" : buffer;
}
```

**Errores típicos en este endpoint:**
- `404` "Unknown agent '<name>'" — typo o agente no registrado
- `400` "Invalid profile_id" — el UUID está mal formado
- `400` "Invalid provider" — provider no es `anthropic` / `openai` / `google` / `ollama`
- Evento `error` mid-stream — la API key del provider falló (`401` upstream) o se acabó la cuota

**Ver también:**
- `GET /api/v1/agents/runs/{run_id}` — recupera resultado si el SSE se cortó
- `POST /api/v1/keys/llm` — debes registrar la key del provider primero
- [SCENARIOS.md#2-validar-señal-discord](../SCENARIOS.md)
```

- [ ] **Step 3: Edit `agents.md` — fill `GET /api/v1/agents/runs/{run_id}`**

```markdown
**Cuándo usar:**
- El SSE de un run anterior se cortó (red inestable, navegador cerrado) — recupera el resultado completo
- Auditoría: revisar qué se le pidió a un agente, cuánto costó, cuánto duró
- Replay para debugging: ¿por qué el agente devolvió X output con Y input?

**Reglas Wally Trader que aplican:**
- Solo retorna runs del usuario actual (filtra por `user_id`)
- `output_md` es el markdown final concatenado; `error` está populado si terminó en `error`

**Ejemplo curl:**

```bash
curl -s -H "X-User-Id: 550e8400-..." \
  http://localhost:8000/api/v1/agents/runs/9f8b... | jq
# {
#   "id": "9f8b...",
#   "agent_name": "regime",
#   "status": "completed",
#   "provider": "anthropic",
#   "model": "claude-sonnet-4-6",
#   "prompt_tokens": 421,
#   "completion_tokens": 87,
#   "cost_usd": 0.00138,
#   "duration_ms": 2104,
#   "output_md": "Régimen: RANGE_CHOP...",
#   "error": null
# }
```

**Ejemplo TypeScript (fetch):**

```typescript
type AgentRunSummary = { id: string; agent_name: string; status: string; output_md: string | null; cost_usd: number | null };
const run: AgentRunSummary = await (await fetch(`${API}/api/v1/agents/runs/${runId}`, {
  headers: { "X-User-Id": userId },
})).json();
```

**Errores típicos en este endpoint:**
- `400` "Invalid run_id" — UUID mal formado
- `404` "Run not found" — el run no existe O pertenece a otro usuario

**Ver también:**
- `POST /api/v1/agents/{name}/run` — para crear runs nuevos
```

- [ ] **Step 4: Verify --check still passes**

```bash
python docs/api/_generate_stubs.py --check
```

- [ ] **Step 5: Commit**

```bash
git add docs/api/routers/agents.md
git commit -m "docs(api): agents.md — cuándo usar + SSE event reference"
```

---

## Task 9: Hand-fill ✍️ sections — `keys.md`

**Files:**
- Modify: `docs/api/routers/keys.md`

3 endpoints: `GET /keys/llm`, `POST /keys/llm`, `DELETE /keys/llm/{key_id}`.

- [ ] **Step 1: Fill `GET /keys/llm`**

```markdown
**Cuándo usar:**
- Mostrar en frontend qué providers tiene configurados el usuario (Anthropic, OpenAI, Google, Ollama)
- Antes de un agente run, verificar que existe la key del provider que vas a usar
- Settings page: lista con `last4` para que el usuario identifique cada key sin exponer el secret

**Reglas Wally Trader que aplican:**
- Las keys se guardan encriptadas con AES-256-GCM en `app/security/encryption.py`
- Solo retorna `last4` + label + timestamps — nunca plaintext
- 1 key por provider por usuario (POST nuevo sobreescribe)

**Ejemplo curl:**

```bash
curl -s -H "X-User-Id: 550e8400-..." http://localhost:8000/api/v1/keys/llm
# [{"id":"...","provider":"anthropic","last4":"abcd","label":"prod","created_at":"...","last_used":"..."}]
```

**Ejemplo TypeScript (fetch):**

```typescript
type LLMKey = { id: string; provider: "anthropic" | "openai" | "google" | "ollama"; last4: string; label: string | null };
const keys: LLMKey[] = await (await fetch(`${API}/api/v1/keys/llm`, { headers: { "X-User-Id": userId } })).json();
```

**Errores típicos:**
- `401` si falta `X-User-Id`

**Ver también:**
- `POST /keys/llm` para registrar
- `POST /agents/{name}/run` consume estas keys
```

- [ ] **Step 2: Fill `POST /keys/llm`**

```markdown
**Cuándo usar:**
- Onboarding: el usuario pega su API key de Anthropic / OpenAI / Google
- Rotación de keys (sobreescribe la existente del mismo provider)

**Reglas Wally Trader que aplican:**
- BYOK (Bring Your Own Key) — el SaaS no provee keys, el usuario paga su propia cuota LLM
- La plaintext key NUNCA se devuelve después de POST — solo `last4`. Guárdala fuera del API si la necesitas
- Encripción a nivel application via DEK/KEK (`MASTER_KEK` env var)

**Ejemplo curl:**

```bash
curl -X POST http://localhost:8000/api/v1/keys/llm \
  -H "X-User-Id: 550e8400-..." \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "anthropic",
    "api_key": "sk-ant-api03-...",
    "label": "prod"
  }'
# 201 Created → {"id":"...","provider":"anthropic","last4":"....","label":"prod",...}
```

**Ejemplo TypeScript (fetch):**

```typescript
const created = await fetch(`${API}/api/v1/keys/llm`, {
  method: "POST",
  headers: { "X-User-Id": userId, "Content-Type": "application/json" },
  body: JSON.stringify({ provider: "anthropic", api_key, label: "prod" }),
});
```

**Errores típicos:**
- `400` con mensaje de `KeyServiceError` — formato de key inválido para el provider

**Ver también:**
- `DELETE /keys/llm/{key_id}` para borrar
```

- [ ] **Step 3: Fill `DELETE /keys/llm/{key_id}`**

```markdown
**Cuándo usar:**
- Usuario rotó la key fuera del provider y quiere limpiar la vieja
- Cancelación de cuenta — borrar todas las keys antes de eliminar al usuario

**Reglas Wally Trader que aplican:**
- Solo borra keys del usuario actual (filtra por `user_id`)

**Ejemplo curl:**

```bash
curl -X DELETE -H "X-User-Id: 550e8400-..." \
  http://localhost:8000/api/v1/keys/llm/9f8b...
# 204 No Content
```

**Ejemplo TypeScript:**

```typescript
await fetch(`${API}/api/v1/keys/llm/${keyId}`, { method: "DELETE", headers: { "X-User-Id": userId } });
```

**Errores típicos:**
- `400` "Invalid key_id" — UUID mal formado
- `404` "Key not found" — la key no existe o no es del usuario actual

**Ver también:**
- `GET /keys/llm` para listar IDs
```

- [ ] **Step 4: Verify + commit**

```bash
python docs/api/_generate_stubs.py --check
git add docs/api/routers/keys.md
git commit -m "docs(api): keys.md — BYOK lifecycle + 4 providers"
```

---

## Task 10: Hand-fill ✍️ sections — `profiles.md`

**Files:**
- Modify: `docs/api/routers/profiles.md`

5 endpoints. Slug-based addressing (`{slug}` not `{id}`) is the unusual bit. Use the EXACT template from Task 9 (keys.md) — six labeled sections per endpoint, no improvisation.

**Reusable per-endpoint template** (copy this block 5 times, customize the bracketed bits):

```markdown
**Cuándo usar:**
- [bullet 1]
- [bullet 2]

**Reglas Wally Trader que aplican:**
- [rule 1]
- [rule 2]

**Ejemplo curl:**

```bash
[curl command with X-User-Id header]
```

**Ejemplo TypeScript (fetch):**

```typescript
[typed fetch call]
```

**Errores típicos en este endpoint:**
- `XXX` [reason]

**Ver también:**
- [related endpoint or scenario]
```

- [ ] **Step 1: Fill `GET /profiles`**

Customize the template with:
- Cuándo usar: dashboard multi-profile (`include_metrics=true`); statusline refresh
- Reglas: cross-profile guard (max 1 profile haciendo BTC simultáneo, frontend muestra warning); `include_metrics=true` corre `compute_signal_stats` por profile (puede ser lento con muchas signals)
- Curl: `curl -s -H "X-User-Id: $USER_ID" "http://localhost:8000/api/v1/profiles?include_metrics=true"`
- TS: typed `Profile[]` con `kind: "retail" | "retail_bingx" | "ftmo" | "fundingpips" | "fotmarkets" | "bitunix" | "quantfury"` y campo opcional `metrics`
- Errores: `401` si falta header; `500` si DB no disponible
- Ver también: `GET /profiles/{slug}` para uno solo, `POST /profiles` para crear

- [ ] **Step 2: Fill `POST /profiles`**

Customize with:
- Cuándo usar: onboarding inicial (crear los 7 profiles del usuario); migrar usuario de CLI al SaaS
- Reglas: `kind` debe ser uno de los 7 valores del enum `ProfileKind` (retail, retail_bingx, ftmo, fundingpips, fotmarkets, bitunix, quantfury); `slug` es único por usuario (no global); `capital_initial` se copia automáticamente a `capital_current` en POST
- Curl: POST con body `{"slug":"retail","name":"Binance Main","kind":"retail","capital_initial":18.09,"currency":"USD","config_json":{...},"strategy_json":{...},"rules_json":{...}}`
- TS: typed body con enum `ProfileKind`
- Errores: `409 Conflict` si slug ya existe; `422` si kind no está en el enum
- Ver también: `PATCH /profiles/{slug}` para update; `DELETE` para eliminar

- [ ] **Step 3: Fill `GET /profiles/{slug}`**

Customize with:
- Cuándo usar: pantalla de detalle de un profile; click "ver más" desde dashboard; `/status` CLI equivalent
- Reglas: slug es human-readable (`retail`, `bitunix`, `ftmo`...) — usar slug en URLs en vez de UUID; siempre devuelve `metrics` populado (no es opcional aquí, a diferencia de `GET /profiles`)
- Curl: `curl -s -H "X-User-Id: $USER_ID" http://localhost:8000/api/v1/profiles/bitunix`
- TS: typed return como `ProfileWithMetrics`
- Errores: `404 Profile not found` (no existe O es de otro usuario)
- Ver también: `PATCH` para update de campos mutables

- [ ] **Step 4: Fill `PATCH /profiles/{slug}`**

Customize with:
- Cuándo usar: ajustar capital_current manualmente (ej. después de retiro); cambiar config_json/strategy_json/rules_json en runtime sin redeploy
- Reglas: solo 5 campos son mutables: `name`, `capital_current`, `config_json`, `strategy_json`, `rules_json`. `kind`, `slug`, `capital_initial`, `currency` son inmutables (cambiarlos requiere recrear el profile)
- Curl: `curl -X PATCH -H "X-User-Id: $USER_ID" -H "Content-Type: application/json" -d '{"capital_current": 22.50}' http://localhost:8000/api/v1/profiles/retail`
- TS: typed body con `Partial<{name, capital_current, config_json, strategy_json, rules_json}>`
- Errores: `404` si slug no existe para el usuario; los campos inmutables se ignoran silenciosamente (no hay error pero tampoco update — TODO mejorar a `400` en sub-proyecto futuro)
- Ver también: `POST /equity/upsert` para tracking diario en vez de PATCH manual

- [ ] **Step 5: Fill `DELETE /profiles/{slug}`**

Customize with:
- Cuándo usar: usuario abandona un challenge (FTMO, FundingPips); cierre definitivo de cuenta retail; cleanup de profile de prueba
- Reglas: cascade delete — destruye `signals` + `equity_points` asociados (foreign key ON DELETE CASCADE en SQLAlchemy models, verificar en `app/models/profile.py` `relationships`). Operación irreversible — el frontend DEBE confirmar dos veces
- Curl: `curl -X DELETE -H "X-User-Id: $USER_ID" http://localhost:8000/api/v1/profiles/test-profile`
- TS: `await fetch(..., {method: "DELETE", headers: {...}})`
- Errores: `404` si slug no existe
- Ver también: si solo querés "pausar" sin destruir history, usá `PATCH` y agrega `config_json.paused=true` (convención frontend-side)

- [ ] **Step 6: Verify + commit**

```bash
python docs/api/_generate_stubs.py --check
git add docs/api/routers/profiles.md
git commit -m "docs(api): profiles.md — 7 kinds + slug addressing + cascade rules"
```

---

## Task 11: Hand-fill ✍️ sections — `signals.md`

**Files:**
- Modify: `docs/api/routers/signals.md`

4 endpoints. Most-used router — spend extra care. Use cases come straight from `signals_received.md` workflows. Apply the same template as Task 10 (six labeled sections per endpoint, no improvisation).

**Endpoint-specific hints to drive the bullets:**

- [ ] **Step 1: Fill `GET /signals`**
  - Cuándo usar: dashboard "history" page; pre-flight check antes de POST (verificar count<7 hoy en bitunix); export CSV; review semanal `/review`
  - Filters disponibles: `profile_id` (required), `symbol`, `side`, `outcome`, `from_date`, `to_date`, `limit` (default 200, max 1000), `offset`
  - Reglas: `stats` siempre se agrega (no opcional) — devuelve total, open, closed, wins, losses, win_rate_pct, avg_win/loss_usd, profit_factor (None si no hay losses)
  - Curl: `curl -s -H "X-User-Id: $USER_ID" "http://localhost:8000/api/v1/signals?profile_id=<UUID>&from_date=2026-05-01&outcome=tp1"`
  - TS: typed `SignalList` con `signals: SignalView[]`, `stats: SignalStats`, `total: number`
  - Errores: `400 Invalid profile_id`; `404 Profile not found`
  - Ver también: `POST /signals` para crear; SCENARIOS.md#5-dashboard

- [ ] **Step 2: Fill `POST /signals`**
  - Use el bloque concreto de ejemplo abajo (sample completo dado más abajo)

- [ ] **Step 3: Fill `PATCH /signals/{id}/outcome`**
  - Cuándo usar: trade cerrado en exchange (TP/SL hit, manual close); comando `/log-outcome SYMBOL TP1 EXIT_PRICE`; reconciliación retroactiva
  - Reglas: side-effect importante — auto-actualiza `profile.capital_current` con `+= pnl_usd`. Si pasás `pnl_usd` mal, el capital queda corrupto y necesitás `PATCH /profiles/{slug}` para corregirlo. Outcomes válidos: `win`, `loss`, `breakeven`, `tp1`, `tp2`, `tp3`, `manual`
  - Curl: `curl -X PATCH -H "X-User-Id: $USER_ID" -H "Content-Type: application/json" -d '{"outcome":"tp1","exit_price":68900,"exit_reason":"TP1 hit","pnl_usd":1.45,"duration_h":2.3,"learning":"Limpio, RSI confirmó la zona"}' http://localhost:8000/api/v1/signals/<UUID>/outcome`
  - TS: typed body, validar que `outcome ∈ SignalOutcome` antes de enviar
  - Errores: `400 Invalid signal_id`; `404 Signal not found` (no existe O es de otro usuario via profile join)
  - Ver también: `POST /agents/journal/run` después de cerrar para generar markdown del día

- [ ] **Step 4: Fill `GET /signals/{id}`**
  - Cuándo usar: deep-link compartible al detalle de una signal (frontend route `/signals/:id`); review post-cierre para ver scores originales vs outcome
  - Reglas: user-scope vía join con `profiles.user_id` (no expone signals de otros usuarios)
  - Curl: `curl -s -H "X-User-Id: $USER_ID" http://localhost:8000/api/v1/signals/<UUID>`
  - TS: typed return `SignalView`
  - Errores: `400 Invalid signal_id`; `404 Signal not found`
  - Ver también: `PATCH /signals/{id}/outcome` para cerrar

**Sample para `POST /signals` (Step 2 — usar este bloque tal cual):**

```markdown
**Cuándo usar:**
- Después de `/signal SYMBOL SIDE entry sl=X tp=Y` en CLI (auto-log via pipeline bitunix)
- Cuando recibes call en Discord punkchainer's y quieres trackearla
- Cuando `/punk-hunt` autohunt encontró setup propio (score≥70) y debes loggearlo
- Cuando ejecutaste trade manual en Bitunix UI y quieres registro retroactivo

**Reglas Wally Trader que aplican:**
- Profile bitunix: max 7 signals/día — antes de POST consulta `GET /signals?profile_id=X&from_date=<today>` y verifica count<7
- Profile retail: leverage cap 10x; bitunix: 20x; ftmo: profile-rule específico
- Profile bitunix: max 2 signals concurrentes con `outcome=pending`
- Si `multifactor_score<50` Y `ml_score<55` el frontend debe mostrar warning "low confluence"

**Ejemplo curl:**

```bash
curl -X POST http://localhost:8000/api/v1/signals \
  -H "X-User-Id: 550e8400-..." \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "f7e6...",
    "symbol": "BTCUSDT",
    "side": "long",
    "entry": 67500,
    "sl": 66800,
    "tp1": 68900,
    "tp2": 70200,
    "leverage": 20,
    "source": "punkchainer_discord",
    "multifactor_score": 72.4,
    "ml_score": 68.1,
    "regime": "RANGE_CHOP",
    "filters_4_count": 4,
    "pillars_4_count": 3,
    "saturday": false
  }'
# 201 Created → SignalView with id + opened_at + outcome="pending"
```

**Ejemplo TypeScript (fetch):**

```typescript
const signal = await fetch(`${API}/api/v1/signals`, {
  method: "POST",
  headers: { "X-User-Id": userId, "Content-Type": "application/json" },
  body: JSON.stringify({
    profile_id, symbol: "BTCUSDT", side: "long",
    entry: 67500, sl: 66800, tp1: 68900,
    leverage: 20, source: "punkchainer_discord",
    multifactor_score: 72.4, ml_score: 68.1,
  }),
});
```

**Errores típicos:**
- `400` "Invalid profile_id"
- `404` "Profile not found" — el profile_id no es del usuario actual
- `422` Pydantic — leverage>125, side no es long/short, entry<=0

**Ver también:**
- `PATCH /signals/{id}/outcome` para cerrar
- [SCENARIOS.md#2-validar-señal-discord](../SCENARIOS.md)
```

- [ ] **Step 5: Verify + commit**

```bash
python docs/api/_generate_stubs.py --check
git add docs/api/routers/signals.md
git commit -m "docs(api): signals.md — full lifecycle + bitunix rules + examples"
```

---

## Task 12: Hand-fill ✍️ sections — `equity.md`

**Files:**
- Modify: `docs/api/routers/equity.md`

2 endpoints. Same template as Tasks 10/11 (six labeled sections).

- [ ] **Step 1: Fill `GET /equity`**
  - Cuándo usar: chart de equity en frontend (área plot); export para review semanal/mensual; comparar curva vs HODL en profile quantfury (campo `outperformance_vs_hodl_pct`)
  - Reglas: filtra por `profile_id` (required) + opcional `from_date`/`to_date` (date, no datetime). `summary` siempre se calcula con `compute_equity_summary` — incluye total_return_pct, max_dd_pct, days_count
  - Curl: `curl -s -H "X-User-Id: $USER_ID" "http://localhost:8000/api/v1/equity?profile_id=<UUID>&from_date=2026-04-01"`
  - TS: typed `EquitySeriesResponse` con `points: EquityPointView[]` y `summary`
  - Errores: `400 Invalid profile_id`; `404 Profile not found`
  - Ver también: `POST /equity/upsert` para registrar puntos

- [ ] **Step 2: Fill `POST /equity/upsert`**
  - Cuándo usar: cierre diario operador FTMO/FundingPips (anota balance MT5); comando CLI `/equity <value>`; backfill histórico de un período offline
  - Reglas: side-effect — si la fecha del upsert es la MÁS RECIENTE registrada, auto-actualiza `profile.capital_current = body.equity`. Si es fecha anterior, NO toca capital_current (solo guarda el punto histórico). Idempotente sobre `(profile_id, date)` — POST repetido sobre la misma fecha sobreescribe
  - Curl: `curl -X POST -H "X-User-Id: $USER_ID" -H "Content-Type: application/json" -d '{"profile_id":"<UUID>","date":"2026-05-13","equity":18.45,"daily_pnl_pct":1.99,"dd_pct":-0.5,"win_rate_pct":71.4,"trade_count":3}' http://localhost:8000/api/v1/equity/upsert`
  - TS: typed body con `EquityPointUpsert`
  - Errores: `400 Invalid profile_id`; `404 Profile not found`; `409 Conflict` (raro — race condition entre dos POSTs simultáneos)
  - Ver también: `GET /equity` para series; `PATCH /profiles/{slug}` si solo querés actualizar capital sin grabar punto histórico

- [ ] **Step 3: Verify + commit**

```bash
python docs/api/_generate_stubs.py --check
git add docs/api/routers/equity.md
git commit -m "docs(api): equity.md — manual daily close + chart series"
```

---

## Task 13: Write `MANUAL.md` — master one-table view

**Files:**
- Create: `docs/api/MANUAL.md`

- [ ] **Step 1: Create the file**

```markdown
# Wally Trader API — Tabla maestra

19 endpoints implementados (Phase 1, requires `X-User-Id` header excepto donde se indica).

| Método | Path | Cuándo usar (1-line) | Detalle |
|---|---|---|---|
| GET | `/healthz` | Liveness probe + version check (público) | [meta.md](routers/meta.md) |
| GET | `/api/v1/ping` | Test "router v1 montado + CORS ok" (público) | [meta.md](routers/meta.md) |
| GET | `/api/v1/agents` | Listar los 6 agentes registrados + sus input schemas | [agents.md](routers/agents.md) |
| POST | `/api/v1/agents/{name}/run` | Correr un agente y consumir output via SSE streaming | [agents.md](routers/agents.md) |
| GET | `/api/v1/agents/runs/{run_id}` | Recuperar resultado de un run anterior (si SSE se cortó) | [agents.md](routers/agents.md) |
| GET | `/api/v1/keys/llm` | Listar LLM keys del usuario (last4 + provider) | [keys.md](routers/keys.md) |
| POST | `/api/v1/keys/llm` | Registrar/rotar una API key (BYOK encriptada) | [keys.md](routers/keys.md) |
| DELETE | `/api/v1/keys/llm/{key_id}` | Borrar una LLM key | [keys.md](routers/keys.md) |
| GET | `/api/v1/profiles` | Listar profiles del usuario + métricas opcionales | [profiles.md](routers/profiles.md) |
| POST | `/api/v1/profiles` | Crear profile (kind: retail / ftmo / bitunix / etc.) | [profiles.md](routers/profiles.md) |
| GET | `/api/v1/profiles/{slug}` | Detalle de un profile + métricas | [profiles.md](routers/profiles.md) |
| PATCH | `/api/v1/profiles/{slug}` | Update parcial (capital_current, config_json, etc.) | [profiles.md](routers/profiles.md) |
| DELETE | `/api/v1/profiles/{slug}` | Eliminar profile (cascade signals + equity) | [profiles.md](routers/profiles.md) |
| GET | `/api/v1/signals` | Listar signals + stats agregadas (filtros) | [signals.md](routers/signals.md) |
| POST | `/api/v1/signals` | Crear signal (después de /signal CLI o call Discord) | [signals.md](routers/signals.md) |
| PATCH | `/api/v1/signals/{id}/outcome` | Cerrar signal con outcome + pnl (auto-update capital) | [signals.md](routers/signals.md) |
| GET | `/api/v1/signals/{id}` | Detalle de una signal | [signals.md](routers/signals.md) |
| GET | `/api/v1/equity` | Series de equity (chart) + summary (max DD, total return) | [equity.md](routers/equity.md) |
| POST | `/api/v1/equity/upsert` | Upsert manual diario (FTMO/FundingPips operador) | [equity.md](routers/equity.md) |

## Modelos huérfanos (en DB pero sin endpoint todavía)

| Modelo | Archivo | Sub-proyecto futuro |
|---|---|---|
| `Subscription` | `app/models/subscription.py` | #4 Billing (Polar.sh) |
| `UsageEvent` | `app/models/usage_event.py` | #4 Billing |
| `AuditLog` | `app/models/audit_log.py` | #5 Audit |
| `TradeBrokerSync` | `app/models/trade_broker_sync.py` | #2 Brokers |
| `JournalEntry` | `app/models/journal_entry.py` | TBD — ver spec del API manual |

## Roadmap (no implementado todavía)

- **#1 Auth** — Clerk + JWT + multi-tenant guards (reemplaza `X-User-Id` stub)
- **#2 Brokers** — Bitunix / Binance / MT5 keys + sync de trades
- **#3 WebSockets** — fanout via Redis pubsub para `signal.created`, `agent.run.token`, etc.
- **#4 Billing** — Polar.sh checkout + portal + metered usage
- **#5 Audit + RL + observability** — `AuditLog`, rate limiting, Sentry
```

- [ ] **Step 2: Commit**

```bash
git add docs/api/MANUAL.md
git commit -m "docs(api): MANUAL.md tabla maestra de 19 endpoints"
```

---

## Task 14: Write `SCENARIOS.md` — 8 flujos Wally Trader

**Files:**
- Create: `docs/api/SCENARIOS.md`

- [ ] **Step 1: Create with all 8 scenarios from the spec**

```markdown
# Escenarios — Wally Trader API

8 flujos típicos del proyecto. Cada uno orquesta varios endpoints. Si vas a construir un frontend, piensa estos casos como "vistas" antes que como "endpoints".

## 1. Morning routine multi-profile

**Trigger:** CR 06:00, el usuario abre el dashboard.

**Pipeline:**
1. `GET /api/v1/profiles?include_metrics=true` — todos los profiles activos con su capital, WR, PF, total PnL
2. Por cada profile: `GET /api/v1/equity?profile_id=<id>&from_date=<today-7d>` — gráfico semanal
3. `POST /api/v1/agents/regime/run` con `input={"symbol": "BTCUSDT", "timeframe": "1h"}` para el activo principal del día
4. (Opcional) `POST /api/v1/agents/sentiment/run` con `input={"asset": "BTC"}` para Fear & Greed + funding bias

**Reglas obligatorias:**
- Si algún profile tiene `daily_pnl_pct <= -2%`, mostrar warning "near daily BLOCK"
- Si más de 1 profile tiene trade BTC abierto hoy, mostrar warning "cross-asset exclusion"

**TypeScript snippet:**

```typescript
const profiles = await fetchJSON<ProfileList>(`${API}/profiles?include_metrics=true`);
const equityByProfile = await Promise.all(
  profiles.profiles.map(p =>
    fetchJSON<EquitySeries>(`${API}/equity?profile_id=${p.id}&from_date=${weekAgo}`)
  )
);
const regime = await streamAgent("regime", { symbol: "BTCUSDT", timeframe: "1h" });
```

---

## 2. Validar señal Discord punkchainer's (bitunix)

**Trigger:** Llega call en Discord. Profile=bitunix.

**Pipeline:**
1. `GET /api/v1/profiles/bitunix` — confirmar `capital_current` + `config_json.leverage_cap`
2. `GET /api/v1/signals?profile_id=<bitunix>&from_date=<today>` — verificar count<7 (bitunix max 7/día)
3. `POST /api/v1/agents/signal_validator/run` con el body de la call (symbol, side, entry, sl, tp, leverage)
4. Consumir SSE; si stream emite verdict=GO y score≥60:
5. `POST /api/v1/signals` con `source="punkchainer_discord"` + scores extraídos del agent
6. Operador ejecuta trade manual en Bitunix UI (no automatizado en Phase 1)
7. Cuando cierra: `PATCH /api/v1/signals/{id}/outcome`

**Reglas obligatorias antes del paso 5:**
- count<7 hoy, count<2 concurrentes con outcome=pending
- daily_pnl > -6% (BLOCK threshold)
- leverage <= 20x (cap bitunix)

---

## 3. Autohunt: cazar setup propio (bitunix)

**Trigger:** `/punk-hunt` corre o el usuario clickea "Hunt" en frontend.

**Pipeline:**
1. Para cada uno de los 24 assets del watchlist bitunix:
   - `POST /api/v1/agents/regime/run` con `input={"symbol": <asset>}`
2. Filtrar assets con régimen `RANGE_CHOP` o `TREND_LEVE`
3. Para los que pasan: `POST /api/v1/agents/multifactor/run`
4. Top 1 por score: si score≥70 → `POST /api/v1/signals` con `source="self_generated"`
5. Notificar al usuario (push / email / Discord)

**Reglas:**
- Max 1 self-generated signal por hora (evita oversignaling)
- Aplican las mismas reglas de límite que en escenario 2

---

## 4. Cerrar trade y journal (cualquier profile)

**Trigger:** Trade cerrado en exchange / fin del día.

**Pipeline:**
1. `PATCH /api/v1/signals/{id}/outcome` con outcome (`tp1`/`tp2`/`tp3`/`win`/`loss`/`breakeven`/`manual`) + `exit_price` + `pnl_usd` + `learning`
2. `POST /api/v1/agents/journal/run` con `input={"profile_id": <id>, "date": <today>}` — genera markdown del día
3. Mostrar el `output_md` al usuario, opcionalmente guardar en `JournalEntry` (no hay endpoint todavía)
4. `POST /api/v1/equity/upsert` con `equity` actualizado, `daily_pnl_pct`, `dd_pct`, `trade_count`

---

## 5. Dashboard multi-profile (frontend)

**Trigger:** Usuario abre la app, ya autenticado.

**Pipeline:**
1. `GET /api/v1/profiles?include_metrics=true` (server-side render o SWR)
2. Por cada profile mostrar tarjeta: capital, WR, PF, PnL día (delta vs ayer), max DD
3. Sparkline: `GET /api/v1/equity?profile_id=<id>&from_date=<today-30d>`
4. Botón "Hunt" → escenario 3; botón "Journal" → escenario 4

---

## 6. Gestionar LLM keys (BYOK setup inicial)

**Trigger:** Usuario nuevo en `/settings/keys`.

**Pipeline:**
1. `GET /api/v1/keys/llm` — ver qué providers ya configurados
2. Para cada provider faltante (anthropic, openai, google, ollama opcional):
   - `POST /api/v1/keys/llm` con `{provider, api_key, label}`
3. Test post-setup: `POST /api/v1/agents/regime/run` con un input mínimo para validar que la key funciona
4. Rotación: `DELETE /api/v1/keys/llm/{id}` + `POST /api/v1/keys/llm` con la nueva

---

## 7. Recuperar agent run histórico

**Trigger:** El SSE de un run anterior se cortó (cliente desconectado, navegador cerrado).

**Pipeline:**
1. El cliente debe haber guardado el `run_id` que llegó en el primer evento `run_started`
2. `GET /api/v1/agents/runs/{run_id}` — devuelve el output completo + cost + tokens + status
3. Si `status=running`, polling cada 2s hasta `completed` o `failed`

---

## 8. Equity tracking manual (FTMO / FundingPips)

**Trigger:** Operador cierra el día y quiere registrar el balance MT5.

**Pipeline:**
1. Operador anota balance MT5 al cierre + PnL día + drawdown
2. `POST /api/v1/equity/upsert` con `{profile_id, date, equity, daily_pnl_pct, dd_pct, trade_count}`
3. El endpoint auto-mirror a `profile.capital_current` si la fecha es la última registrada
4. (Futuro #2) Cuando el broker bridge esté wired, este flow se automatiza
```

- [ ] **Step 2: Commit**

```bash
git add docs/api/SCENARIOS.md
git commit -m "docs(api): SCENARIOS.md — 8 flujos Wally Trader → endpoints"
```

---

## Task 15: Write `CLI_TO_API.md` — slash command mapping

**Files:**
- Create: `docs/api/CLI_TO_API.md`

- [ ] **Step 1: Create the mapping table**

```markdown
# CLI → API equivalencias

Mapeo de los slash commands más usados a sus equivalentes API. Útil si quieres replicar el workflow CLI desde frontend o un script externo.

| CLI command | API equivalente | Notas |
|---|---|---|
| `/signal SYMBOL SIDE entry sl=X tp=Y` | 1. `POST /api/v1/agents/signal_validator/run` (SSE)<br>2. Si verdict=GO: `POST /api/v1/signals` con scores extraídos | El signal_validator agent corre los 4 filtros + multifactor + ML score |
| `/journal` | 1. `POST /api/v1/agents/journal/run` con `{profile_id, date}`<br>2. `POST /api/v1/equity/upsert` con balance del día | Genera markdown + actualiza equity en una sola sesión |
| `/risk SIDE entry sl` | `POST /api/v1/agents/risk/run` con `{side, entry, sl, profile_id}` | Pure compute, no escribe DB |
| `/punk-hunt` | Ver [SCENARIOS.md#3-autohunt](SCENARIOS.md) — orquesta `regime` + `multifactor` + `signals POST` | Loop sobre 24 assets watchlist bitunix |
| `/punk-watch` | _Sin equivalente API en Phase 1_ | El watch path dibuja en TradingView local — necesita TV MCP, no expuesto vía HTTP |
| `/regime` | `POST /api/v1/agents/regime/run` con `{symbol, timeframe}` | Default `BTCUSDT` 1H |
| `/multifactor` | `POST /api/v1/agents/multifactor/run` con `{symbol, side}` | Devuelve score 0-100 |
| `/sentiment` | `POST /api/v1/agents/sentiment/run` con `{asset}` | F&G + Reddit VADER + News + Funding |
| `/status` | 1. `GET /api/v1/profiles?include_metrics=true`<br>2. `GET /api/v1/equity?profile_id=<active>&from_date=<today>` | Equivalente al statusline multi-profile |
| `/equity <value>` | `POST /api/v1/equity/upsert` con `{profile_id, date: today, equity: <value>}` | Auto-mirror a `profile.capital_current` |

## Comandos CLI sin equivalente API hoy (Phase 1)

Estos comandos dependen de side-effects locales (TradingView MCP, archivos en `.claude/cache/`) y no están expuestos vía HTTP:

- `/punk-watch`, `/chart`, `/levels`, `/alert` — escriben/leen TradingView Desktop via MCP
- `/morning`, `/punk-morning` — agregan WebFetch a APIs externas + leen archivos locales
- `/backtest`, `/hmm-analyze` — corren scripts Python locales con datasets >100MB
- `/profile` — switch de profile activo (state local en `.claude/`)
- `/macross`, `/asian-range`, `/pullback`, `/liq-heatmap` — helpers numéricos puros, podrían exponerse en sub-proyecto futuro como `/agents/<helper>/run` adicionales
```

- [ ] **Step 2: Commit**

```bash
git add docs/api/CLI_TO_API.md
git commit -m "docs(api): CLI_TO_API.md mapeo de 10 slash commands a endpoints"
```

---

## Task 16: Write `AUTH.md`

**Files:**
- Create: `docs/api/AUTH.md`

- [ ] **Step 1: Create the file**

```markdown
# Auth — Phase 1 (X-User-Id) + roadmap a Clerk JWT

## Estado actual (Phase 1)

Todos los endpoints `/api/v1/*` requieren el header `X-User-Id: <uuid>` excepto:
- `GET /healthz`
- `GET /api/v1/ping`

El header debe contener el UUID de un row existente en `users`. Si falta o es inválido:
- Falta header → `401 Unauthorized` con `{"detail": "Missing X-User-Id header (Clerk JWT verification lands in Phase 1.5)"}`
- UUID mal formado → `400 Bad Request` con `{"detail": "X-User-Id is not a valid UUID"}`
- UUID no existe en DB → `401 Unauthorized` con `{"detail": "Unknown user"}`

**⚠️ NO exponer este API a internet pública con esta config.** El header es trivial de spoofear. Sólo apto para:
- Local dev
- Red privada / VPN
- Pruebas de integración con seed data controlada

Definido en `app/deps.py:get_current_user`.

## Por qué no hay Clerk JWT todavía

Sub-proyecto #1 (Auth) en el roadmap. Una vez wired:
1. Clerk envía webhook `user.created` → endpoint `/api/v1/auth/webhook` crea row en `users`
2. Frontend obtiene JWT de Clerk client SDK
3. `get_current_user` valida JWT (firma + iss + aud + exp) en vez de leer header
4. Header `X-User-Id` queda sólo como fallback para tests (con env var `WALLY_DEV_AUTH_BYPASS=1`)

## Roadmap concreto (Phase 1.5)

Ver spec `docs/superpowers/specs/<future>-auth-clerk-design.md` (no escrito aún). El cambio es self-contained — solo `app/deps.py` + un router nuevo + middleware. Endpoints existentes no cambian su firma pública (siguen aceptando o el JWT en `Authorization: Bearer ...` o el header de bypass para tests).

## Testing local

Crea un user manualmente vía SQL o seed script:

```sql
INSERT INTO users (id, email, clerk_user_id, created_at)
VALUES ('550e8400-e29b-41d4-a716-446655440000', 'dev@local', null, now());
```

Luego usa ese UUID en todas las requests:

```bash
export USER_ID=550e8400-e29b-41d4-a716-446655440000
curl -H "X-User-Id: $USER_ID" http://localhost:8000/api/v1/profiles
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/api/AUTH.md
git commit -m "docs(api): AUTH.md — Phase 1 X-User-Id + roadmap Clerk"
```

---

## Task 17: Write `ERRORS.md`

**Files:**
- Create: `docs/api/ERRORS.md`

- [ ] **Step 1: Create the file**

```markdown
# Errors — convenciones HTTP

Todos los errores devuelven JSON con `{"detail": "<mensaje>"}` (formato FastAPI default).

| Status | Cuándo se emite hoy | Ejemplo body |
|---|---|---|
| `400 Bad Request` | UUID mal formado en path o query (`profile_id`, `signal_id`, `key_id`, `run_id`) | `{"detail": "Invalid profile_id"}` |
| `401 Unauthorized` | Header `X-User-Id` falta o el UUID no existe en `users` | `{"detail": "Missing X-User-Id header (...)"}` o `{"detail": "Unknown user"}` |
| `404 Not Found` | Resource no existe O existe pero pertenece a otro usuario (información leak protection) | `{"detail": "Profile not found"}`, `{"detail": "Signal not found"}`, `{"detail": "Run not found"}`, `{"detail": "Key not found"}` |
| `409 Conflict` | Constraint de unicidad: `profiles.slug` duplicado, `equity_points (profile_id, date)` ya existe | `{"detail": "Profile with slug 'retail' already exists"}` |
| `422 Unprocessable Entity` | Validación de schema Pydantic — tipos, rangos, enums | `{"detail":[{"type":"greater_than","loc":["body","entry"],"msg":"Input should be greater than 0",...}]}` |
| `500 Internal Server Error` | Excepción no capturada — bug del backend | `{"detail":"Internal Server Error"}` (en producción no se filtra el stack trace) |
| `201 Created` | POST exitoso a recurso nuevo (signals, profiles, keys) | (con response body del recurso creado) |
| `204 No Content` | DELETE exitoso (keys, profiles) | (sin body) |

## Manejo en frontend (TypeScript pattern)

```typescript
async function apiCall<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    ...init,
    headers: { ...(init?.headers ?? {}), "X-User-Id": userId },
  });
  if (r.status === 204) return undefined as T;
  const body = await r.json();
  if (!r.ok) {
    // Body shape varies: 4xx-custom = {detail: string}, 422 = {detail: ValidationError[]}
    const msg = typeof body.detail === "string"
      ? body.detail
      : `Validation error: ${JSON.stringify(body.detail)}`;
    throw new APIError(r.status, msg);
  }
  return body as T;
}

class APIError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
```

## Diferencia 401 vs 404

Importante: cuando un signal/profile/run existe pero pertenece a OTRO usuario, devolvemos `404` (no `403`). Esto evita leak de "este recurso existe pero no es tuyo" que un atacante podría usar para enumerar IDs ajenos. La auth-failure para "no estás autenticado" es `401`; "no encontré nada accesible para vos" es `404`.

## Errores SSE (`POST /agents/{name}/run`)

Cuando un run falla mid-stream, el SSE emite un evento `error`:

```
event: error
data: {"type":"error","error":"<descripción>"}
```

El response HTTP sigue siendo `200 OK` porque el stream se abrió correctamente. El frontend debe inspeccionar cada evento, no solo el status code inicial.

Casos típicos del evento `error`:
- LLM provider devolvió 401 → "Anthropic authentication failed"
- Quota agotada → "Provider rate limit exceeded"
- Input inválido para el agent → "regime agent requires 'symbol' in input"
- Timeout interno → "LLM call timed out after 120s"
```

- [ ] **Step 2: Commit**

```bash
git add docs/api/ERRORS.md
git commit -m "docs(api): ERRORS.md — status codes + SSE error events"
```

---

## Task 18: Correct `api/README.md` — remove false claims

**Files:**
- Modify: `api/README.md`

- [ ] **Step 1: Open `api/README.md` and replace the body**

The current README claims `auth.py`, `billing.py`, `brokers.py`, `ws.py` exist. Remove those claims. Replace the file content with:

```markdown
# api/ — Wally Trader Backend

FastAPI + Python 3.13 + SQLAlchemy 2.0 + PostgreSQL + Redis.

This is the application API. Reuses `shared/wally_core/` for pure-logic
trading primitives (risk, regime, signals, multifactor, journal, macro).

> **Status: Phase 1.** Auth is via the `X-User-Id` header stub
> (`app/deps.py:get_current_user`). **Do not expose to public internet
> with this config** — the header is trivial to spoof. See
> [`../docs/api/AUTH.md`](../docs/api/AUTH.md) for details and the path
> to Clerk JWT in sub-project #1.

## Quick start (local dev)

```bash
cd api
uv sync                                  # install deps from pyproject.toml
cp .env.example .env                     # fill in DATABASE_URL, MASTER_KEK, etc
uv run alembic upgrade head              # apply DB migrations
uv run uvicorn app.main:app --reload     # http://localhost:8000
```

Or run the whole stack with Docker:

```bash
cd ../infra
docker compose -f docker-compose.dev.yml up
```

## Documentación

📖 **Manual completo:** [`../docs/api/`](../docs/api/) — endpoints, ejemplos curl + TypeScript, scenarios Wally Trader, mapping CLI → API.

📊 **Swagger UI** (sólo dev/staging): http://localhost:8000/docs

📜 **OpenAPI JSON:** http://localhost:8000/openapi.json

## Layout actual

```
app/
├── main.py                 # FastAPI app instance + middleware
├── core/
│   ├── config.py           # Pydantic Settings (env vars)
│   └── logging.py          # structured logging + secret redaction
├── db/
│   ├── base.py             # SQLAlchemy declarative base
│   └── session.py          # async engine + session factory
├── models/                 # 12 SQLAlchemy models
├── schemas/                # Pydantic v2 request/response models
├── api/v1/
│   ├── agents.py           # GET /agents, POST /agents/{name}/run (SSE), GET /agents/runs/{id}
│   ├── keys.py             # GET/POST/DELETE /keys/llm (BYOK encrypted)
│   ├── profiles.py         # 5 endpoints CRUD
│   ├── signals.py          # 4 endpoints CRUD + stats
│   └── equity.py           # GET series, POST upsert
├── agents/                 # 6 backend agents (regime, risk, signal_validator,
│                           #   multifactor, journal, sentiment)
├── llm_gateway/            # Provider router: anthropic / openai / google / ollama
├── security/
│   └── encryption.py       # AES-256-GCM DEK/KEK
└── deps.py                 # FastAPI dependency injection (current_user, db)

alembic/
├── env.py
└── versions/

tests/
├── conftest.py
├── test_encryption.py
├── test_llm_gateway_stream.py
├── test_pricing.py
├── test_generate_stubs.py  # docs autogen + idempotence
└── test_docs_in_sync.py    # CI gate: docs match code
```

## Roadmap (NO IMPLEMENTADO TODAVÍA)

Sub-proyectos del SaaS API que se trabajarán en specs separados:

| # | Sub-proyecto | Notas |
|---|---|---|
| #1 | Auth — Clerk + JWT + multi-tenant guards | Reemplaza el stub `X-User-Id`. Bloquea #2/#3/#4/#5. |
| #2 | Brokers — Bitunix / Binance / MT5 keys + sync | Reusa el patrón `key_service.py` |
| #3 | WebSockets + Redis pubsub | Eventos `signal.created`, `agent.run.token`, etc. |
| #4 | Billing — **Polar.sh** (no Stripe) | Subscriptions + metered usage via `UsageEvent` |
| #5 | Audit + rate limiting + observability | Wires `AuditLog`, Sentry |

Modelos huérfanos en DB esperando endpoint: `Subscription`, `UsageEvent`, `AuditLog`, `TradeBrokerSync`, `JournalEntry`. Ver [`../docs/api/MANUAL.md`](../docs/api/MANUAL.md).

## Reuses (from project root)

- `shared/wally_core/src/wally_core/*` — pure logic (do NOT duplicate)
- `scripts/ml_system/*` — ML pipeline (sentiment + XGBoost)
- `.claude/scripts/macro_gate.py` etc — wrapped as agent endpoints
```

- [ ] **Step 2: Commit**

```bash
git add api/README.md
git commit -m "docs(api): correct README — remove false claims, point to docs/api/"
```

---

## Task 19: Write `test_docs_in_sync.py` — CI canary

**Files:**
- Create: `api/tests/test_docs_in_sync.py`

- [ ] **Step 1: Create the test**

```python
"""CI canary: run docs/api/_generate_stubs.py --check.

If this fails, the engineer changed an endpoint (route/schema/status code)
without regenerating the manual. Fix:

    cd "$(git rev-parse --show-toplevel)"
    python docs/api/_generate_stubs.py
    git add docs/api/routers/
    git commit
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_docs_routers_in_sync() -> None:
    """Idempotence: running --check after a clean repo state must exit 0."""
    rc = subprocess.call(
        [sys.executable, "docs/api/_generate_stubs.py", "--check"],
        cwd=REPO_ROOT,
    )
    assert rc == 0, (
        "docs/api/routers/*.md is out of sync with the code. "
        "Run `python docs/api/_generate_stubs.py` and commit the result."
    )
```

- [ ] **Step 2: Run it**

```bash
cd api && uv run pytest tests/test_docs_in_sync.py -v
```

Expected: PASS (the manual is in sync because we just generated it in Task 6).

- [ ] **Step 3: Commit**

```bash
git add api/tests/test_docs_in_sync.py
git commit -m "test(api): docs-in-sync canary"
```

---

## Task 20: Wire CI gate (new GitHub Actions workflow)

**Files:**
- Create: `.github/workflows/api-docs-ci.yml`

The existing `ci.yml` uses Python 3.9-3.12 and pip; `api/` requires 3.13 + uv. A separate workflow is cleaner than complicating the matrix.

- [ ] **Step 1: Create the workflow**

```yaml
name: API Docs Sync

on:
  push:
    branches: [main]
    paths:
      - "api/**"
      - "docs/api/**"
      - ".github/workflows/api-docs-ci.yml"
  pull_request:
    branches: [main]
    paths:
      - "api/**"
      - "docs/api/**"
      - ".github/workflows/api-docs-ci.yml"
  workflow_dispatch:

jobs:
  docs-in-sync:
    name: Docs in sync with API
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"

      - name: Install api dependencies
        working-directory: api
        run: uv sync

      - name: Run docs sync check
        run: uv --project api run python docs/api/_generate_stubs.py --check

      - name: Run docs-sync test
        working-directory: api
        run: uv run pytest tests/test_docs_in_sync.py -v
```

- [ ] **Step 2: Verify YAML syntax locally**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/api-docs-ci.yml'))"
```

Expected: no output / no exception.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/api-docs-ci.yml
git commit -m "ci(api): docs-in-sync gate (Python 3.13 + uv)"
```

---

## Task 21: Final verification — DoD checklist

**Files:** _(no new files; verification only)_

- [ ] **Step 1: Run the full test suite for api/**

```bash
cd api && uv run pytest -v
```

Expected: all tests pass, including new `test_generate_stubs.py` and `test_docs_in_sync.py`.

- [ ] **Step 2: Verify all 11 DoD items**

Run each check and confirm:

```bash
# 1. Six router files exist
ls docs/api/routers/{meta,agents,keys,profiles,signals,equity}.md

# 2. MANUAL.md lists 19 endpoints
grep -c "^| " docs/api/MANUAL.md  # >= 20 (header + 19 rows)

# 3. SCENARIOS.md has 8 scenarios
grep -c "^## [0-9]" docs/api/SCENARIOS.md  # == 8

# 4. CLI_TO_API.md maps 10 commands
grep -c "^| \`/" docs/api/CLI_TO_API.md  # == 10

# 5. AUTH.md exists with content
test -s docs/api/AUTH.md && echo "AUTH.md ok"

# 6. ERRORS.md catalogs status codes
grep -c '`[0-9][0-9][0-9]' docs/api/ERRORS.md  # >= 6

# 7. api/README.md does not lie about non-existent files
! grep -E '^\| \w+\.py' api/README.md | grep -E 'auth|billing|brokers|ws' \
  || echo "FAIL: README still mentions phantom files"

# 8. _generate_stubs.py runs and supports modes
python docs/api/_generate_stubs.py --check  # exit 0
python docs/api/_generate_stubs.py --router signals  # exits 0

# 9. CI gate exists
test -s .github/workflows/api-docs-ci.yml && echo "CI workflow ok"

# 10. test_docs_in_sync.py passes
cd api && uv run pytest tests/test_docs_in_sync.py -v && cd ..

# 11. docs/api/README.md is the entry point
grep -q "Wally Trader API" docs/api/README.md && echo "Entry README ok"
```

- [ ] **Step 3: Sanity check — try a real workflow**

Spin up the API locally and test scenario 1 end-to-end:

```bash
cd api && uv run uvicorn app.main:app --reload &
sleep 3

# Need a seed user — adjust if your dev DB doesn't have one yet
USER_ID="550e8400-e29b-41d4-a716-446655440000"

# 1. List profiles
curl -s -H "X-User-Id: $USER_ID" http://localhost:8000/api/v1/profiles?include_metrics=true | jq

# 2. Health check
curl -s http://localhost:8000/healthz | jq

# 3. List agents
curl -s -H "X-User-Id: $USER_ID" http://localhost:8000/api/v1/agents | jq '.[].name'

kill %1
```

If any of these fail, document the gap as a follow-up issue (don't try to fix scope-creep here — this is the audit-only sub-project).

- [ ] **Step 4: Final commit (if any small fixes were needed during verification)**

```bash
# only if there are pending changes from the verification
git status
# git add ... && git commit -m "docs(api): verification fixes"
```

- [ ] **Step 5: Push the branch and open PR (if working in a feature branch)**

If you started this work on a feature branch:

```bash
git push -u origin <branch-name>
gh pr create --title "docs(api): manual + audit (sub-project #0)" --body "$(cat <<'EOF'
## Summary
- Documents the 5 routers already implemented in api/ (19 endpoints)
- Adds docs/api/_generate_stubs.py with FastAPI introspection + CI gate
- 8 scenarios + 10 CLI mappings + AUTH + ERRORS docs
- Corrects api/README.md (removed phantom file claims)

## Test plan
- [x] api/tests/test_generate_stubs.py — 8 unit tests pass
- [x] api/tests/test_docs_in_sync.py — idempotence canary passes
- [x] python docs/api/_generate_stubs.py --check returns 0
- [x] All 11 DoD items in the spec verified manually

Spec: docs/superpowers/specs/2026-05-13-api-manual-design.md
Plan: docs/superpowers/plans/2026-05-13-api-manual.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
