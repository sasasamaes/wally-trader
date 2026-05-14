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
        f"- **Method** `{route.method}`\n"
        f"- **Path** `{route.path}`\n"
        f"- **Auth** {auth}\n"
        f"- **Status codes** {statuses_str}\n\n"
        f"**Request body:**\n\n{req_table}\n\n"
        f"**Response:** `{resp_name}`\n"
        f"<!-- AUTOGEN:END name={bid} -->"
    )


if __name__ == "__main__":
    routes = discover_routes()
    print(f"Discovered {len(routes)} routes:")
    for r in routes:
        print(f"  {r.method:6} {r.path}   [tag={r.tag}, auth={r.requires_auth}]")
