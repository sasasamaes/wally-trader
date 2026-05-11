"""Create a dev user row + print the UUID for the `X-User-Id` header.

The Phase 1 auth stub uses `X-User-Id: <uuid>` headers. This script gives
you one so you can hit the API from curl / the frontend without standing
up Clerk first.

Usage:
    cd api
    uv run python scripts/create_dev_user.py jose@example.com

Idempotent — re-running with the same email returns the existing UUID.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

API_ROOT = Path(__file__).parent.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


async def run(email: str, name: str | None) -> None:
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.email == email)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            print(existing.id)
            return

        user = User(
            email=email,
            clerk_id=f"dev_{email}",
            name=name,
            plan_tier="beta",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(user.id)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: create_dev_user.py <email> [name]", file=sys.stderr)
        sys.exit(1)
    asyncio.run(run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
