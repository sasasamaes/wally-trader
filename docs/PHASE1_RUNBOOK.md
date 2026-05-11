# Phase 1 — Local dev runbook

End-to-end recipe to bring up the web app locally and run your first
agent call. Assumes you've gone through Phase 0 setup once (Docker
installed, repo cloned, etc.).

## 1. Generate a MASTER_KEK and write `.env`

```bash
cp .env.example .env
python3 -c "import secrets,base64; print('MASTER_KEK=' + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())" >> .env
# Edit .env to taste — at minimum confirm DATABASE_URL + REDIS_URL match
# the docker-compose defaults.
```

## 2. Start the local stack

```bash
docker compose -f infra/docker-compose.dev.yml up -d postgres redis
```

Verify health:

```bash
docker compose -f infra/docker-compose.dev.yml ps
```

## 3. Install Python deps + bootstrap DB

```bash
cd api
uv sync
uv run python scripts/bootstrap_db.py
```

Expected output:
```
→ Waiting for Postgres at localhost:5432 …
→ No migrations yet — generating initial revision …
   Generating /api/alembic/versions/XXXX_initial.py ...  done
→ Running alembic upgrade head …
   Running upgrade  -> XXXX, initial
✓ All 12 tables present.
```

## 4. Create a dev user (auth stub)

Phase 1 uses an `X-User-Id` header instead of Clerk JWT. Mint one:

```bash
uv run python scripts/create_dev_user.py jose@example.com "Jose"
# → 0f8e7d6c-XXXX-XXXX-XXXX-XXXXXXXXXXXX
```

Store the UUID in your terminal env (or paste it into `localStorage.wally_user_id`
in the browser devtools when running the frontend).

```bash
export WALLY_USER_ID=0f8e7d6c-XXXX-XXXX-XXXX-XXXXXXXXXXXX
```

## 5. Run the API

```bash
uv run uvicorn app.main:app --reload
```

Verify:

```bash
curl http://localhost:8000/healthz
# {"status":"ok","version":"0.1.0"}

curl http://localhost:8000/api/v1/ping
# {"pong":"ok"}

curl -H "X-User-Id: $WALLY_USER_ID" http://localhost:8000/api/v1/agents
# [{"name":"regime", …}, {"name":"risk", …}, …]
```

## 6. Add your first LLM key

```bash
curl -X POST http://localhost:8000/api/v1/keys/llm \
  -H "X-User-Id: $WALLY_USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"provider": "anthropic", "api_key": "sk-ant-…YOUR-REAL-KEY…", "label": "test"}'
```

You should get back a row with `last4` and **no plaintext**.

## 7. Run your first agent

```bash
curl -N -X POST http://localhost:8000/api/v1/agents/regime/run \
  -H "X-User-Id: $WALLY_USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "anthropic",
    "model": "claude-sonnet-4-6",
    "input": {
      "symbol": "BTCUSDT",
      "timeframe": "1H",
      "bars": [{"open":80000,"high":80500,"low":79800,"close":80300,"volume":150}, ...]
    }
  }'
```

You'll see SSE chunks streaming back:
```
event: run_started
data: {"type": "run_started", "run_id": "…", "agent": "regime"}

event: text
data: {"type": "text", "delta": "El"}

event: text
data: {"type": "text", "delta": " regime"}
…
event: usage
data: {"type": "usage", "prompt_tokens": 230, "completion_tokens": 145, "cost_usd": 0.002865, …}

event: done
data: {"type": "done"}
```

## 8. Run the frontend

```bash
cd web
cp .env.local.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

Open `http://localhost:3000`, then:
1. Set `localStorage.wally_user_id` to your UUID via devtools console:
   ```js
   localStorage.setItem("wally_user_id", "0f8e7d6c-…");
   ```
2. Navigate to `/settings/keys` — add an LLM key from the UI.
3. Navigate to `/agents` — pick `/regime`, type a JSON payload, hit send.

You should see streaming text appear in real time, with a token count + cost
breakdown when the response ends.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `MASTER_KEK is not valid base64` | Re-run the generator one-liner; the value must be 44 chars base64. |
| `Missing X-User-Id header` | You're hitting the API without auth. Set the header or wait for Phase 1.5 Clerk. |
| `No API key set for provider …` | Add it via `POST /api/v1/keys/llm` first. |
| `MissingApiKeyError` in agent run | Same — provider key not yet stored. |
| SSE stream cuts off in browser | Some corporate proxies buffer SSE. Test with curl first. |
| `uv: command not found` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` then restart shell. |

## Verification — Phase 1 done if

- [ ] `pytest api/tests/` passes (excluding tests requiring real LLM calls)
- [ ] You can `POST /api/v1/keys/llm` and the row has encrypted_key as bytes, not the plaintext
- [ ] You can `POST /api/v1/agents/regime/run` and SSE chunks arrive
- [ ] The `agent_runs` table has a completed row with prompt_tokens, completion_tokens, cost_usd
- [ ] The `usage_events` table has one row per agent run
- [ ] `grep -RE "(sk-ant|sk-|gsk_|AIza)" api/logs/` returns NOTHING — no plaintext leaks
- [ ] Frontend `/agents` page renders streaming text + final cost summary
