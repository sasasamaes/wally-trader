# Wally Trader API — Tabla maestra

19 endpoints implementados (Phase 1, requires `X-User-Id` header excepto donde se indica).

| Método | Path | Cuándo usar (1-line) | Detalle |
|---|---|---|---|
| GET | `/healthz` | Liveness probe + version check (público) | [meta.md](routers/meta.md) |
| GET | `/api/v1/ping` | Test "router v1 montado + CORS ok" (público) | [meta.md](routers/meta.md) |
| GET | `/api/v1/agents` | Listar los 6 agentes registrados + sus input schemas (público) | [agents.md](routers/agents.md) |
| POST | `/api/v1/agents/{name}/run` | Correr un agente y consumir output via SSE streaming | [agents.md](routers/agents.md) |
| GET | `/api/v1/agents/runs/{run_id}` | Recuperar resultado de un run anterior (si SSE se cortó) | [agents.md](routers/agents.md) |
| GET | `/api/v1/keys/llm` | Listar LLM keys del usuario (last4 + provider) | [keys.md](routers/keys.md) |
| POST | `/api/v1/keys/llm` | Registrar/rotar una API key (BYOK encriptada) | [keys.md](routers/keys.md) |
| DELETE | `/api/v1/keys/llm/{key_id}` | Borrar una LLM key | [keys.md](routers/keys.md) |
| GET | `/api/v1/profiles` | Listar profiles del usuario + métricas opcionales | [profiles.md](routers/profiles.md) |
| POST | `/api/v1/profiles` | Crear profile (kind: retail / ftmo / bitunix / etc.) | [profiles.md](routers/profiles.md) |
| GET | `/api/v1/profiles/{slug}` | Detalle de un profile + métricas | [profiles.md](routers/profiles.md) |
| PATCH | `/api/v1/profiles/{slug}` | Update parcial (capital_current, config_json, etc.) | [profiles.md](routers/profiles.md) |
| DELETE | `/api/v1/profiles/{slug}` | Eliminar profile (cascade signals + equity) | [profiles.md](routers/profiles.md) |
| GET | `/api/v1/signals` | Listar signals + stats agregadas (filtros) | [signals.md](routers/signals.md) |
| POST | `/api/v1/signals` | Crear signal (después de /signal CLI o call Discord) | [signals.md](routers/signals.md) |
| PATCH | `/api/v1/signals/{id}/outcome` | Cerrar signal con outcome + pnl (auto-update capital) | [signals.md](routers/signals.md) |
| GET | `/api/v1/signals/{id}` | Detalle de una signal | [signals.md](routers/signals.md) |
| GET | `/api/v1/equity` | Series de equity (chart) + summary (max DD, total return) | [equity.md](routers/equity.md) |
| POST | `/api/v1/equity/upsert` | Upsert manual diario (FTMO/FundingPips operador) | [equity.md](routers/equity.md) |

## Modelos huérfanos (en DB pero sin endpoint todavía)

| Modelo | Archivo | Sub-proyecto futuro |
|---|---|---|
| `Subscription` | `app/models/subscription.py` | #4 Billing (Polar.sh) |
| `UsageEvent` | `app/models/usage_event.py` | #4 Billing |
| `AuditLog` | `app/models/audit_log.py` | #5 Audit |
| `TradeBrokerSync` | `app/models/trade_broker_sync.py` | #2 Brokers |
| `JournalEntry` | `app/models/journal_entry.py` | TBD — ver spec del API manual |

## Roadmap (no implementado todavía)

- **#1 Auth** — Clerk + JWT + multi-tenant guards (reemplaza `X-User-Id` stub)
- **#2 Brokers** — Bitunix / Binance / MT5 keys + sync de trades
- **#3 WebSockets** — fanout via Redis pubsub para `signal.created`, `agent.run.token`, etc.
- **#4 Billing** — Polar.sh checkout + portal + metered usage
- **#5 Audit + RL + observability** — `AuditLog`, rate limiting, Sentry
