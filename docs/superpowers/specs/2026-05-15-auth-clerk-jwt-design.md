# Auth — Clerk JWT + Webhook Sync — Design Spec

**Date:** 2026-05-15
**Status:** Approved (brainstorming complete, ready for implementation plan)
**Source:** User request "dale" after merge of sub-project #0 (API manual + audit). Auth was identified as sub-project #1 of the SaaS roadmap and the blocker for #2/#3/#4/#5.
**Scope decision:** Replace `X-User-Id` header stub with Clerk JWT verification (production hard requirement) + webhook handler for `user.*` events; preserve dev/test bypass via env var.

## Context & motivation

After completing sub-project #0, the API in `api/` is fully documented but auth is still stubbed:

```python
# app/deps.py:get_current_user (current state)
async def get_current_user(
    db: AsyncSession = Depends(get_db_session),
    x_user_id: str | None = Header(default=None, description="Dev-only override"),
) -> User:
    if x_user_id is None:
        raise HTTPException(401, "Missing X-User-Id header (...)")
    # ... lookup by UUID ...
```

This is the only thing standing between the API and "can be safely exposed publicly". The header is trivial to spoof — anyone can set `X-User-Id: <any uuid>` and impersonate that user. Sub-projects #2 (brokers), #3 (websockets), #4 (billing), and #5 (audit) all assume `current_user` reflects a real authenticated identity, so this is a strict prerequisite.

The codebase already has the scaffolding ready:
- `app/models/user.py` has `clerk_id: str` (unique indexed) and `email: str` columns
- `app/core/config.py` already declares `CLERK_SECRET_KEY`, `CLERK_PUBLISHABLE_KEY`, `CLERK_JWT_ISSUER`, `CLERK_WEBHOOK_SECRET` as optional Settings
- `pyjwt>=2.10.0` and `httpx>=0.28.0` are already in `api/pyproject.toml`
- `BETA_ALLOWED_EMAILS: list[str]` exists for beta gating (NOT used in this spec — see below)

Decisions during brainstorming session 2026-05-15:
- **Clerk readiness:** User has Clerk account ready with the 4 keys → hard requirement in production
- **Webhook signature lib:** Use `svix>=1.40.0` (Clerk's official pattern, avoids manual HMAC bugs)
- **Beta gating:** Done in Clerk dashboard (allowlist there). Backend trusts everything that arrives — does NOT use `BETA_ALLOWED_EMAILS` env var (which becomes vestigial; cleanup deferred to #5)
- **Dev/test escape hatch:** `X-User-Id` header path stays, gated by `WALLY_DEV_AUTH_BYPASS=1` env var. Off in production
- **Webhook events:** Only `user.created`, `user.updated`, `user.deleted` (HARD delete via cascade). Other event types return 200 + log (no retries triggered)
- **Multi-tenant guards:** Application-layer only for now (existing `WHERE user_id = current_user.id` pattern). Postgres RLS deferred to sub-project #5

## Goals

1. Make the API safe to expose publicly behind a Clerk-protected frontend
2. Sync user lifecycle from Clerk webhooks so the local `users` table is always consistent with Clerk's source of truth
3. Preserve the existing `X-User-Id` flow as a test/dev bypass (no test rewrites needed in this sub-project)
4. Fail loud at startup when production is misconfigured (no Clerk keys)
5. Keep the implementation small enough to fit one PR (~3-4 days work)

## Non-goals (explicit)

- Frontend integration (React/Next.js Clerk SDK setup, login pages, etc.) — frontend is responsibility of a separate consumer
- Beta access enforcement in the backend — Clerk dashboard handles allowlist
- `session.*` webhook events (login/logout audit) — sub-project #5
- `last_login_at` field on User — sub-project #5
- Postgres Row-Level Security (RLS) — sub-project #5
- API keys / Personal Access Tokens (long-lived non-JWT auth) — possibly future #6
- RBAC / roles / permissions — every authenticated user has the same access scope to their own resources
- Clerk Organizations support (multi-tenant via orgs) — User stays single-tenant
- Cleanup of vestigial `BETA_ALLOWED_EMAILS` env var (deferred — Settings remains permissive)
- Rotation of `MASTER_KEK` (orthogonal — already documented in config.py)

## Architecture

```
docs/api/
└── routers/auth.md                          # auto-generated stub + ✍️ hand-fill (Task 13 of plan)

api/
├── pyproject.toml                           # + svix>=1.40.0  + respx>=0.21.0 (test)
├── app/
│   ├── api/v1/
│   │   ├── __init__.py                      # + include_router(auth_router)
│   │   └── auth.py                          # NEW — POST /api/v1/auth/webhook
│   ├── core/
│   │   └── config.py                        # + jwks_url property + production validation hook
│   ├── deps.py                              # REFACTOR — Bearer JWT path + bypass header path
│   ├── main.py                              # MODIFIED — lifespan validates Clerk env vars in production
│   └── security/
│       ├── clerk.py                         # NEW — pure-logic verify_jwt() + JWKS cache
│       └── webhook.py                       # NEW — svix verify + 3 user.* handlers
└── tests/
    ├── conftest.py                          # MODIFIED — set WALLY_DEV_AUTH_BYPASS=1 + clerk_authed_client fixture
    ├── test_clerk.py                        # NEW — verify_jwt unit tests
    ├── test_auth_webhook.py                 # NEW — webhook integration tests
    └── test_deps.py                         # NEW — get_current_user routing logic tests
```

## Auth flow — production (`ENV=production`)

```
HTTP Request with Authorization: Bearer <jwt>
        │
        ▼
FastAPI route → Depends(get_current_user)
        │
        ▼
deps.py: read Authorization header
        │
        ▼
security/clerk.py: verify_jwt(token)
        │
        ├─ Fetch JWKS from settings.jwks_url (TTL-cached 1h, async_lru or asyncache)
        ├─ Decode JWT header → extract kid (key id)
        ├─ Pick matching JWK from set; raise InvalidJWT if no match
        ├─ pyjwt.decode(token, key, algorithms=["RS256"], issuer=CLERK_JWT_ISSUER)
        ├─ Validate: exp (jwt lib), iat (jwt lib), iss (jwt lib)
        └─ Return claims dict {sub: "user_xxx", email: "...", ...}
        │
        ▼
Lookup User WHERE clerk_id = claims["sub"]
        │
        ├─ Found → return User
        └─ Not found → 401 "Unknown user (webhook not delivered yet?)"
```

Failure modes mapped to HTTP responses:

| Failure | Status | Detail |
|---|---|---|
| Missing `Authorization` header | 401 | "Missing Authorization header" |
| Header doesn't start with `Bearer ` | 401 | "Invalid Authorization scheme" |
| JWT decode fails (signature, exp, iss, malformed) | 401 | "Invalid token: <pyjwt-message>" |
| JWKS fetch fails (Clerk down) | 503 | "Auth provider unavailable" |
| Token valid but `clerk_id` not in `users` table | 401 | "Unknown user" |

## Auth flow — dev/test (`WALLY_DEV_AUTH_BYPASS=1`)

```
HTTP Request with X-User-Id: <uuid>
        │
        ▼
deps.py: bypass enabled → read X-User-Id header
        │
        ▼
Lookup User WHERE id = uuid → return or 401 (existing behavior)
```

The bypass env var is read at module-load via Settings. In `ENV=production`, the validation hook (see below) refuses to start if the bypass is enabled — defense in depth so a misconfig doesn't leave the bypass active in prod.

## JWKS cache strategy

- Fetched on first request to `verify_jwt`
- Cached in process memory with TTL 1h (`asyncache.TTLCache(maxsize=1, ttl=3600)` or equivalent)
- Cache miss + Clerk down → propagate 503 (better than serving forever-stale keys)
- Key rotation: Clerk JWKS endpoint typically returns multiple keys during rotation period — `verify_jwt` looks up by `kid` claim in the JWT header → naturally supports rollover without code changes
- Multi-pod deployment: each pod has its own cache (no shared Redis cache needed — JWKS is small, refresh is cheap)

## Webhook handler

**Endpoint:** `POST /api/v1/auth/webhook`

**Required headers** (Clerk via Svix):
- `svix-id` — `msg_<uuid>` message identifier
- `svix-timestamp` — Unix epoch seconds
- `svix-signature` — `v1,<base64>` HMAC

**Verification flow:**

```python
@router.post("/webhook", status_code=200)
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_db_session)):
    body = await request.body()  # MUST be raw bytes for signature
    headers = {
        "svix-id": request.headers.get("svix-id"),
        "svix-timestamp": request.headers.get("svix-timestamp"),
        "svix-signature": request.headers.get("svix-signature"),
    }
    if not all(headers.values()):
        raise HTTPException(400, "Missing svix-* headers")
    try:
        wh = Webhook(settings.CLERK_WEBHOOK_SECRET.get_secret_value())
        payload = wh.verify(body, headers)  # WebhookVerificationError if invalid
    except WebhookVerificationError:
        raise HTTPException(401, "Invalid webhook signature")
    return await dispatch_event(payload, db)
```

**Event dispatch:**

```python
EVENT_HANDLERS = {
    "user.created": handle_user_created,
    "user.updated": handle_user_updated,
    "user.deleted": handle_user_deleted,
}

async def dispatch_event(payload: dict, db: AsyncSession) -> dict:
    event_type = payload.get("type")
    handler = EVENT_HANDLERS.get(event_type)
    if handler is None:
        log.info("clerk.webhook.skipped", event_type=event_type)
        return {"status": "skipped", "reason": "unknown_event_type"}
    return await handler(payload["data"], db)
```

**Per-event behavior:**

| Event | Logic |
|---|---|
| `user.created` | Extract `id` (clerk_id), `email_addresses[0].email_address`, `first_name + last_name`. INSERT row. If `clerk_id` already exists (race / retry) → return 200 with `{"status":"ok","duplicate":true}`. If `email_addresses` empty → log warning + return 200 + skip. |
| `user.updated` | Lookup by `clerk_id` → UPDATE `email`, `name`. If not found (out-of-order delivery) → INSERT (treat as upsert). |
| `user.deleted` | Lookup by `clerk_id` → `db.delete(user)` → cascade destroys `profiles`+`signals`+`equity_points`+`api_keys`+`subscription` via FKs. If not found → return 200 with `{"status":"ok","not_found":true}`. |

**Idempotency:** All three handlers tolerate retries safely. Clerk retries non-2xx for ~30 seconds, so we always return 2xx unless signature verification fails (401) or body is malformed (400).

**Error mapping:**

| Case | Status | Body |
|---|---|---|
| Missing `svix-*` headers | 400 | `{"detail": "Missing svix-* headers"}` |
| Invalid signature | 401 | `{"detail": "Invalid webhook signature"}` |
| Body not valid JSON | 400 | `{"detail": "Invalid JSON body"}` |
| Schema missing `type` or `data` | 400 | `{"detail": "Malformed event payload"}` |
| Unknown event type | 200 | `{"status": "skipped", "reason": "unknown_event_type"}` |
| `created` IntegrityError (duplicate) | 200 | `{"status": "ok", "duplicate": true}` |
| Database connection lost | 500 | (default FastAPI handler — Clerk will retry) |

**Multi-email accounts:** Clerk's `email_addresses` is an array. Find the entry where `id == primary_email_address_id` (top-level field on `data`); fall back to `[0]` only if no match. If the array is empty → log warning + skip user creation (cannot create User without email).

## Startup validation

In `app/main.py:lifespan`:

```python
if settings.ENV == "production":
    missing = [
        k for k in ("CLERK_SECRET_KEY", "CLERK_JWT_ISSUER", "CLERK_WEBHOOK_SECRET")
        if not getattr(settings, k)
    ]
    if missing:
        raise RuntimeError(f"Production requires Clerk config: {missing}")
    if os.getenv("WALLY_DEV_AUTH_BYPASS") == "1":
        raise RuntimeError("WALLY_DEV_AUTH_BYPASS must NOT be set in production")
```

This catches the most dangerous misconfig — bypass left enabled in prod — at boot rather than on first request.

## Test strategy

| File | Type | Coverage |
|---|---|---|
| `test_clerk.py` | Unit | `verify_jwt(token)` happy path with mocked JWKS (via `respx`); 4 failure modes: expired, invalid signature, unknown `kid`, wrong issuer |
| `test_auth_webhook.py` | Integration | Build valid svix-signed request via `svix.Webhook.sign()`; assert all 3 user.* handlers run end-to-end; assert invalid signature → 401; assert unknown event_type → 200 + skipped; assert duplicate `user.created` → 200 + `duplicate:true` |
| `test_deps.py` | Unit (mocked DB) | `get_current_user` routing: bypass on → reads `X-User-Id` (existing path); bypass off → requires Bearer; missing Bearer → 401; valid JWT but unknown `clerk_id` → 401 |
| `conftest.py` REFACTOR | Test infra | Autouse fixture sets `WALLY_DEV_AUTH_BYPASS=1` for ALL tests; `clerk_authed_client` fixture mocks `verify_jwt` to return synthetic claims for tests that explicitly want to exercise the prod path |
| Existing tests (`test_signals.py`, `test_profiles.py`, etc.) | NO CHANGES | Continue using `X-User-Id` header — auto-bypassed by conftest |

Total expected: ~42 tests (25 existing + 17 new = 5 in `test_clerk.py` + 8 in `test_auth_webhook.py` + 4 in `test_deps.py`).

## Documentation updates

- `docs/api/AUTH.md` — replace Phase 1 narrative with Phase 2: Clerk JWT in production + bypass for dev. Update the curl examples to show `Authorization: Bearer <jwt>` instead of just `X-User-Id`.
- `docs/api/routers/auth.md` — auto-generated stub for POST `/api/v1/auth/webhook` + hand-filled ✍️ sections (Cuándo usar, Reglas Wally Trader, curl example using `svix sign`, TypeScript example for receiving Clerk webhooks)
- `docs/api/MANUAL.md` — add row for `POST /api/v1/auth/webhook`; remove the "Phase 1" narrative; mark sub-project #1 as ✅ in roadmap
- `api/README.md` — change Status callout from Phase 1 → Phase 2; mark sub-project #1 ✅ in roadmap table
- `docs/api/_generate_stubs.py --check` must pass after the doc updates

## Definition of Done

1. ✅ `app/security/clerk.py` exists with `verify_jwt(token: str) -> dict[str, Any]` + cached `_fetch_jwks()` helper
2. ✅ `app/api/v1/auth.py` exists with POST `/api/v1/auth/webhook` registered in v1 router
3. ✅ `app/security/webhook.py` exists with `dispatch_event` + 3 `user.*` handlers
4. ✅ `app/deps.py:get_current_user` handles BOTH paths (Bearer JWT + bypass header) gated by `WALLY_DEV_AUTH_BYPASS` env var
5. ✅ `app/main.py:lifespan` validates Clerk env vars in `ENV=production` and refuses to start if `WALLY_DEV_AUTH_BYPASS=1` is set in production
6. ✅ `app/core/config.py` adds `jwks_url` property derived from `CLERK_JWT_ISSUER`
7. ✅ `api/pyproject.toml` adds `svix>=1.40.0` and `respx>=0.21.0` (test dep)
8. ✅ `api/tests/conftest.py` sets `WALLY_DEV_AUTH_BYPASS=1` autouse and provides `clerk_authed_client` fixture
9. ✅ Tests added: `test_clerk.py` (5 tests), `test_auth_webhook.py` (8 tests), `test_deps.py` (4 tests) — all pass
10. ✅ Existing tests pass without modifications (signals, profiles, equity, agents, keys)
11. ✅ `docs/api/AUTH.md` updated with new mechanics
12. ✅ `docs/api/_generate_stubs.py --check` passes (auto-generated stub for the new auth router)
13. ✅ `docs/api/routers/auth.md` ✍️ sections hand-filled
14. ✅ `docs/api/MANUAL.md` updated with new endpoint row + roadmap status
15. ✅ `api/README.md` updated: Status → Phase 2; roadmap #1 ✅
16. ✅ Full pytest run: ~46 tests pass

## Estimated effort

3-4 days full-time:

- `clerk.py` JWT verify + JWKS cache + tests: ~4h
- `webhook.py` + svix integration + 3 handlers + tests: ~4h
- `deps.py` refactor + bypass env var + tests: ~2h
- `main.py` startup validation + config tweaks: ~1h
- `conftest.py` refactor + fixture: ~2h
- Doc updates (AUTH.md, auth.md, MANUAL.md, api/README.md): ~3h
- Buffer for "Clerk JWT format quirks" (template tokens vs session tokens, audience claim handling, `sub` format): ~4h
- Buffer for getting svix + httpx + AsyncClient interactions right in tests: ~2h

## Risks & mitigations

| Risk | Probability | Mitigation |
|---|---|---|
| Clerk JWT template missing expected claims (`sub`, `email`) | Medium | Spec assumes default Clerk template. If user customized → spec gets adjusted in plan-time |
| svix lib quirks with FastAPI raw body parsing | Low | Integration tests sign + verify end-to-end via the real svix lib |
| Existing tests break due to conftest env-var ordering race | Low | Use `monkeypatch.setenv` in autouse fixture (runs before each test), not module-level `os.environ[...] = ...` |
| JWKS cache stale after Clerk key rotation | Low | TTL 1h + `kid`-based key lookup naturally handles rollover |
| Production deploy without Clerk env vars | Low | Startup validation refuses to boot — fail-fast loud |
| `WALLY_DEV_AUTH_BYPASS=1` accidentally left in prod env | Low | Same startup validation refuses to boot |

## Future sub-projects (out of scope, listed for traceability)

| # | Sub-project | What this sub-project unblocks |
|---|---|---|
| #2 | Brokers — Bitunix/Binance/MT5 keys + sync | Now has user_id from real auth |
| #3 | WebSockets + Redis pubsub | Per-user channels keyed by authenticated user_id |
| #4 | Billing with Polar.sh | UsageEvent / Subscription rows attributable to real users |
| #5 | Audit + rate limit + observability | Includes session.* webhook events, last_login_at, Postgres RLS, BETA_ALLOWED_EMAILS cleanup |
