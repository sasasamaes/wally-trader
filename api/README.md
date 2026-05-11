# api/ — Wally Trader Backend

FastAPI + Python 3.13 + SQLAlchemy 2.0 + PostgreSQL + Redis.

This is the application API. Reuses `shared/wally_core/` for pure-logic
trading primitives (risk, regime, signals, multifactor, journal, macro).

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

## Layout

```
app/
├── main.py                 # FastAPI app instance + middleware
├── core/
│   ├── config.py           # Pydantic Settings (env vars)
│   └── logging.py          # structured logging + secret redaction
├── db/
│   ├── base.py             # SQLAlchemy declarative base
│   └── session.py          # async engine + session factory
├── models/                 # SQLAlchemy models (user, profile, signal, ...)
├── schemas/                # Pydantic v2 request/response models
├── api/
│   └── v1/
│       ├── agents.py       # POST /agents/{name}/run (SSE streaming)
│       ├── auth.py         # Clerk webhook sync
│       ├── billing.py      # Stripe checkout + portal + webhooks
│       ├── brokers.py      # broker keys (read-only validation)
│       ├── keys.py         # LLM keys CRUD (encrypted)
│       ├── profiles.py     # profile CRUD
│       ├── signals.py      # signals CRUD + WR/PF stats
│       └── equity.py       # equity curve series
├── agents/                 # backend port of `.opencode/agents/`
│   ├── regime.py
│   ├── risk.py
│   ├── signal_validator.py
│   ├── multifactor.py
│   ├── journal.py
│   └── sentiment.py
├── llm_gateway/
│   ├── router.py           # provider dispatch
│   ├── anthropic_client.py
│   ├── openai_client.py
│   ├── google_client.py
│   ├── ollama_client.py
│   └── pricing.py          # token → cost mapping per model
├── brokers/
│   ├── bitunix.py
│   ├── binance.py
│   └── mt5_bridge.py
├── billing/
│   ├── stripe_client.py
│   ├── webhooks.py
│   └── meters.py           # emit usage events
├── security/
│   ├── encryption.py       # AES-256-GCM DEK/KEK
│   └── audit.py
├── ws.py                   # WebSocket hub (Redis pubsub fanout)
└── deps.py                 # FastAPI dependency injection (current_user, db)

alembic/
├── env.py
└── versions/

tests/
├── conftest.py
├── test_encryption.py
├── test_llm_gateway.py
├── test_agents.py
├── test_billing.py
└── test_brokers.py
```

## Reuses (from project root)

- `shared/wally_core/src/wally_core/*` — pure logic (do NOT duplicate)
- `scripts/ml_system/*` — ML pipeline (sentiment + XGBoost)
- `.claude/scripts/macro_gate.py` etc — wrapped as agent endpoints
