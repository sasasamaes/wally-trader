"""Regenerate AUTOGEN sections in docs/api/routers/*.md from FastAPI introspection.

Modes:
    python docs/api/_generate_stubs.py             # write changes
    python docs/api/_generate_stubs.py --check     # exit 1 if any file would change
    python docs/api/_generate_stubs.py --router signals   # only one file

Run from repo root.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Make `app` importable without uv sync needing to install us as a package.
REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "api"
sys.path.insert(0, str(API_ROOT))

# Set required env vars BEFORE app imports — Pydantic Settings reads at import time.
import os  # noqa: E402

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://wally:wally@localhost:5432/wally_dev"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault(
    "MASTER_KEK", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
)

from fastapi.routing import APIRoute  # noqa: E402

from app.main import app  # noqa: E402
from app.deps import get_current_user as _GET_CURRENT_USER  # noqa: E402


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
        return str(route.tags[0])
    return "meta"


def _route_requires_auth(route: APIRoute) -> bool:
    """True if the route depends directly on get_current_user.

    Walks only top-level deps (not transitive). Identity comparison so renames
    of the function in app.deps do not silently break detection.
    """
    return any(dep.call is _GET_CURRENT_USER for dep in route.dependant.dependencies)


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
                annotation = r.body_field.field_info.annotation
                if hasattr(annotation, "model_json_schema"):
                    req_schema = annotation.model_json_schema()
            resp_schema = None
            if r.response_model is not None:
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
    if "allOf" in p:
        # Pydantic v2 wraps some model refs in allOf with a single element
        return _schema_type(p["allOf"][0]) if p["allOf"] else "any"
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
    status_set = {route.success_status} | set(route.error_responses.keys())
    statuses_str = ", ".join(str(c) for c in sorted(status_set))
    req_table = _render_request_table(route.request_schema)
    resp_name = _response_model_name(route.response_schema)
    summary_part = f"_{route.summary}_\n\n" if route.summary else ""

    return (
        f"<!-- AUTOGEN:START name={bid} -->\n"
        f"{summary_part}"
        f"- **Method** `{route.method}`\n"
        f"- **Path** `{route.path}`\n"
        f"- **Auth** {auth}\n"
        f"- **Status codes** {statuses_str}\n\n"
        f"**Request body:**\n\n{req_table}\n\n"
        f"**Response:** `{resp_name}`\n"
        f"<!-- AUTOGEN:END name={bid} -->"
    )


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


class MismatchedBlockError(RuntimeError):
    """A file has an AUTOGEN START marker without a matching END (or with a different id)."""


_START_SCAN = re.compile(r"<!-- AUTOGEN:START name=([\w\-]+) -->")


def apply_blocks(path: Path, blocks: dict[str, str]) -> None:
    """Replace each AUTOGEN block in `path` with the matching string in `blocks`.

    - Existing markers whose id IS in `blocks` get replaced.
    - Markers whose id is NOT in `blocks` raise OrphanBlockError.
    - Block ids in `blocks` that are NOT in the file get appended as a fresh
      stub (with empty hand-write sections).
    - START markers without a matching END (or with a mismatched END id) raise
      MismatchedBlockError to fail loud rather than silently skip them.
    """
    text = path.read_text() if path.exists() else ""

    # Pre-scan to validate: every START must end up matched by the back-referenced
    # block_re below, otherwise the markers are malformed.
    all_starts = set(_START_SCAN.findall(text))
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

    block_re = re.compile(
        r"<!-- AUTOGEN:START name=([\w\-]+) -->.*?<!-- AUTOGEN:END name=\1 -->",
        re.DOTALL,
    )
    new_text = block_re.sub(_replace, text)

    unmatched_starts = all_starts - found_ids
    if unmatched_starts:
        raise MismatchedBlockError(
            f"File {path} has START marker(s) for {sorted(unmatched_starts)} "
            f"with no matching END marker (or END has a different id). "
            f"Fix the markers manually and retry."
        )

    missing = [bid for bid in blocks if bid not in found_ids]
    if missing:
        if not new_text.endswith("\n"):
            new_text += "\n"
        for bid in missing:
            method, route_path = bid.split("-", 1)
            new_text += f"\n## `{method} /{route_path.replace('-', '/')}`\n\n"
            new_text += blocks[bid] + "\n"
            new_text += EMPTY_HANDWRITE + "\n"

    path.write_text(new_text)


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
        except MismatchedBlockError as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return 4
        after = f.read_text()
        if before != after:
            diffs += 1
            if args.check:
                # In --check mode, restore the original
                if before:
                    f.write_text(before)
                else:
                    f.unlink(missing_ok=True)
                try:
                    display = f.relative_to(REPO_ROOT)
                except ValueError:
                    display = f
                print(f"DRIFT: {display}", file=sys.stderr)

    if args.check and diffs > 0:
        print(
            f"\n{diffs} file(s) out of sync. Run `python docs/api/_generate_stubs.py` and commit.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
