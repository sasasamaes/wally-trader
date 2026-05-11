"""Bootstrap the local dev database.

Idempotent. Run after `docker compose up -d postgres`:

    cd api
    uv run python scripts/bootstrap_db.py

What it does:
1. Connects to Postgres (waiting up to 30s for readiness)
2. If there are no Alembic migrations yet, generates the initial one via
   `alembic revision --autogenerate -m initial`
3. Runs `alembic upgrade head`
4. Verifies every table from `app.models` exists

This is a dev convenience — in production we generate migrations during
development, commit them, and `upgrade head` runs as part of deploy.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

API_ROOT = Path(__file__).parent.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


async def wait_for_postgres(url: str, timeout_s: int = 30) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url, pool_pre_ping=True)
    deadline = asyncio.get_event_loop().time() + timeout_s
    while asyncio.get_event_loop().time() < deadline:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                await engine.dispose()
                return
        except OperationalError:
            await asyncio.sleep(1)
    raise RuntimeError(f"Postgres at {url} not ready after {timeout_s}s")


async def run() -> None:
    from app.core.config import get_settings
    from app.db.base import Base

    settings = get_settings()
    url = str(settings.DATABASE_URL)
    print(f"→ Waiting for Postgres at {url.split('@')[-1]} …")
    await wait_for_postgres(url)

    versions_dir = API_ROOT / "alembic" / "versions"
    existing_migrations = [
        f for f in versions_dir.glob("*.py") if not f.name.startswith("__")
    ]
    if not existing_migrations:
        print("→ No migrations yet — generating initial revision …")
        result = subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", "initial"],
            cwd=API_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            raise SystemExit("alembic revision failed")
        print(result.stdout)
    else:
        print(f"→ Found {len(existing_migrations)} existing migration(s); skipping autogenerate.")

    print("→ Running alembic upgrade head …")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=API_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit("alembic upgrade failed")
    print(result.stdout)

    # Verify every expected table is present
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url)
    async with engine.connect() as conn:
        names = await conn.run_sync(lambda c: inspect(c).get_table_names())
    await engine.dispose()

    expected = set(Base.metadata.tables.keys())
    missing = expected - set(names)
    if missing:
        raise SystemExit(f"Missing tables after upgrade: {missing}")
    print(f"✓ All {len(expected)} tables present.")


if __name__ == "__main__":
    asyncio.run(run())
