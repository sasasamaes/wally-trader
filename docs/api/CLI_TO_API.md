# CLI → API equivalencias

Mapeo de los slash commands más usados a sus equivalentes API. Útil si quieres replicar el workflow CLI desde frontend o un script externo.

| CLI command | API equivalente | Notas |
|---|---|---|
| `/signal SYMBOL SIDE entry sl=X tp=Y` | 1. `POST /api/v1/agents/signal_validator/run` (SSE)<br>2. Si verdict=GO: `POST /api/v1/signals` con scores extraídos | El signal_validator agent corre los 4 filtros + multifactor + ML score |
| `/journal` | 1. `POST /api/v1/agents/journal/run` con `{profile_id, date}`<br>2. `POST /api/v1/equity/upsert` con balance del día | Genera markdown + actualiza equity en una sola sesión |
| `/risk SIDE entry sl` | `POST /api/v1/agents/risk/run` con `{side, entry, sl, profile_id}` | Pure compute, no escribe DB |
| `/punk-hunt` | Ver [SCENARIOS.md#3-autohunt](SCENARIOS.md) — orquesta `regime` + `multifactor` + `signals POST` | Loop sobre 24 assets watchlist bitunix |
| `/punk-watch` | _Sin equivalente API en Phase 1_ | El watch path dibuja en TradingView local — necesita TV MCP, no expuesto vía HTTP |
| `/regime` | `POST /api/v1/agents/regime/run` con `{symbol, timeframe}` | Default `BTCUSDT` 1H |
| `/multifactor` | `POST /api/v1/agents/multifactor/run` con `{symbol, side}` | Devuelve score 0-100 |
| `/sentiment` | `POST /api/v1/agents/sentiment/run` con `{asset}` | F&G + Reddit VADER + News + Funding |
| `/status` | 1. `GET /api/v1/profiles?include_metrics=true`<br>2. `GET /api/v1/equity?profile_id=<active>&from_date=<today>` | Equivalente al statusline multi-profile |
| `/equity <value>` | `POST /api/v1/equity/upsert` con `{profile_id, date: today, equity: <value>}` | Auto-mirror a `profile.capital_current` |

## Comandos CLI sin equivalente API hoy (Phase 1)

Estos comandos dependen de side-effects locales (TradingView MCP, archivos en `.claude/cache/`) y no están expuestos vía HTTP:

- `/punk-watch`, `/chart`, `/levels`, `/alert` — escriben/leen TradingView Desktop via MCP
- `/morning`, `/punk-morning` — agregan WebFetch a APIs externas + leen archivos locales
- `/backtest`, `/hmm-analyze` — corren scripts Python locales con datasets >100MB
- `/profile` — switch de profile activo (state local en `.claude/`)
- `/macross`, `/asian-range`, `/pullback`, `/liq-heatmap` — helpers numéricos puros, podrían exponerse en sub-proyecto futuro como `/agents/<helper>/run` adicionales
