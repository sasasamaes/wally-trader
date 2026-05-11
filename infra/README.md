# infra/ — Wally Trader Infrastructure

Deployment, dev environment, and IaC configs.

## Files

| File | Purpose |
|---|---|
| `docker-compose.dev.yml` | Local stack: postgres + redis + api + workers |
| `fly.toml` | Fly.io app config for api + workers (production) |
| `vercel.json` | Vercel project config for `web/` (production) |
| `nginx.conf` | (Optional) reverse proxy config if self-hosted |

## Local development

```bash
cd infra
docker compose -f docker-compose.dev.yml up
# Postgres @ localhost:5432 (user: wally, db: wally_dev)
# Redis    @ localhost:6379
# API      @ localhost:8000
```

`docker compose down -v` to wipe volumes and start fresh.

## Production deploy (beta)

1. Frontend → Vercel (auto on push to `main`)
2. Backend → Fly.io `fly deploy` from `infra/`
3. DB → Fly Postgres cluster (`fly pg create`)
4. Redis → Fly Redis (`fly redis create`) or Upstash free tier
5. Secrets → `fly secrets set MASTER_KEK=... STRIPE_SECRET_KEY=...`

See `SETUP.md` at repo root for the full bootstrap sequence.
