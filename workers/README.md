# workers/ — Wally Trader Background Jobs

ARQ (async Redis queue) workers for periodic + on-demand background tasks.

## Job inventory

| Job | Schedule | Source |
|---|---|---|
| `sync_broker_positions` | every 30s | `workers/sync_positions.py` |
| `refresh_macro_calendar` | daily 04:00 CR | `workers/macro_refresh.py` |
| `fetch_sentiment` | every 30 min | `workers/sentiment_fetch.py` |
| `aggregate_equity_eod` | daily 23:55 CR | `workers/equity_aggregator.py` |
| `retrain_ml` | weekly Sun 02:00 CR | `workers/ml_retrain.py` |
| `reconcile_stripe_usage` | hourly | `workers/billing_reconcile.py` |

## Running locally

```bash
cd workers
uv sync
uv run arq workers.main.WorkerSettings
```

Or use docker-compose (recommended) — see `../infra/docker-compose.dev.yml`.
The worker container imports the same Python packages as `api/` so they
share the `shared/wally_core/` library installed in editable mode.
