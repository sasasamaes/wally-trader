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
# crea api/.env con DATABASE_URL, MASTER_KEK, ANTHROPIC_API_KEY (ver ../docs/api/AUTH.md)
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
