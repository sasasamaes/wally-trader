# Wally Trader — Web App Setup Guide

Bootstrap instructions for the Next.js + FastAPI web app introduced in
branch `feat/web-app-bootstrap`. The CLI side of the project (the
`.claude/` directory, the `tradingview-mcp/` server, the launchd jobs)
continues to work in parallel — this doc only covers the new web stack.

For the full design context, read:
- `/Users/josecampos/.claude/plans/hacer-de-wally-trader-polished-bachman.md`

## TL;DR — local dev in 5 commands

```bash
# 1. Generate a fresh MASTER_KEK and copy .env.example → .env
cp .env.example .env
python3 -c "import secrets,base64; print('MASTER_KEK=' + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())" >> .env

# 2. Bring up postgres + redis + api
docker compose -f infra/docker-compose.dev.yml up -d

# 3. Apply DB migrations
docker compose -f infra/docker-compose.dev.yml exec api uv run alembic upgrade head

# 4. Frontend dev server (in another terminal)
cd web && cp .env.local.example .env.local && npm install && npm run dev

# 5. Open http://localhost:3000
```

That gives you the landing page, the `/dashboard` placeholder, and the
API at `http://localhost:8000` (Swagger UI at `/docs`).

## Repo layout (post-bootstrap)

```
wally-trader/
├── .claude/             # existing CLI / Claude Code system (untouched)
├── shared/wally_core/   # existing shared Python library (reused by api/)
├── tradingview-mcp/     # existing MCP server (stays for personal CLI use)
│
├── web/                 # NEW — Next.js 15 frontend
│   ├── app/
│   │   ├── (auth)/      # Clerk sign-in / sign-up routes
│   │   ├── (app)/       # authenticated routes (dashboard, agents, etc.)
│   │   └── page.tsx     # public landing
│   ├── lib/
│   ├── package.json
│   └── tailwind.config.ts
│
├── api/                 # NEW — FastAPI backend
│   ├── app/
│   │   ├── main.py
│   │   ├── core/        # config, logging
│   │   ├── db/          # SQLAlchemy session
│   │   ├── models/      # ORM models
│   │   ├── api/v1/      # REST endpoints (filled in Phase 1+)
│   │   ├── security/    # AES-256-GCM encryption
│   │   └── ...
│   ├── alembic/         # migrations
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
│
├── workers/             # NEW — ARQ background jobs (filled in Phase 3)
│
├── infra/               # NEW — deployment configs
│   ├── docker-compose.dev.yml
│   ├── fly.toml
│   ├── vercel.json
│   └── PROVISIONING.md  # one-time signup checklist (Clerk, Stripe, Fly, Vercel)
│
├── .env.example         # NEW — backend env var template
└── SETUP_WEBAPP.md      # NEW — this file
```

## What's done (Phase 0 — bootstrap, this commit)

- [x] Top-level directory layout: `web/`, `api/`, `workers/`, `infra/`
- [x] FastAPI app skeleton with health check + Pydantic settings + structured logging with secret redaction
- [x] SQLAlchemy 2.0 models for every table in the data plan (users, profiles, signals, equity_points, agent_runs, usage_events, subscriptions, api_keys_llm, api_keys_broker, journal_entries, trade_broker_sync, audit_log)
- [x] Alembic migration scaffold (no migrations generated yet — that's the first task in Phase 1)
- [x] AES-256-GCM envelope encryption module (`app/security/encryption.py`) + 10 unit tests
- [x] docker-compose dev stack (postgres + redis + api + workers placeholder)
- [x] Next.js 15 + React 19 + Tailwind + shadcn-ready frontend with landing page, placeholder dashboard, Clerk-shaped auth routes
- [x] GitHub Actions workflow `web-app-ci.yml` (separate from existing CLI CI)
- [x] Fly.io + Vercel deployment configs + provisioning checklist

## What's next (Phase 1 — LLM Gateway + core agents)

See the plan doc for the full breakdown. Headline items:
1. Generate the first Alembic migration (`uv run alembic revision --autogenerate -m initial`)
2. Wire Clerk for auth + first user webhook
3. Build the LLM Gateway (Anthropic + OpenAI + Gemini + Ollama)
4. Wrap 6 core agents as `/api/v1/agents/{name}/run` SSE endpoints
5. Frontend: settings page for adding LLM keys + chat UI

## Verification — does the bootstrap work?

```bash
# Backend
docker compose -f infra/docker-compose.dev.yml up -d postgres redis
cd api
uv sync
uv run pytest tests/test_encryption.py -v   # 10 tests should pass
uv run uvicorn app.main:app --reload
# Visit http://localhost:8000/docs and http://localhost:8000/healthz

# Frontend (separate terminal)
cd web
npm install
npm run typecheck      # should pass with zero errors
npm run dev
# Visit http://localhost:3000
```

If any step fails, that's a bug in the bootstrap — please report.

## Sensitive operations checklist

The web app stores user secrets. Before going live with real friends:

- [ ] Generate a fresh `MASTER_KEK` and back it up to 1Password admin vault
- [ ] Confirm Clerk webhook signature is verified
- [ ] Confirm Stripe webhook signature is verified
- [ ] Run secret-leak grep over logs: `grep -RE "(sk-ant|sk-|gsk_|AIza)" api/logs/`
- [ ] Test `rewrap_dek()` rotation flow with a dummy key
- [ ] Set rate limits in Redis
- [ ] Configure backups for postgres (Fly snapshots daily)
