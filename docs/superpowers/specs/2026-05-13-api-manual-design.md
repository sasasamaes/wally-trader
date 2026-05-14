# API Manual + Audit — Design Spec

**Date:** 2026-05-13
**Status:** Approved (brainstorming complete, ready for implementation plan)
**Source:** User request "crear api y crear documentación o manual del api y endpoints como usarlos y en que caso de wally trader usar cada api"
**Scope decision:** First sub-project of the larger SaaS API completion roadmap (#0 of #0–#5). Audit + manual ONLY — no new endpoints implemented in this spec.

## Context & motivation

The user asked to "create the API + documentation". Audit revealed that an API already exists at `api/` (FastAPI + Python 3.13 + SQLAlchemy 2.0 + PostgreSQL) with **5 routers v1 implemented and fully working**, plus several stubbed-out files referenced by the README that **do not exist yet**.

The user clarified the end-state goal is a SaaS multi-user product, and we agreed to decompose the work into 6 sub-projects (#0–#5). This spec covers **only #0**.

The user's original ask ("manual" + "en qué caso de Wally Trader usar cada API") is best fulfilled by:

1. Documenting exhaustively the 5 routers that already exist
2. Mapping each endpoint to concrete Wally Trader scenarios (CLI workflows, signal validation, journal, etc.)
3. Establishing an anti-drift mechanism so the manual stays current as the codebase evolves
4. Correcting `api/README.md`, which currently advertises endpoints that do not exist

User decisions (brainstorming session 2026-05-13):
- **Sub-project ordering:** Start with #0 (this spec). #1 Auth (Clerk+JWT), #2 Brokers, #3 WebSockets, #4 Billing (Polar.sh, NOT Stripe), #5 Audit/RL/observability follow as separate spec→plan→implementation cycles.
- **Audience:** Self + future frontend devs. Spanish, technical-pragmatic tone.
- **Format:** Markdown in `docs/api/` + auto-generated OpenAPI from FastAPI. Not Mintlify/Scalar at this stage.
- **Code examples:** `curl` + TypeScript `fetch`. No Python/JS-only.
- **Use-case mapping:** BOTH inline "Cuándo usar" per endpoint AND a separate `SCENARIOS.md` catalog. Plus a `CLI_TO_API.md` mapping slash commands to endpoints.
- **Anti-drift:** Approach B — script introspects FastAPI app, regenerates the auto sections between markers, CI gate fails on drift.

## Goals

1. Make the existing API navigable and explainable — anyone (the user himself returning in 3 months, or a frontend dev joining) can find how to call endpoint X for scenario Y in under 30 seconds
2. Prevent docs from rotting via auto-generated schema sections + CI gate
3. Correct `api/README.md` so it stops claiming features that do not exist
4. Lay the groundwork (template + scenarios pattern) that sub-projects #1–#5 can extend incrementally instead of writing from scratch
5. Surface explicitly the 5 orphan models in the DB (`Subscription`, `UsageEvent`, `AuditLog`, `TradeBrokerSync`, `JournalEntry`) so future sub-projects know what's already wired vs what needs creating

## Non-goals (explicit)

- Implement new endpoints (auth, billing, brokers, ws, audit) — those are sub-projects #1–#5
- Document Clerk webhook payloads, Polar.sh integration, broker key flows — none exist yet
- Build a Mintlify/Scalar/Redocly site
- Translate to English (Spanish-only for this iteration; if SaaS launches publicly, English version is a separate task)
- Build a TypeScript SDK or React client library
- Create end-to-end tutorials ("build a trading bot in 10 min")
- Document `app/llm_gateway/` internals — that's an implementation detail consumed by `/agents/{name}/run`, not a public surface

## Audit findings (current state of `api/`)

### What's implemented and working

| Router | File | LOC | Endpoints |
|---|---|---|---|
| meta | `app/main.py`, `app/api/v1/__init__.py` | 53+23 | `GET /healthz`, `GET /api/v1/ping` |
| agents | `app/api/v1/agents.py` | 151 | `GET /agents`, `POST /agents/{name}/run` (SSE), `GET /agents/runs/{run_id}` |
| keys | `app/api/v1/keys.py` | 100 | `GET /keys/llm`, `POST /keys/llm`, `DELETE /keys/llm/{key_id}` |
| profiles | `app/api/v1/profiles.py` | 178 | `GET /profiles`, `POST /profiles`, `GET /profiles/{slug}`, `PATCH /profiles/{slug}`, `DELETE /profiles/{slug}` |
| signals | `app/api/v1/signals.py` | 244 | `GET /signals`, `POST /signals`, `PATCH /signals/{id}/outcome`, `GET /signals/{id}` |
| equity | `app/api/v1/equity.py` | 151 | `GET /equity`, `POST /equity/upsert` |

**Total endpoints to document: 19** (2 meta + 3 agents + 3 keys + 5 profiles + 4 signals + 2 equity).

### Auth state

`app/deps.py` (`get_current_user`) requires header `X-User-Id: <uuid>`. This is a **Phase 1 stub**, explicitly documented in the file as "Clerk JWT verification lands in Phase 1.5". This means the API is NOT exposed to the public internet today — only suitable for local dev and trusted-network usage.

### Six agents registered

`app/agents/__init__.py` registers: `regime`, `risk`, `signal_validator`, `multifactor`, `journal`, `sentiment`. Each is a port of the corresponding `.opencode/agents/` CLI subagent. Each implements `system_prompt()` + `user_prompt()` and streams via SSE.

### Orphan models (no endpoint, just DB rows)

| Model | File | Purpose | Belongs to sub-project |
|---|---|---|---|
| `Subscription` | `app/models/subscription.py` | Polar.sh plan tracking | #4 Billing |
| `UsageEvent` | `app/models/usage_event.py` | Metered LLM/agent usage events | #4 Billing |
| `AuditLog` | `app/models/audit_log.py` | Security/compliance trail | #5 Audit |
| `TradeBrokerSync` | `app/models/trade_broker_sync.py` | Broker → Signal reconciliation | #2 Brokers |
| `JournalEntry` | `app/models/journal_entry.py` | Daily journal output | Not in #1–#5 today. Will get its own mini-spec for `/journals` router (post-#5) once user confirms it should be a first-class API resource vs an artifact returned by `POST /agents/journal/run` |

The manual will list these in `MANUAL.md` under "Modelos huérfanos (sin endpoint)" so future contributors know they exist before designing new routers.

### README.md mismatches

`api/README.md` claims the following exist, but they do NOT:

- `auth.py` (Clerk webhook sync)
- `billing.py` (Stripe checkout + portal + webhooks)
- `brokers.py` (broker keys validation)
- `ws.py` (WebSocket hub)
- `app/brokers/` (bitunix, binance, mt5_bridge implementations)
- `app/billing/` (stripe_client, webhooks, meters)
- `app/security/audit.py`

Part of this spec's deliverable is to correct `api/README.md` so it stops misrepresenting reality. The corrected version will list only what's implemented + a "Roadmap (not implemented yet)" section that links to specs #1–#5 once they're written.

## Architecture

```
docs/api/
├── README.md                          # entry point — overview, quick start, índice
├── MANUAL.md                          # tabla maestra: 19 endpoints + 1-line cuándo usar
├── routers/
│   ├── meta.md                        # GET /healthz, GET /ping
│   ├── agents.md                      # 3 endpoints
│   ├── keys.md                        # 3 endpoints
│   ├── profiles.md                    # 5 endpoints
│   ├── signals.md                     # 4 endpoints
│   └── equity.md                      # 2 endpoints
├── SCENARIOS.md                       # 8+ flujos Wally Trader → endpoints
├── CLI_TO_API.md                      # tabla slash command → endpoints
├── AUTH.md                            # X-User-Id ahora + roadmap Clerk
├── ERRORS.md                          # convenciones HTTP errors + ejemplos
└── _generate_stubs.py                 # introspecta FastAPI, regenera AUTOGEN sections

api/
└── README.md                          # corregido — sin mentiras

.github/workflows/<existing-or-new>.yml # CI step: python docs/api/_generate_stubs.py --check
```

## Per-endpoint document template

Each endpoint section in `routers/<name>.md` follows this exact structure. Sections marked 🤖 are emitted by `_generate_stubs.py` between `<!-- AUTOGEN:START name=POST-signals -->` and `<!-- AUTOGEN:END name=POST-signals -->` markers. Sections marked ✍️ are hand-written and preserved across regenerations.

```markdown
### `<METHOD> /api/v1/<path>` — <Short title in Spanish>

🤖 **Method + Path + Tag** + **Auth** + **Status codes** + **Request body table** + **Response model**

✍️ **Cuándo usar:**
- (1-3 concrete Wally Trader scenarios)

✍️ **Reglas Wally Trader que aplican:**
- (Profile-specific caps, rate limits, business rules — e.g., "bitunix max 7 signals/día")

✍️ **Ejemplo curl:** (full working command with `X-User-Id` header)

✍️ **Ejemplo TypeScript (fetch):** (typed when reasonable)

✍️ **Errores típicos en este endpoint:** (status codes the user is most likely to hit)

✍️ **Ver también:** (links to related endpoints + SCENARIOS.md anchors)
```

The 🤖 block is rendered from FastAPI introspection:

- `path`, `method`, `tags` from the route metadata
- Auth from the `Depends(get_current_user)` presence (constant for v1; if absent, label "Public")
- Status codes from `responses=` decorator + a sane default for the success case
- Request body table from the Pydantic v2 schema (`.model_json_schema()` → walk `properties`/`required`)
- Response model from `response_model=` parameter

## SCENARIOS.md catalog (initial 8 scenarios)

Each scenario is one chapter with: trigger, pre-conditions, step-by-step pipeline (with endpoint links), required rule checks, and a TypeScript snippet showing the orchestration.

Initial 8 scenarios — these are the floor for DoD. The plan may add 1–2 more if it finds obvious gaps, but cannot remove any of these eight without coming back here for an amendment:

1. **Morning routine multi-profile** — `GET /profiles?include_metrics=true` + per profile `GET /equity?from_date=today-7d` + `POST /agents/regime/run` for the day's primary symbol
2. **Validar señal Discord punkchainer's (bitunix)** — `GET /profiles/bitunix` → `POST /agents/signal_validator/run` (SSE) → if GO `POST /signals` with `source="punkchainer_discord"`
3. **Autohunt: cazar setup propio (bitunix)** — `POST /agents/regime/run` → if RANGE_CHOP `POST /agents/multifactor/run` → if score≥70 `POST /signals` with `source="self_generated"`
4. **Cerrar trade y journal (cualquier profile)** — `PATCH /signals/{id}/outcome` → `POST /agents/journal/run` (genera markdown del día) → `POST /equity/upsert`
5. **Dashboard multi-profile (frontend)** — `GET /profiles?include_metrics=true` → por cada profile mostrar capital, WR, PF, PnL día, drawdown
6. **Gestionar LLM keys (BYOK setup inicial)** — `POST /keys/llm` para anthropic + openai → `GET /keys/llm` para confirmar last4 → eventually rotate via `DELETE /keys/llm/{id}` + `POST /keys/llm`
7. **Recuperar agent run histórico** — Caso: el SSE se cortó a media corrida. Frontend tiene `run_id` del primer evento `run_started`. `GET /agents/runs/{run_id}` para ver el resultado final + cost.
8. **Equity tracking manual (FTMO/FundingPips)** — Caso: brokers no integrados aún (sub-proyecto #2). Operador hace daily upsert con balance MT5 → `POST /equity/upsert` con `daily_pnl_pct`, `dd_pct`, `trade_count`.

`SCENARIOS.md` will be open to grow as the user thinks of new flows. The 8 above are the floor for "approved DoD".

## CLI_TO_API.md mapping (initial 10 slash commands)

Two-column table. Left: CLI command (current state). Right: equivalent API call(s).

Initial 10 commands to map (final list in plan):

| CLI | API equivalent |
|---|---|
| `/signal SYMBOL SIDE entry sl=X tp=Y` | `POST /agents/signal_validator/run` then `POST /signals` |
| `/journal` | `POST /agents/journal/run` then `POST /equity/upsert` |
| `/risk` | `POST /agents/risk/run` (no DB write — pure compute) |
| `/punk-hunt` | `POST /agents/regime/run` + `POST /agents/multifactor/run` (loop over watchlist) |
| `/punk-watch` | (no API equivalent yet — TV drawing path is local-only; document as "out of scope for current API") |
| `/regime` | `POST /agents/regime/run` |
| `/multifactor` | `POST /agents/multifactor/run` |
| `/sentiment` | `POST /agents/sentiment/run` |
| `/status` | `GET /profiles?include_metrics=true` + `GET /equity?from_date=today` |
| `/equity <value>` | `POST /equity/upsert` |

## Drift prevention

### `_generate_stubs.py`

Modes:
- `python docs/api/_generate_stubs.py` — write changes
- `python docs/api/_generate_stubs.py --check` — exit 1 if any file has uncommitted changes after regeneration (CI gate)
- `python docs/api/_generate_stubs.py --router signals` — regenerate just one file (faster local iteration)

Implementation outline:
1. Set `PYTHONPATH=api`, import `app.api.v1 import router as v1_router` and `app.main import app`
2. Walk `app.routes`, filter `APIRoute` instances under `/api/v1`
3. Group by tag → file
4. For each route, render the 🤖 block as markdown, locate the matching `<!-- AUTOGEN:START name=<METHOD>-<route-name> -->` ... `<!-- AUTOGEN:END ... -->` block in the target file, replace its body
5. If a route has no matching block in the file → append a fresh stub at the bottom with empty ✍️ sections so the human knows to fill them in
6. If a block exists in the file but has no matching route → flag as orphan (probably an endpoint was deleted) and abort with non-zero exit

### CI gate

Find the existing GitHub Actions workflow (or create a minimal one if there is none for the `api/` folder). Add a step:

```yaml
- name: API docs in sync
  run: |
    cd api && uv sync
    cd .. && python docs/api/_generate_stubs.py --check
```

If the user does not run GitHub Actions for this repo, fall back to a `pre-commit` hook in `.pre-commit-config.yaml`.

### Test

`api/tests/test_docs_in_sync.py` calls the script in `--check` mode via `subprocess` and asserts exit code 0. This guarantees idempotence and serves as the canary for the CI gate.

## Definition of Done

1. ✅ Six files exist in `docs/api/routers/` covering all 19 implemented endpoints
2. ✅ `MANUAL.md` lists the 19 endpoints in a single table with method, path, 1-line "cuándo usar"
3. ✅ `SCENARIOS.md` contains at minimum the 8 scenarios listed above
4. ✅ `CLI_TO_API.md` maps at minimum the 10 slash commands listed above
5. ✅ `AUTH.md` explains the `X-User-Id` header, why Clerk JWT is not yet wired, and links to spec #1 once written
6. ✅ `ERRORS.md` catalogs the HTTP status codes the API uses today. Confirmed from grep of route files: `400 Bad Request` (custom invalid UUID), `401 Unauthorized` (missing/invalid `X-User-Id`), `404 Not Found` (resource not user-scoped or missing), `409 Conflict` (slug uniqueness, equity-point uniqueness), plus FastAPI defaults `422 Unprocessable Entity` (Pydantic validation) and `500 Internal Server Error` (uncaught). Each gets an example JSON body
7. ✅ `api/README.md` is corrected — no false claims about `auth.py`, `billing.py`, `brokers.py`, `ws.py`, etc. Has a "Roadmap" section pointing to future specs #1–#5
8. ✅ `docs/api/_generate_stubs.py` exists, runs idempotently, supports `--check` and `--router <name>` modes
9. ✅ CI gate (or pre-commit hook fallback) is wired
10. ✅ `api/tests/test_docs_in_sync.py` passes locally (`cd api && uv run pytest tests/test_docs_in_sync.py`)
11. ✅ `docs/api/README.md` exists as the entry point with quick-start and index

## Estimación realista

1.5–2 días full-time:
- `_generate_stubs.py` + tests: ~3 hours
- 6 router files (avg 4 endpoints, ~30 min each polished): ~3 hours
- `SCENARIOS.md` (8 scenarios): ~2 hours
- `CLI_TO_API.md` (10 commands): ~1 hour
- `AUTH.md` + `ERRORS.md` + `MANUAL.md` + `README.md` corrected: ~2 hours
- CI wiring + verification: ~1 hour
- Buffer for "I missed something in the audit": ~2 hours

## Open questions deferred to plan

- Does the repo have an active GitHub Actions workflow we add the gate to, or do we create a new `api-docs.yml`? Plan will inspect `.github/` and decide.
- Pydantic v2 `model_json_schema()` produces verbose JSON Schema. The plan will pick the rendering strategy (table-only vs JSON Schema collapsed in `<details>`).
- `SCENARIOS.md` TypeScript snippets — should we include error handling? The plan will pick the snippet template once.

## Future sub-projects (out of scope for this spec — listed for traceability)

| # | Sub-project | Notes |
|---|---|---|
| #1 | Auth — Clerk + JWT + multi-tenant guards | Estimated ~1 week. Blocks #2/#3/#4/#5. |
| #2 | Brokers — Bitunix, Binance, MT5 bridge | Estimated ~1.5 weeks. Reuses `key_service.py` pattern. |
| #3 | WebSockets + Redis pubsub | Estimated 3-5 days. UX upgrade, not revenue-blocking. |
| #4 | Billing with **Polar.sh** (NOT Stripe) | Estimated ~1 week. User-confirmed Polar.sh as the choice. |
| #5 | Audit + rate limiting + observability | Estimated 3-5 days. Hardening pre-launch. |

Each gets its own spec → plan → implementation cycle in `docs/superpowers/`.
