# Auth — Clerk JWT + Webhook Sync — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `X-User-Id` stub in `app/deps.py:get_current_user` with real Clerk JWT verification (production hard requirement) + add `POST /api/v1/auth/webhook` to sync `users` from Clerk `user.*` events. Preserve dev/test bypass via `WALLY_DEV_AUTH_BYPASS=1`.

**Architecture:** Pure-logic JWT verifier in `app/security/clerk.py` (testable without FastAPI), svix-verified webhook handler in `app/security/webhook.py` + thin route in `app/api/v1/auth.py`. `app/deps.py:get_current_user` routes between Bearer-JWT path and bypass header path based on env var. Startup validation refuses to boot in production with missing Clerk config.

**Tech Stack:** Python 3.13 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 async + pyjwt (JWT) + svix (webhook signatures) + httpx (JWKS fetch) + asyncache (JWKS TTL cache) + respx (test mocking) + pytest-asyncio.

---

## File Structure

**Files created (5 new):**

```
api/app/
├── api/v1/auth.py                 # POST /api/v1/auth/webhook (thin route)
└── security/
    ├── clerk.py                    # verify_jwt + JWKS fetch+cache (pure logic)
    └── webhook.py                  # svix verify + dispatch + 3 user.* handlers

api/tests/
├── test_clerk.py                   # 5 unit tests (verify_jwt happy + 4 fails)
├── test_auth_webhook.py            # 8 integration tests (svix sign, 3 events, errors)
└── test_deps.py                    # 4 unit tests (get_current_user routing)
```

**Files modified (6):**

```
api/pyproject.toml                  # + svix>=1.40.0 + respx>=0.21.0 + asyncache>=0.3.1
api/app/core/config.py              # + jwks_url property + WALLY_DEV_AUTH_BYPASS field
api/app/api/v1/__init__.py          # include_router(auth_router)
api/app/main.py                     # lifespan validates Clerk env vars in production
api/app/deps.py                     # refactor get_current_user (Bearer + bypass paths)
api/tests/conftest.py               # autouse WALLY_DEV_AUTH_BYPASS=1 + clerk_authed_client fixture
docs/api/AUTH.md                    # Phase 2 narrative
docs/api/routers/auth.md            # auto-generated stub + ✍️ hand-fill
docs/api/MANUAL.md                  # +1 endpoint row + roadmap #1 ✅
api/README.md                       # Status callout + roadmap #1 ✅
```

---

## Task 1: Add dependencies (svix, respx, asyncache)

**Files:**
- Modify: `api/pyproject.toml`

- [ ] **Step 1: Edit `api/pyproject.toml` to add dependencies**

In the main `[project] dependencies = [...]` array, locate the line `"pyjwt>=2.10.0",` and add a new line right after it:

```toml
    # Webhook signature verification (Clerk uses Svix)
    "svix>=1.40.0",
    # JWKS TTL cache for Clerk JWT verification
    "asyncache>=0.3.1",
```

In the `[dependency-groups] dev = [...]` array (or the test-related section, wherever pytest deps live), add:

```toml
    # HTTP request mocking for clerk.py JWKS tests
    "respx>=0.21.0",
```

- [ ] **Step 2: Sync deps**

```bash
cd /Users/josecampos/Documents/wally-trader/api && uv sync
```

Expected: `Resolved N packages` + `Installed M packages` mentioning `svix`, `respx`, `asyncache`.

- [ ] **Step 3: Verify import works**

```bash
api/.venv/bin/python -c "from svix.webhooks import Webhook; from asyncache import cached; import respx; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add api/pyproject.toml api/uv.lock
git commit -m "chore(api): add svix + asyncache + respx for Clerk auth"
```

---

## Task 2: Settings — `WALLY_DEV_AUTH_BYPASS` field + `jwks_url` property (TDD)

**Files:**
- Modify: `api/app/core/config.py`
- Create: `api/tests/test_config_clerk.py`

- [ ] **Step 1: Write failing test for `jwks_url` property**

Create `api/tests/test_config_clerk.py`:

```python
"""Tests for Clerk-specific Settings extensions."""

from __future__ import annotations

from app.core.config import Settings


def test_jwks_url_derived_from_issuer() -> None:
    s = Settings(
        DATABASE_URL="postgresql+asyncpg://x:y@localhost/test",
        REDIS_URL="redis://localhost",
        MASTER_KEK="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        CLERK_JWT_ISSUER="https://example.clerk.accounts.dev",
    )
    assert s.jwks_url == "https://example.clerk.accounts.dev/.well-known/jwks.json"


def test_jwks_url_returns_none_without_issuer() -> None:
    s = Settings(
        DATABASE_URL="postgresql+asyncpg://x:y@localhost/test",
        REDIS_URL="redis://localhost",
        MASTER_KEK="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    )
    assert s.jwks_url is None


def test_dev_auth_bypass_default_false() -> None:
    s = Settings(
        DATABASE_URL="postgresql+asyncpg://x:y@localhost/test",
        REDIS_URL="redis://localhost",
        MASTER_KEK="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    )
    assert s.WALLY_DEV_AUTH_BYPASS is False


def test_dev_auth_bypass_reads_env(monkeypatch) -> None:
    monkeypatch.setenv("WALLY_DEV_AUTH_BYPASS", "1")
    s = Settings(
        DATABASE_URL="postgresql+asyncpg://x:y@localhost/test",
        REDIS_URL="redis://localhost",
        MASTER_KEK="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    )
    assert s.WALLY_DEV_AUTH_BYPASS is True
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd api && uv run pytest tests/test_config_clerk.py -v
```

Expected: 4 failures (`AttributeError: 'Settings' object has no attribute 'jwks_url'` / `WALLY_DEV_AUTH_BYPASS`)

- [ ] **Step 3: Implement in `api/app/core/config.py`**

Add `WALLY_DEV_AUTH_BYPASS` field. Find the `# --- Auth (Clerk) ---` section and add after `CLERK_WEBHOOK_SECRET`:

```python
    # Dev/test escape hatch: when True, get_current_user accepts X-User-Id header
    # instead of requiring a Clerk JWT. MUST be False in production (validated at startup).
    WALLY_DEV_AUTH_BYPASS: bool = False
```

Find the Settings class. Add a property at the end of the class body (after the last field, before any closing methods if they exist):

```python
    @property
    def jwks_url(self) -> str | None:
        """Derive Clerk JWKS endpoint from CLERK_JWT_ISSUER."""
        if not self.CLERK_JWT_ISSUER:
            return None
        return f"{self.CLERK_JWT_ISSUER.rstrip('/')}/.well-known/jwks.json"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd api && uv run pytest tests/test_config_clerk.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add api/app/core/config.py api/tests/test_config_clerk.py
git commit -m "feat(config): jwks_url property + WALLY_DEV_AUTH_BYPASS field"
```

---

## Task 3: `app/security/clerk.py` — JWKS fetch + cache (TDD)

**Files:**
- Create: `api/app/security/clerk.py`
- Create: `api/tests/test_clerk.py`

- [ ] **Step 1: Write failing test for `_fetch_jwks`**

Create `api/tests/test_clerk.py`:

```python
"""Tests for app/security/clerk.py — Clerk JWT verification."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.security import clerk

JWKS_URL = "https://example.clerk.accounts.dev/.well-known/jwks.json"

# Sample JWKS response — 1 RSA key
SAMPLE_JWKS = {
    "keys": [
        {
            "kty": "RSA",
            "kid": "ins_test_kid_1",
            "use": "sig",
            "alg": "RS256",
            "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw",
            "e": "AQAB",
        }
    ]
}


@pytest.mark.asyncio
@respx.mock
async def test_fetch_jwks_returns_keys() -> None:
    respx.get(JWKS_URL).mock(return_value=Response(200, json=SAMPLE_JWKS))
    keys = await clerk._fetch_jwks(JWKS_URL)
    assert keys == SAMPLE_JWKS["keys"]


@pytest.mark.asyncio
@respx.mock
async def test_fetch_jwks_caches_result() -> None:
    """Second call within TTL must NOT trigger another HTTP request."""
    clerk._jwks_cache.clear()  # ensure clean state
    route = respx.get(JWKS_URL).mock(return_value=Response(200, json=SAMPLE_JWKS))
    await clerk._fetch_jwks(JWKS_URL)
    await clerk._fetch_jwks(JWKS_URL)
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_fetch_jwks_propagates_503_on_clerk_down() -> None:
    clerk._jwks_cache.clear()
    respx.get(JWKS_URL).mock(return_value=Response(503))
    with pytest.raises(clerk.JWKSFetchError):
        await clerk._fetch_jwks(JWKS_URL)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd api && uv run pytest tests/test_clerk.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.security.clerk'`

- [ ] **Step 3: Implement `_fetch_jwks` + cache in `api/app/security/clerk.py`**

Create `api/app/security/clerk.py`:

```python
"""Clerk JWT verification — pure-logic, no FastAPI dependencies.

Verifies a Bearer JWT issued by Clerk by:
  1. Fetching the JWKS document from CLERK_JWT_ISSUER (TTL-cached)
  2. Picking the matching key by `kid` claim in the JWT header
  3. Validating signature + exp + iat + iss via pyjwt
"""

from __future__ import annotations

from typing import Any

import httpx
from asyncache import cached
from cachetools import TTLCache


class JWKSFetchError(RuntimeError):
    """JWKS endpoint unavailable or returned non-2xx."""


class InvalidJWT(RuntimeError):
    """JWT failed signature, expiry, issuer, or other claim validation."""


# Cache JWKS for 1 hour; only one entry (one Clerk instance).
_jwks_cache: TTLCache[str, list[dict[str, Any]]] = TTLCache(maxsize=4, ttl=3600)


@cached(_jwks_cache)
async def _fetch_jwks(jwks_url: str) -> list[dict[str, Any]]:
    """Fetch the JWKS document from Clerk. TTL-cached 1h.

    Raises JWKSFetchError on network failure or non-2xx response.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(jwks_url)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise JWKSFetchError(f"Failed to fetch JWKS from {jwks_url}: {exc}") from exc
    body = resp.json()
    keys = body.get("keys", [])
    if not isinstance(keys, list):
        raise JWKSFetchError(f"JWKS response from {jwks_url} has no 'keys' array")
    return keys
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd api && uv run pytest tests/test_clerk.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add api/app/security/clerk.py api/tests/test_clerk.py
git commit -m "feat(security): clerk.py JWKS fetch + TTL cache"
```

---

## Task 4: `app/security/clerk.py` — `verify_jwt` (TDD)

**Files:**
- Modify: `api/app/security/clerk.py`
- Modify: `api/tests/test_clerk.py`

- [ ] **Step 1: Write failing tests for `verify_jwt`**

Append to `api/tests/test_clerk.py`:

```python
import time

import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

ISSUER = "https://example.clerk.accounts.dev"


def _generate_rsa_keypair() -> tuple[rsa.RSAPrivateKey, str, dict[str, Any]]:
    """Generate an RSA keypair + return (private_key, kid, jwk_dict_for_jwks)."""
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = priv.public_key()
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    # Build a minimal JWK from public numbers
    numbers = pub.public_numbers()
    import base64

    def _b64u(n: int) -> str:
        b = n.to_bytes((n.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

    kid = "test-kid-1"
    jwk = {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": "RS256",
        "n": _b64u(numbers.n),
        "e": _b64u(numbers.e),
    }
    return priv, kid, jwk


def _sign_jwt(private_key, kid: str, claims: dict[str, Any]) -> str:
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pyjwt.encode(claims, priv_pem, algorithm="RS256", headers={"kid": kid})


@pytest.mark.asyncio
@respx.mock
async def test_verify_jwt_happy_path() -> None:
    clerk._jwks_cache.clear()
    priv, kid, jwk = _generate_rsa_keypair()
    respx.get(JWKS_URL).mock(return_value=Response(200, json={"keys": [jwk]}))

    now = int(time.time())
    token = _sign_jwt(priv, kid, {
        "sub": "user_clerk_id_xyz",
        "iss": ISSUER,
        "iat": now,
        "exp": now + 3600,
    })

    claims = await clerk.verify_jwt(token, jwks_url=JWKS_URL, issuer=ISSUER)
    assert claims["sub"] == "user_clerk_id_xyz"


@pytest.mark.asyncio
@respx.mock
async def test_verify_jwt_expired_raises() -> None:
    clerk._jwks_cache.clear()
    priv, kid, jwk = _generate_rsa_keypair()
    respx.get(JWKS_URL).mock(return_value=Response(200, json={"keys": [jwk]}))
    now = int(time.time())
    token = _sign_jwt(priv, kid, {
        "sub": "user_x", "iss": ISSUER, "iat": now - 7200, "exp": now - 3600,
    })
    with pytest.raises(clerk.InvalidJWT) as exc:
        await clerk.verify_jwt(token, jwks_url=JWKS_URL, issuer=ISSUER)
    assert "expired" in str(exc.value).lower()


@pytest.mark.asyncio
@respx.mock
async def test_verify_jwt_unknown_kid_raises() -> None:
    clerk._jwks_cache.clear()
    priv, _, jwk = _generate_rsa_keypair()  # JWKS has kid="test-kid-1"
    respx.get(JWKS_URL).mock(return_value=Response(200, json={"keys": [jwk]}))
    now = int(time.time())
    token = _sign_jwt(priv, "different-kid", {  # signed with different kid
        "sub": "user_x", "iss": ISSUER, "iat": now, "exp": now + 3600,
    })
    with pytest.raises(clerk.InvalidJWT) as exc:
        await clerk.verify_jwt(token, jwks_url=JWKS_URL, issuer=ISSUER)
    assert "kid" in str(exc.value).lower()


@pytest.mark.asyncio
@respx.mock
async def test_verify_jwt_wrong_issuer_raises() -> None:
    clerk._jwks_cache.clear()
    priv, kid, jwk = _generate_rsa_keypair()
    respx.get(JWKS_URL).mock(return_value=Response(200, json={"keys": [jwk]}))
    now = int(time.time())
    token = _sign_jwt(priv, kid, {
        "sub": "user_x", "iss": "https://wrong.issuer.example",
        "iat": now, "exp": now + 3600,
    })
    with pytest.raises(clerk.InvalidJWT):
        await clerk.verify_jwt(token, jwks_url=JWKS_URL, issuer=ISSUER)


@pytest.mark.asyncio
@respx.mock
async def test_verify_jwt_malformed_token_raises() -> None:
    clerk._jwks_cache.clear()
    respx.get(JWKS_URL).mock(return_value=Response(200, json=SAMPLE_JWKS))
    with pytest.raises(clerk.InvalidJWT):
        await clerk.verify_jwt("not.a.real.jwt", jwks_url=JWKS_URL, issuer=ISSUER)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd api && uv run pytest tests/test_clerk.py -v -k verify_jwt
```

Expected: 5 failures (`AttributeError: module 'app.security.clerk' has no attribute 'verify_jwt'`).

- [ ] **Step 3: Implement `verify_jwt` in `app/security/clerk.py`**

Append to `api/app/security/clerk.py`:

```python
import jwt as pyjwt
from jwt.algorithms import RSAAlgorithm


async def verify_jwt(token: str, *, jwks_url: str, issuer: str) -> dict[str, Any]:
    """Verify a Clerk-issued JWT and return its claims.

    Raises InvalidJWT for any signature, expiry, issuer, or format failure.
    Raises JWKSFetchError if the JWKS endpoint is unreachable.
    """
    try:
        unverified_header = pyjwt.get_unverified_header(token)
    except pyjwt.PyJWTError as exc:
        raise InvalidJWT(f"Malformed JWT header: {exc}") from exc

    kid = unverified_header.get("kid")
    if not kid:
        raise InvalidJWT("JWT header missing 'kid' claim")

    keys = await _fetch_jwks(jwks_url)
    matching = next((k for k in keys if k.get("kid") == kid), None)
    if matching is None:
        raise InvalidJWT(f"No JWKS entry matches token kid={kid!r}")

    public_key = RSAAlgorithm.from_jwk(matching)

    try:
        claims = pyjwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"verify_aud": False},  # Clerk template may or may not set audience
        )
    except pyjwt.ExpiredSignatureError as exc:
        raise InvalidJWT(f"Token expired: {exc}") from exc
    except pyjwt.InvalidIssuerError as exc:
        raise InvalidJWT(f"Wrong issuer: {exc}") from exc
    except pyjwt.PyJWTError as exc:
        raise InvalidJWT(f"Invalid JWT: {exc}") from exc

    return claims
```

- [ ] **Step 4: Run tests to verify all 8 pass**

```bash
cd api && uv run pytest tests/test_clerk.py -v
```

Expected: 8 PASS (3 from Task 3 + 5 new).

- [ ] **Step 5: Commit**

```bash
git add api/app/security/clerk.py api/tests/test_clerk.py
git commit -m "feat(security): clerk.verify_jwt with kid lookup + RS256 + issuer validation"
```

---

## Task 5: `app/security/webhook.py` — svix verify + 3 user.* handlers (TDD)

**Files:**
- Create: `api/app/security/webhook.py`
- Create part 1 of `api/tests/test_auth_webhook.py` (handler-level tests)

- [ ] **Step 1: Write failing tests for handlers**

Create `api/tests/test_auth_webhook.py`:

```python
"""Tests for app/security/webhook.py — Clerk webhook event handlers."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.user import User
from app.security import webhook


@pytest.mark.asyncio
async def test_handle_user_created_inserts_row(db_session) -> None:
    data = {
        "id": "user_clerk_xyz",
        "email_addresses": [
            {"id": "email_1", "email_address": "alice@example.com"}
        ],
        "primary_email_address_id": "email_1",
        "first_name": "Alice",
        "last_name": "Smith",
    }
    result = await webhook.handle_user_created(data, db_session)
    assert result["status"] == "ok"

    row = (await db_session.execute(
        select(User).where(User.clerk_id == "user_clerk_xyz")
    )).scalar_one()
    assert row.email == "alice@example.com"
    assert row.name == "Alice Smith"
    assert row.plan_tier == "beta"


@pytest.mark.asyncio
async def test_handle_user_created_idempotent_on_duplicate(db_session) -> None:
    data = {
        "id": "user_dup",
        "email_addresses": [{"id": "e", "email_address": "dup@example.com"}],
        "primary_email_address_id": "e",
        "first_name": "D", "last_name": "U",
    }
    await webhook.handle_user_created(data, db_session)
    result = await webhook.handle_user_created(data, db_session)
    assert result["status"] == "ok"
    assert result.get("duplicate") is True


@pytest.mark.asyncio
async def test_handle_user_created_skips_when_no_email(db_session) -> None:
    data = {
        "id": "user_no_email",
        "email_addresses": [],
        "primary_email_address_id": None,
        "first_name": "X", "last_name": "Y",
    }
    result = await webhook.handle_user_created(data, db_session)
    assert result["status"] == "skipped"
    assert "no_email" in result["reason"]


@pytest.mark.asyncio
async def test_handle_user_updated_modifies_existing(db_session) -> None:
    # Seed
    seed = User(clerk_id="user_upd", email="old@x.com", name="Old", plan_tier="beta")
    db_session.add(seed)
    await db_session.flush()

    data = {
        "id": "user_upd",
        "email_addresses": [{"id": "e", "email_address": "new@x.com"}],
        "primary_email_address_id": "e",
        "first_name": "New", "last_name": "Name",
    }
    result = await webhook.handle_user_updated(data, db_session)
    assert result["status"] == "ok"

    row = await db_session.get(User, seed.id)
    assert row.email == "new@x.com"
    assert row.name == "New Name"


@pytest.mark.asyncio
async def test_handle_user_updated_inserts_when_missing(db_session) -> None:
    data = {
        "id": "user_upd_missing",
        "email_addresses": [{"id": "e", "email_address": "first@x.com"}],
        "primary_email_address_id": "e",
        "first_name": "First", "last_name": "Time",
    }
    result = await webhook.handle_user_updated(data, db_session)
    assert result["status"] == "ok"
    row = (await db_session.execute(
        select(User).where(User.clerk_id == "user_upd_missing")
    )).scalar_one()
    assert row.email == "first@x.com"


@pytest.mark.asyncio
async def test_handle_user_deleted_removes_row(db_session) -> None:
    seed = User(clerk_id="user_del", email="del@x.com", name="Del", plan_tier="beta")
    db_session.add(seed)
    await db_session.flush()

    result = await webhook.handle_user_deleted({"id": "user_del"}, db_session)
    assert result["status"] == "ok"
    row = (await db_session.execute(
        select(User).where(User.clerk_id == "user_del")
    )).scalar_one_or_none()
    assert row is None


@pytest.mark.asyncio
async def test_handle_user_deleted_idempotent_on_missing(db_session) -> None:
    result = await webhook.handle_user_deleted({"id": "nonexistent"}, db_session)
    assert result["status"] == "ok"
    assert result.get("not_found") is True


@pytest.mark.asyncio
async def test_dispatch_event_unknown_type_returns_skipped(db_session) -> None:
    payload = {"type": "session.created", "data": {}}
    result = await webhook.dispatch_event(payload, db_session)
    assert result["status"] == "skipped"
    assert result["reason"] == "unknown_event_type"
```

These tests need a `db_session` fixture. Verify `api/tests/conftest.py` exposes one — if NOT, add it now. Inspect the file first; if no `db_session` fixture exists, add this fixture (note: it requires a real Postgres reachable at the DATABASE_URL):

```python
# Add to api/tests/conftest.py
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async for session in get_db():
        yield session
        await session.rollback()
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd api && uv run pytest tests/test_auth_webhook.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.security.webhook'`

- [ ] **Step 3: Implement `app/security/webhook.py`**

Create `api/app/security/webhook.py`:

```python
"""Clerk webhook event dispatch + handlers.

Exposes:
    dispatch_event(payload, db) — routes type → handler, returns dict response.
    handle_user_created / handle_user_updated / handle_user_deleted — per-event logic.

All handlers are idempotent: duplicates / missing rows return 200 + indicator.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log
from app.models.user import User


def _extract_primary_email(data: dict[str, Any]) -> str | None:
    """Find the primary email per Clerk schema (id == primary_email_address_id),
    falling back to [0] if no match."""
    addresses = data.get("email_addresses") or []
    if not addresses:
        return None
    primary_id = data.get("primary_email_address_id")
    if primary_id:
        match = next((a for a in addresses if a.get("id") == primary_id), None)
        if match and match.get("email_address"):
            return match["email_address"]
    # Fallback to first
    first = addresses[0]
    return first.get("email_address")


def _full_name(data: dict[str, Any]) -> str | None:
    parts = [data.get("first_name"), data.get("last_name")]
    name = " ".join(p for p in parts if p)
    return name or None


async def handle_user_created(data: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    clerk_id = data["id"]
    email = _extract_primary_email(data)
    if not email:
        log.warning("clerk.webhook.no_email", clerk_id=clerk_id)
        return {"status": "skipped", "reason": "no_email"}

    user = User(
        clerk_id=clerk_id,
        email=email,
        name=_full_name(data),
        plan_tier="beta",
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        log.info("clerk.webhook.duplicate_user", clerk_id=clerk_id)
        return {"status": "ok", "duplicate": True}
    return {"status": "ok", "user_id": str(user.id)}


async def handle_user_updated(data: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    clerk_id = data["id"]
    email = _extract_primary_email(data)
    if not email:
        log.warning("clerk.webhook.no_email_on_update", clerk_id=clerk_id)
        return {"status": "skipped", "reason": "no_email"}

    stmt = select(User).where(User.clerk_id == clerk_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        # Out-of-order delivery — upsert
        user = User(
            clerk_id=clerk_id, email=email,
            name=_full_name(data), plan_tier="beta",
        )
        db.add(user)
    else:
        user.email = email
        user.name = _full_name(data) or user.name
    await db.flush()
    return {"status": "ok", "user_id": str(user.id)}


async def handle_user_deleted(data: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    clerk_id = data["id"]
    stmt = select(User).where(User.clerk_id == clerk_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        return {"status": "ok", "not_found": True}
    await db.delete(user)
    await db.flush()
    return {"status": "ok", "deleted": True}


EVENT_HANDLERS = {
    "user.created": handle_user_created,
    "user.updated": handle_user_updated,
    "user.deleted": handle_user_deleted,
}


async def dispatch_event(payload: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    """Route an event to its handler. Unknown event types return skipped (200)."""
    event_type = payload.get("type")
    handler = EVENT_HANDLERS.get(event_type)
    if handler is None:
        log.info("clerk.webhook.skipped", event_type=event_type)
        return {"status": "skipped", "reason": "unknown_event_type"}
    return await handler(payload.get("data") or {}, db)
```

- [ ] **Step 4: Run tests**

```bash
cd api && uv run pytest tests/test_auth_webhook.py -v
```

Expected: 8 PASS.

If any DB-related test fails with "no such table" or connection errors, the local Postgres is missing or migrations aren't applied. Apply: `cd api && uv run alembic upgrade head`. If Postgres truly unavailable, mark as DONE_WITH_CONCERNS and stop — do NOT modify the tests.

- [ ] **Step 5: Commit**

```bash
git add api/app/security/webhook.py api/tests/test_auth_webhook.py api/tests/conftest.py
git commit -m "feat(security): webhook.py dispatch + 3 user.* handlers (idempotent)"
```

---

## Task 6: `app/api/v1/auth.py` — webhook route + svix verification (TDD)

**Files:**
- Create: `api/app/api/v1/auth.py`
- Modify: `api/app/api/v1/__init__.py`
- Modify: `api/tests/test_auth_webhook.py` (append integration tests)

- [ ] **Step 1: Append failing integration tests for the route**

Append to `api/tests/test_auth_webhook.py`:

```python
import json

from svix.webhooks import Webhook
from httpx import AsyncClient


SAMPLE_WEBHOOK_SECRET = "whsec_test_dummy_secret_AAAAAAAAAAAAAAAAAAAAAAAA"


def _sign_webhook(body: bytes, secret: str = SAMPLE_WEBHOOK_SECRET) -> dict[str, str]:
    """Produce valid svix-* headers for a payload using the test secret."""
    import time
    import uuid

    msg_id = f"msg_{uuid.uuid4().hex[:20]}"
    timestamp = str(int(time.time()))
    wh = Webhook(secret)
    signature = wh.sign(msg_id, int(timestamp), body)
    return {
        "svix-id": msg_id,
        "svix-timestamp": timestamp,
        "svix-signature": signature,
    }


@pytest.mark.asyncio
async def test_webhook_route_user_created_end_to_end(
    async_client: AsyncClient,
) -> None:
    """Use FastAPI dependency_overrides to inject a Settings with a known webhook secret."""
    from pydantic import SecretStr
    from app.core.config import Settings, get_settings
    from app.main import app

    def _settings_with_secret() -> Settings:
        return Settings(
            DATABASE_URL="postgresql+asyncpg://x:y@h/d",
            REDIS_URL="redis://h",
            MASTER_KEK="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            CLERK_WEBHOOK_SECRET=SecretStr(SAMPLE_WEBHOOK_SECRET),
        )

    app.dependency_overrides[get_settings] = _settings_with_secret
    try:
        payload = {
        "type": "user.created",
        "data": {
            "id": "user_int_1",
            "email_addresses": [{"id": "e", "email_address": "int@example.com"}],
            "primary_email_address_id": "e",
            "first_name": "Int", "last_name": "Test",
        },
    }
        body = json.dumps(payload).encode()
        headers = _sign_webhook(body)
        r = await async_client.post(
            "/api/v1/auth/webhook",
            content=body,
            headers={**headers, "content-type": "application/json"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "ok"
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_webhook_route_invalid_signature_returns_401(async_client: AsyncClient) -> None:
    payload = {"type": "user.created", "data": {"id": "x"}}
    body = json.dumps(payload).encode()
    bad_headers = {
        "svix-id": "msg_x", "svix-timestamp": "1700000000",
        "svix-signature": "v1,deadbeef",
        "content-type": "application/json",
    }
    r = await async_client.post("/api/v1/auth/webhook", content=body, headers=bad_headers)
    assert r.status_code == 401
    assert "signature" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_webhook_route_missing_svix_headers_returns_400(async_client: AsyncClient) -> None:
    r = await async_client.post(
        "/api/v1/auth/webhook",
        content=b'{"type":"x"}',
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 400
    assert "svix" in r.json()["detail"].lower()
```

If `async_client` fixture doesn't exist in `conftest.py` yet, add it:

```python
# Add to api/tests/conftest.py
from httpx import ASGITransport, AsyncClient

@pytest_asyncio.fixture
async def async_client() -> AsyncClient:
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd api && uv run pytest tests/test_auth_webhook.py -v -k webhook_route
```

Expected: 3 failures (404 because route doesn't exist).

- [ ] **Step 3: Create `api/app/api/v1/auth.py`**

```python
"""Auth API — POST /api/v1/auth/webhook for Clerk user.* events."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from app.core.config import Settings, get_settings
from app.deps import get_db_session
from app.security import webhook as wh_handlers

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def clerk_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Receive Clerk user.* webhooks. Verifies svix signature, dispatches handler."""
    secret_obj = settings.CLERK_WEBHOOK_SECRET
    if secret_obj is None:
        raise HTTPException(503, "Webhook secret not configured")
    secret = secret_obj.get_secret_value()

    body = await request.body()

    headers = {
        "svix-id": request.headers.get("svix-id"),
        "svix-timestamp": request.headers.get("svix-timestamp"),
        "svix-signature": request.headers.get("svix-signature"),
    }
    if not all(headers.values()):
        raise HTTPException(400, "Missing svix-* headers")

    try:
        verifier = Webhook(secret)
        verifier.verify(body, headers)
    except WebhookVerificationError as exc:
        raise HTTPException(401, f"Invalid webhook signature: {exc}") from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "Invalid JSON body") from exc

    if "type" not in payload or "data" not in payload:
        raise HTTPException(400, "Malformed event payload (missing type or data)")

    return await wh_handlers.dispatch_event(payload, db)
```

- [ ] **Step 4: Register the router in `api/app/api/v1/__init__.py`**

Edit the file. Add the import alphabetically and include the router (order in OpenAPI is insertion order — pick whichever feels natural, e.g. before `agents`):

```python
from app.api.v1.agents import router as agents_router
from app.api.v1.auth import router as auth_router       # NEW
from app.api.v1.equity import router as equity_router
from app.api.v1.keys import router as keys_router
from app.api.v1.profiles import router as profiles_router
from app.api.v1.signals import router as signals_router

router = APIRouter()
router.include_router(auth_router)        # NEW — first, so OpenAPI lists it on top
router.include_router(agents_router)
router.include_router(keys_router)
router.include_router(profiles_router)
router.include_router(signals_router)
router.include_router(equity_router)
```

- [ ] **Step 5: Run tests**

```bash
cd api && uv run pytest tests/test_auth_webhook.py -v
```

Expected: 11 PASS (8 handler + 3 route).

- [ ] **Step 6: Commit**

```bash
git add api/app/api/v1/auth.py api/app/api/v1/__init__.py api/tests/test_auth_webhook.py api/tests/conftest.py
git commit -m "feat(api): POST /api/v1/auth/webhook with svix signature verification"
```

---

## Task 7: `app/deps.py` — refactor `get_current_user` (TDD)

**Files:**
- Create: `api/tests/test_deps.py`
- Modify: `api/app/deps.py`

- [ ] **Step 1: Write failing tests**

Create `api/tests/test_deps.py`:

```python
"""Tests for app/deps.py — get_current_user routing."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user
from app.models.user import User


@pytest.mark.asyncio
async def test_bypass_path_accepts_x_user_id(db_session, monkeypatch) -> None:
    """When WALLY_DEV_AUTH_BYPASS=1, the X-User-Id header path works."""
    monkeypatch.setenv("WALLY_DEV_AUTH_BYPASS", "1")
    # Seed
    u = User(clerk_id="bypass_user", email="bp@x.com", name="Bp", plan_tier="beta")
    db_session.add(u)
    await db_session.flush()

    # Force fresh Settings read
    from app.core.config import get_settings
    get_settings.cache_clear()

    user = await get_current_user(
        db=db_session,
        x_user_id=str(u.id),
        authorization=None,
    )
    assert user.id == u.id


@pytest.mark.asyncio
async def test_bypass_off_requires_bearer(db_session, monkeypatch) -> None:
    """When bypass is off, missing Authorization header → 401."""
    monkeypatch.setenv("WALLY_DEV_AUTH_BYPASS", "0")
    from app.core.config import get_settings
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc:
        await get_current_user(db=db_session, x_user_id=None, authorization=None)
    assert exc.value.status_code == 401
    assert "authorization" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_bearer_path_with_valid_jwt_and_known_user(db_session, monkeypatch) -> None:
    """Bypass off + valid Bearer JWT + clerk_id in DB → returns User."""
    monkeypatch.setenv("WALLY_DEV_AUTH_BYPASS", "0")
    from app.core.config import get_settings
    get_settings.cache_clear()

    u = User(clerk_id="bearer_user_xyz", email="b@x.com", name="B", plan_tier="beta")
    db_session.add(u)
    await db_session.flush()

    fake_claims = {"sub": "bearer_user_xyz", "email": "b@x.com"}

    with patch("app.deps.verify_jwt", new=AsyncMock(return_value=fake_claims)):
        user = await get_current_user(
            db=db_session,
            x_user_id=None,
            authorization="Bearer fake.jwt.here",
        )
    assert user.id == u.id


@pytest.mark.asyncio
async def test_bearer_path_unknown_clerk_id_raises_401(db_session, monkeypatch) -> None:
    monkeypatch.setenv("WALLY_DEV_AUTH_BYPASS", "0")
    from app.core.config import get_settings
    get_settings.cache_clear()

    fake_claims = {"sub": "never_synced_user", "email": "x@x.com"}

    with patch("app.deps.verify_jwt", new=AsyncMock(return_value=fake_claims)):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(
                db=db_session,
                x_user_id=None,
                authorization="Bearer fake.jwt.here",
            )
    assert exc.value.status_code == 401
    assert "unknown user" in exc.value.detail.lower()
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd api && uv run pytest tests/test_deps.py -v
```

Expected: 4 failures (`get_current_user` signature doesn't accept `authorization` kwarg yet).

- [ ] **Step 3: Refactor `api/app/deps.py`**

Replace the existing `get_current_user` function. Update imports first to include `verify_jwt`:

```python
from app.security.clerk import InvalidJWT, JWKSFetchError, verify_jwt
```

Replace the function body:

```python
async def get_current_user(
    db: AsyncSession = Depends(get_db_session),
    x_user_id: str | None = Header(default=None, description="Dev-only override (bypass)"),
    authorization: str | None = Header(default=None, description="Bearer <Clerk-JWT>"),
) -> User:
    """Return the authenticated user.

    Routing logic:
      - If WALLY_DEV_AUTH_BYPASS=1 in env: read X-User-Id header (existing path)
      - Else: parse Authorization: Bearer <jwt>, verify via Clerk, lookup by clerk_id
    """
    settings = get_settings()

    if settings.WALLY_DEV_AUTH_BYPASS:
        return await _resolve_by_uuid_header(db, x_user_id)

    return await _resolve_by_bearer_jwt(db, settings, authorization)


async def _resolve_by_uuid_header(db: AsyncSession, x_user_id: str | None) -> User:
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header (dev bypass mode)",
        )
    try:
        user_uuid = uuid.UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-User-Id is not a valid UUID",
        ) from exc

    stmt = select(User).where(User.id == user_uuid)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user"
        )
    return user


async def _resolve_by_bearer_jwt(
    db: AsyncSession, settings: Settings, authorization: str | None
) -> User:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization scheme (expected Bearer)",
        )
    token = authorization[len("Bearer "):]

    if not settings.jwks_url or not settings.CLERK_JWT_ISSUER:
        raise HTTPException(503, "Clerk JWT verification not configured")

    try:
        claims = await verify_jwt(
            token, jwks_url=settings.jwks_url, issuer=settings.CLERK_JWT_ISSUER
        )
    except InvalidJWT as exc:
        raise HTTPException(401, f"Invalid token: {exc}") from exc
    except JWKSFetchError as exc:
        raise HTTPException(503, f"Auth provider unavailable: {exc}") from exc

    clerk_sub = claims.get("sub")
    if not clerk_sub:
        raise HTTPException(401, "Token missing 'sub' claim")

    stmt = select(User).where(User.clerk_id == clerk_sub)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown user (webhook not delivered yet?)",
        )
    return user
```

- [ ] **Step 4: Run tests**

```bash
cd api && uv run pytest tests/test_deps.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add api/app/deps.py api/tests/test_deps.py
git commit -m "feat(deps): get_current_user routes Bearer JWT vs X-User-Id by env var"
```

---

## Task 8: `app/main.py` — startup validation (TDD)

**Files:**
- Modify: `api/app/main.py`
- Create: `api/tests/test_main_lifespan.py`

- [ ] **Step 1: Write failing tests**

Create `api/tests/test_main_lifespan.py`:

```python
"""Tests for app/main.py startup validation."""

from __future__ import annotations

import os

import pytest

from app.core.config import Settings, get_settings
from app.main import _validate_production_config


def test_production_without_clerk_keys_raises() -> None:
    s = Settings(
        ENV="production",
        DATABASE_URL="postgresql+asyncpg://x:y@h/d",
        REDIS_URL="redis://h",
        MASTER_KEK="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    )
    with pytest.raises(RuntimeError) as exc:
        _validate_production_config(s)
    assert "CLERK_SECRET_KEY" in str(exc.value)


def test_production_with_bypass_enabled_raises(monkeypatch) -> None:
    monkeypatch.setenv("WALLY_DEV_AUTH_BYPASS", "1")
    s = Settings(
        ENV="production",
        DATABASE_URL="postgresql+asyncpg://x:y@h/d",
        REDIS_URL="redis://h",
        MASTER_KEK="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        CLERK_SECRET_KEY="sk_x", CLERK_JWT_ISSUER="https://example.clerk", CLERK_WEBHOOK_SECRET="whsec_x",
    )
    with pytest.raises(RuntimeError) as exc:
        _validate_production_config(s)
    assert "WALLY_DEV_AUTH_BYPASS" in str(exc.value)


def test_dev_does_not_validate(monkeypatch) -> None:
    """Dev env doesn't enforce Clerk config or bypass restrictions."""
    monkeypatch.setenv("WALLY_DEV_AUTH_BYPASS", "1")
    s = Settings(
        ENV="dev",
        DATABASE_URL="postgresql+asyncpg://x:y@h/d",
        REDIS_URL="redis://h",
        MASTER_KEK="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    )
    # Should NOT raise
    _validate_production_config(s)


def test_production_with_full_clerk_config_and_no_bypass_passes(monkeypatch) -> None:
    monkeypatch.delenv("WALLY_DEV_AUTH_BYPASS", raising=False)
    s = Settings(
        ENV="production",
        DATABASE_URL="postgresql+asyncpg://x:y@h/d",
        REDIS_URL="redis://h",
        MASTER_KEK="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        CLERK_SECRET_KEY="sk_x", CLERK_JWT_ISSUER="https://example.clerk", CLERK_WEBHOOK_SECRET="whsec_x",
    )
    _validate_production_config(s)  # no raise
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd api && uv run pytest tests/test_main_lifespan.py -v
```

Expected: 4 failures (`ImportError: cannot import name '_validate_production_config'`).

- [ ] **Step 3: Implement in `api/app/main.py`**

Add at the top of the file (after existing imports):

```python
import os
```

Add this function before `lifespan`:

```python
def _validate_production_config(settings) -> None:
    """Refuse to boot in production if Clerk config is missing or bypass is on.

    Raises RuntimeError on any misconfiguration.
    """
    if settings.ENV != "production":
        return
    missing = [
        k
        for k in ("CLERK_SECRET_KEY", "CLERK_JWT_ISSUER", "CLERK_WEBHOOK_SECRET")
        if not getattr(settings, k)
    ]
    if missing:
        raise RuntimeError(
            f"Production requires Clerk config; missing: {missing}"
        )
    if os.getenv("WALLY_DEV_AUTH_BYPASS") == "1":
        raise RuntimeError(
            "WALLY_DEV_AUTH_BYPASS must NOT be '1' in production"
        )
```

Modify `lifespan` to call it:

```python
@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    settings = get_settings()
    _validate_production_config(settings)
    log.info("api.startup", version=__version__, env=settings.ENV)
    yield
    log.info("api.shutdown")
```

- [ ] **Step 4: Run tests**

```bash
cd api && uv run pytest tests/test_main_lifespan.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add api/app/main.py api/tests/test_main_lifespan.py
git commit -m "feat(main): production startup validation (Clerk config + bypass guard)"
```

---

## Task 9: `conftest.py` — set bypass for all tests + clerk_authed_client fixture

**Files:**
- Modify: `api/tests/conftest.py`

- [ ] **Step 1: Edit `api/tests/conftest.py` to set bypass autouse**

Add this near the existing `os.environ.setdefault` block:

```python
# All tests run with the bypass enabled — get_current_user uses X-User-Id header.
# Tests that explicitly want to exercise the production Bearer path use the
# `clerk_authed_client` fixture defined below.
os.environ.setdefault("WALLY_DEV_AUTH_BYPASS", "1")
```

Then add the fixture at the end of the file:

```python
@pytest.fixture
def clerk_authed_client(monkeypatch, async_client):
    """Async client where verify_jwt is mocked to return synthetic claims.

    Use this when you want to test the production Bearer JWT path explicitly.
    Default `clerk_id` is `clerk_test_user`; override via the returned setter.
    """
    from unittest.mock import AsyncMock
    monkeypatch.setenv("WALLY_DEV_AUTH_BYPASS", "0")

    state = {"clerk_id": "clerk_test_user", "claims": {}}

    def set_user(clerk_id: str, **extra_claims) -> None:
        state["clerk_id"] = clerk_id
        state["claims"] = extra_claims

    async def fake_verify(token, *, jwks_url, issuer):
        return {"sub": state["clerk_id"], **state["claims"]}

    monkeypatch.setattr("app.deps.verify_jwt", fake_verify)

    async_client.set_clerk_user = set_user  # type: ignore[attr-defined]
    return async_client
```

- [ ] **Step 2: Run the FULL test suite to verify nothing broke**

```bash
cd api && uv run pytest -v
```

Expected: all existing tests + the new ones from Tasks 2-8 pass. Roughly ~42-46 tests.

If existing tests fail, the most likely cause is the `WALLY_DEV_AUTH_BYPASS` env var not being set early enough (Settings reads at import time but the bypass var is read each call via `get_settings`). Verify by running just `tests/test_signals.py` (or whichever existing test failed) in isolation — it should pass.

- [ ] **Step 3: Commit**

```bash
git add api/tests/conftest.py
git commit -m "test(api): autouse WALLY_DEV_AUTH_BYPASS=1 + clerk_authed_client fixture"
```

---

## Task 10: Regenerate router stubs to add `auth.md`

**Files:**
- Create: `docs/api/routers/auth.md` (auto-generated)

- [ ] **Step 1: Run the generator**

```bash
cd /Users/josecampos/Documents/wally-trader
api/.venv/bin/python docs/api/_generate_stubs.py
```

Expected: silently writes `docs/api/routers/auth.md` (because the auth router is now registered).

- [ ] **Step 2: Verify the file was created**

```bash
ls docs/api/routers/auth.md
grep "AUTOGEN:START" docs/api/routers/auth.md
```

Expected: file exists with at least one AUTOGEN block (for `POST /api/v1/auth/webhook`).

- [ ] **Step 3: Verify --check passes**

```bash
api/.venv/bin/python docs/api/_generate_stubs.py --check
echo "Exit: $?"
```

Expected: 0.

- [ ] **Step 4: Commit**

```bash
git add docs/api/routers/auth.md
git commit -m "docs(api): generate auto stub for /auth/webhook router"
```

---

## Task 11: Hand-fill `docs/api/routers/auth.md` ✍️ sections

**Files:**
- Modify: `docs/api/routers/auth.md`

- [ ] **Step 1: Replace the placeholder block under `POST /api/v1/auth/webhook` with**

```markdown
**Cuándo usar:**
- Configurar como webhook destination en el Clerk dashboard (Settings → Webhooks → Add endpoint)
- Eventos suscritos: `user.created`, `user.updated`, `user.deleted` (otros se ignoran con 200 OK)
- Re-deliveries automáticas por Clerk si el handler retorna no-2xx en <30s

**Reglas Wally Trader que aplican:**
- **Endpoint público** — NO requiere `Authorization` header (lo autentica la firma svix)
- Verificación de firma con `svix>=1.40.0` usando `CLERK_WEBHOOK_SECRET`
- Idempotente: `user.created` duplicado → 200 + `duplicate:true`. `user.deleted` sobre row inexistente → 200 + `not_found:true`
- `user.deleted` HARD delete con CASCADE: destruye `profiles`+`signals`+`equity_points`+`api_keys`+`subscription` del usuario
- En production sin `CLERK_WEBHOOK_SECRET` → 503 (NO crashea el servidor — failsafe para evitar perder requests cuando se rota la key)

**Ejemplo curl** (test local con secret dummy — production lo dispara Clerk):

```bash
# Genera una firma válida con el helper python svix:
python -c "
import json, time, uuid
from svix.webhooks import Webhook
secret = 'whsec_test_dummy_secret'
payload = {'type':'user.created','data':{'id':'user_x','email_addresses':[{'id':'e','email_address':'a@b.com'}],'primary_email_address_id':'e','first_name':'A','last_name':'B'}}
body = json.dumps(payload).encode()
msg_id = f'msg_{uuid.uuid4().hex[:20]}'
ts = str(int(time.time()))
sig = Webhook(secret).sign(msg_id, int(ts), body)
print(f'curl -X POST http://localhost:8000/api/v1/auth/webhook \\\\\n  -H \"svix-id: {msg_id}\" \\\\\n  -H \"svix-timestamp: {ts}\" \\\\\n  -H \"svix-signature: {sig}\" \\\\\n  -H \"content-type: application/json\" \\\\\n  -d {json.dumps(payload)!r}')
"
```

**Ejemplo TypeScript (Clerk client SDK):**

```typescript
// El backend NO se llama directamente desde TS — Clerk dispara este webhook server-to-server.
// Para testing local podés usar `svix-cli` o ngrok+Clerk dashboard.
// Si querés simular en un test e2e:
import { Webhook } from "svix";
const wh = new Webhook(process.env.CLERK_WEBHOOK_SECRET!);
const body = JSON.stringify({ type: "user.created", data: { /* ... */ } });
const headers = wh.sign("msg_test_1", Math.floor(Date.now() / 1000), body);
await fetch("http://localhost:8000/api/v1/auth/webhook", {
  method: "POST",
  headers: { ...headers, "content-type": "application/json" },
  body,
});
```

**Errores típicos en este endpoint:**
- `400 Missing svix-* headers` — Clerk no incluyó las 3 headers (revisar configuración del webhook en Clerk dashboard)
- `400 Invalid JSON body` — body no parseable
- `400 Malformed event payload (missing type or data)` — schema inesperado
- `401 Invalid webhook signature` — secret en `.env` distinto al del Clerk dashboard
- `503 Webhook secret not configured` — `CLERK_WEBHOOK_SECRET` no seteado en el ambiente (raro en production por la startup validation)

**Ver también:**
- [AUTH.md](../AUTH.md) — flow general de auth
- `app/security/webhook.py` — código del dispatcher + handlers
- Clerk dashboard → Webhooks → "Logs" para ver re-deliveries y status
```

- [ ] **Step 2: Verify --check passes**

```bash
cd /Users/josecampos/Documents/wally-trader
api/.venv/bin/python docs/api/_generate_stubs.py --check
```

Expected: 0.

- [ ] **Step 3: Commit**

```bash
git add docs/api/routers/auth.md
git commit -m "docs(api): hand-fill auth.md with svix curl helper + dashboard guidance"
```

---

## Task 12: Update `docs/api/AUTH.md` with Phase 2 narrative

**Files:**
- Modify: `docs/api/AUTH.md`

- [ ] **Step 1: Use Write tool to OVERWRITE `docs/api/AUTH.md` with**

```markdown
# Auth — Phase 2 (Clerk JWT) + dev bypass

## Estado actual (Phase 2)

Todos los endpoints `/api/v1/*` requieren un Clerk JWT en el header `Authorization: Bearer <jwt>`, excepto:
- `GET /healthz`
- `GET /api/v1/ping`
- `GET /api/v1/agents`
- `POST /api/v1/auth/webhook` (autenticado por firma svix, no por JWT)

**Production flow:**
1. Frontend autentica al usuario via Clerk client SDK
2. Frontend obtiene un JWT (template default de Clerk) y lo manda en cada request: `Authorization: Bearer <jwt>`
3. Backend (`app/deps.py:get_current_user`) verifica el JWT contra los JWKS públicos de Clerk (cached 1h)
4. Si claims válidos: lookup `users WHERE clerk_id = jwt.sub` → return User row
5. Si user no existe en la DB: 401 "Unknown user (webhook not delivered yet?)" — significa que el `user.created` webhook todavía no llegó

**Webhook sync:**
- Clerk dashboard → Webhooks → Add endpoint apuntando a `https://api.tudominio/api/v1/auth/webhook`
- Subscribed events: `user.created`, `user.updated`, `user.deleted`
- Backend procesa con verificación de firma svix
- Eventos no-user.* se ignoran con 200 OK (no triggear retries)

**Errores HTTP:**

| Caso | Status | Detail |
|---|---|---|
| Falta `Authorization` header | 401 | "Missing Authorization header" |
| Header no empieza con `Bearer ` | 401 | "Invalid Authorization scheme (expected Bearer)" |
| JWT decode falla (firma, exp, iss) | 401 | "Invalid token: <pyjwt-message>" |
| JWKS endpoint Clerk down | 503 | "Auth provider unavailable" |
| Token válido pero `clerk_id` no existe en `users` | 401 | "Unknown user (webhook not delivered yet?)" |

## Dev/test bypass

Para desarrollo local o tests automatizados sin necesitar un JWT real de Clerk:

```bash
export WALLY_DEV_AUTH_BYPASS=1
```

Con esa env var setada, `get_current_user` acepta el header `X-User-Id: <uuid>` (mismo path que Phase 1 stub). Útil para:
- Local dev sin internet a Clerk
- Tests automatizados con seed users en la DB
- Smoke tests después de un deploy en staging

**⚠️ En production, esta env var NO debe estar seteada.** El startup validation en `app/main.py:lifespan` refuse to boot si `ENV=production` y `WALLY_DEV_AUTH_BYPASS=1` están ambos presentes.

## Setup local para testing

1. Crea un user en Clerk dashboard manualmente
2. En tu DB local: `INSERT INTO users (id, clerk_id, email, plan_tier, created_at) VALUES ('550e8400-...', 'user_clerk_xyz', 'dev@local', 'beta', now());`
3. Setea bypass:
   ```bash
   export WALLY_DEV_AUTH_BYPASS=1
   export USER_ID=550e8400-e29b-41d4-a716-446655440000
   ```
4. Hace requests con el header bypass:
   ```bash
   curl -H "X-User-Id: $USER_ID" http://localhost:8000/api/v1/profiles
   ```

## Setup para production-like testing (sin bypass)

1. En Clerk dashboard → Configure → JWT Templates → copia el `Issuer` URL → set como `CLERK_JWT_ISSUER` en `.env`
2. Set `CLERK_SECRET_KEY` y `CLERK_PUBLISHABLE_KEY`
3. En Webhooks → Add endpoint → copia el "Signing Secret" → set como `CLERK_WEBHOOK_SECRET`
4. Asegurate de NO tener `WALLY_DEV_AUTH_BYPASS` seteado
5. Frontend Clerk client emite el JWT, mandalo como `Authorization: Bearer <jwt>` en el request

## Configuración requerida en production

| Env var | Required en prod | Source |
|---|---|---|
| `CLERK_SECRET_KEY` | ✓ | Clerk dashboard → API Keys |
| `CLERK_PUBLISHABLE_KEY` | ✓ | Clerk dashboard → API Keys (frontend lo usa también) |
| `CLERK_JWT_ISSUER` | ✓ | Clerk dashboard → JWT Templates → Issuer |
| `CLERK_WEBHOOK_SECRET` | ✓ | Clerk dashboard → Webhooks → Signing Secret |
| `WALLY_DEV_AUTH_BYPASS` | ✗ NUNCA | (no setear) |

Si alguna de las 4 primeras falta en `ENV=production`, el servidor falla al arrancar (`RuntimeError: Production requires Clerk config; missing: [...]`).
```

- [ ] **Step 2: Commit**

```bash
git add docs/api/AUTH.md
git commit -m "docs(api): AUTH.md updated for Phase 2 Clerk JWT + bypass"
```

---

## Task 13: Update `docs/api/MANUAL.md`

**Files:**
- Modify: `docs/api/MANUAL.md`

- [ ] **Step 1: Read current state to find the right insertion points**

```bash
cat docs/api/MANUAL.md
```

You'll see: a header noting "Phase 1, requires X-User-Id header" + endpoint table + orphan models + roadmap.

- [ ] **Step 2: Update the description line under `# Wally Trader API — Tabla maestra`**

Find:
```markdown
19 endpoints implementados (Phase 1, requires `X-User-Id` header excepto donde se indica).
```

Replace with:
```markdown
20 endpoints implementados (Phase 2, requires `Authorization: Bearer <Clerk-JWT>` header excepto donde se indica). En dev/test usá `WALLY_DEV_AUTH_BYPASS=1` + `X-User-Id` header — ver [AUTH.md](AUTH.md).
```

- [ ] **Step 3: Add the new endpoint row in the table**

Find the row for `GET | /api/v1/agents`. Insert ABOVE it (so auth shows up first per OpenAPI ordering):

```markdown
| POST | `/api/v1/auth/webhook` | Recibe webhooks Clerk (user.created/updated/deleted) — público autenticado por firma svix | [auth.md](routers/auth.md) |
```

- [ ] **Step 4: Update the Roadmap section — mark #1 as done**

Find:
```markdown
- **#1 Auth** — Clerk + JWT + multi-tenant guards (reemplaza `X-User-Id` stub)
```

Replace with:
```markdown
- ✅ **#1 Auth** — Clerk + JWT + webhook sync (DONE — ver [AUTH.md](AUTH.md))
```

- [ ] **Step 5: Commit**

```bash
git add docs/api/MANUAL.md
git commit -m "docs(api): MANUAL.md adds /auth/webhook + marks #1 done"
```

---

## Task 14: Update `api/README.md`

**Files:**
- Modify: `api/README.md`

- [ ] **Step 1: Read current state**

```bash
head -25 api/README.md
```

You'll see the Phase 1 status callout block-quote.

- [ ] **Step 2: Replace the Status block-quote**

Find:
```markdown
> **Status: Phase 1.** Auth is via the `X-User-Id` header stub
> (`app/deps.py:get_current_user`). **Do not expose to public internet
> with this config** — the header is trivial to spoof. See
> [`../docs/api/AUTH.md`](../docs/api/AUTH.md) for details and the path
> to Clerk JWT in sub-project #1.
```

Replace with:
```markdown
> **Status: Phase 2.** Auth is real Clerk JWT verification (`app/security/clerk.py` +
> `app/deps.py:get_current_user`). Production-ready — startup validation refuses
> to boot if Clerk env vars are missing or `WALLY_DEV_AUTH_BYPASS=1` is set in prod.
> Dev/test bypass via `WALLY_DEV_AUTH_BYPASS=1` + `X-User-Id` header. See
> [`../docs/api/AUTH.md`](../docs/api/AUTH.md).
```

- [ ] **Step 3: Mark sub-project #1 done in the Roadmap table**

Find the row in the Roadmap table:
```markdown
| #1 | Auth — Clerk + JWT + multi-tenant guards | Reemplaza el stub `X-User-Id`. Bloquea #2/#3/#4/#5. |
```

Replace with:
```markdown
| ✅ #1 | Auth — Clerk + JWT + webhook sync (DONE) | Reemplaza el stub `X-User-Id`. Desbloquea #2/#3/#4/#5. |
```

- [ ] **Step 4: Commit**

```bash
git add api/README.md
git commit -m "docs(api): README Phase 2 status + roadmap #1 ✅"
```

---

## Task 15: Final verification — DoD checklist

**Files:** _(no changes; verification only)_

- [ ] **Step 1: Run the FULL test suite**

```bash
cd /Users/josecampos/Documents/wally-trader/api && uv run pytest -v
```

Expected: ~42 tests pass (25 existing + 17 new across test_clerk.py, test_auth_webhook.py, test_deps.py, test_config_clerk.py, test_main_lifespan.py).

- [ ] **Step 2: Verify drift gate**

```bash
cd /Users/josecampos/Documents/wally-trader
api/.venv/bin/python docs/api/_generate_stubs.py --check
```

Expected: exit 0.

- [ ] **Step 3: Verify all 16 DoD items from spec**

```bash
cd /Users/josecampos/Documents/wally-trader

# DoD-1: clerk.py exists with verify_jwt + _fetch_jwks
grep -q "def verify_jwt" api/app/security/clerk.py && echo "DOD-1 PASS"

# DoD-2: auth.py exists with /webhook
grep -q "POST.*webhook\|router.post.*webhook" api/app/api/v1/auth.py && echo "DOD-2 PASS"

# DoD-3: webhook.py with dispatch_event + 3 handlers
grep -q "dispatch_event\|handle_user_created\|handle_user_updated\|handle_user_deleted" api/app/security/webhook.py && echo "DOD-3 PASS"

# DoD-4: deps.py routes by env var
grep -q "WALLY_DEV_AUTH_BYPASS" api/app/deps.py && echo "DOD-4 PASS"

# DoD-5: main.py validates production
grep -q "_validate_production_config" api/app/main.py && echo "DOD-5 PASS"

# DoD-6: jwks_url property
grep -q "def jwks_url\|jwks_url:" api/app/core/config.py && echo "DOD-6 PASS"

# DoD-7: pyproject deps
grep -q "svix" api/pyproject.toml && grep -q "respx" api/pyproject.toml && echo "DOD-7 PASS"

# DoD-8: conftest bypass
grep -q "WALLY_DEV_AUTH_BYPASS" api/tests/conftest.py && echo "DOD-8 PASS"

# DoD-9: 5+8+4 tests in the 3 new files
TC=$(grep -c "^def test_\|^async def test_" api/tests/test_clerk.py)
TW=$(grep -c "^def test_\|^async def test_" api/tests/test_auth_webhook.py)
TD=$(grep -c "^def test_\|^async def test_" api/tests/test_deps.py)
echo "DOD-9 test counts: clerk=$TC webhook=$TW deps=$TD"

# DoD-10: existing tests still pass — covered by Step 1 above

# DoD-11: AUTH.md updated
grep -q "Phase 2" docs/api/AUTH.md && echo "DOD-11 PASS"

# DoD-12: --check passes — covered by Step 2 above

# DoD-13: auth.md handfilled
! grep -q "_(rellenar)_" docs/api/routers/auth.md && echo "DOD-13 PASS (no _(rellenar)_ left)"

# DoD-14: MANUAL.md updated
grep -q "/auth/webhook" docs/api/MANUAL.md && grep -q "✅ \*\*#1" docs/api/MANUAL.md && echo "DOD-14 PASS"

# DoD-15: README Phase 2
grep -q "Phase 2" api/README.md && grep -q "✅ #1" api/README.md && echo "DOD-15 PASS"

# DoD-16: full pytest count >= 42 — covered by Step 1
```

- [ ] **Step 4: Report**

If any DoD item fails, report which and pause. Otherwise: ALL GREEN. Branch is ready to be merged or PR'd.

Do NOT do `gh pr create` or merge — that's the user's call via `superpowers:finishing-a-development-branch` skill afterwards.
