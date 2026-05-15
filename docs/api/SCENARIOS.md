# Escenarios — Wally Trader API

8 flujos típicos del proyecto. Cada uno orquesta varios endpoints. Si vas a construir un frontend, piensa estos casos como "vistas" antes que como "endpoints".

## 1. Morning routine multi-profile

**Trigger:** CR 06:00, el usuario abre el dashboard.

**Pipeline:**
1. `GET /api/v1/profiles?include_metrics=true` — todos los profiles activos con su capital, WR, PF, total PnL
2. Por cada profile: `GET /api/v1/equity?profile_id=<id>&from_date=<today-7d>` — gráfico semanal
3. `POST /api/v1/agents/regime/run` con `input={"symbol": "BTCUSDT", "timeframe": "1h"}` para el activo principal del día
4. (Opcional) `POST /api/v1/agents/sentiment/run` con `input={"asset": "BTC"}` para Fear & Greed + funding bias

**Reglas obligatorias:**
- Si algún profile tiene `daily_pnl_pct <= -2%`, mostrar warning "near daily BLOCK"
- Si más de 1 profile tiene trade BTC abierto hoy, mostrar warning "cross-asset exclusion"

**TypeScript snippet:**

```typescript
const profiles = await fetchJSON<ProfileList>(`${API}/api/v1/profiles?include_metrics=true`);
const equityByProfile = await Promise.all(
  profiles.profiles.map(p =>
    fetchJSON<EquitySeries>(`${API}/api/v1/equity?profile_id=${p.id}&from_date=${weekAgo}`)
  )
);
const regime = await streamAgent("regime", { symbol: "BTCUSDT", timeframe: "1h" });
```

---

## 2. Validar señal Discord punkchainer's (bitunix)

**Trigger:** Llega call en Discord. Profile=bitunix.

**Pipeline:**
1. `GET /api/v1/profiles/bitunix` — confirmar `capital_current` + `config_json.leverage_cap`
2. `GET /api/v1/signals?profile_id=<bitunix>&from_date=<today>` — verificar count<7 (bitunix max 7/día)
3. `POST /api/v1/agents/signal_validator/run` con el body de la call (symbol, side, entry, sl, tp, leverage)
4. Consumir SSE; si stream emite verdict=GO y score≥60:
5. `POST /api/v1/signals` con `source="punkchainer_discord"` + scores extraídos del agent
6. Operador ejecuta trade manual en Bitunix UI (no automatizado en Phase 1)
7. Cuando cierra: `PATCH /api/v1/signals/{id}/outcome`

**Reglas obligatorias antes del paso 5:**
- count<7 hoy, count<2 concurrentes con outcome=pending
- daily_pnl > -6% (BLOCK threshold)
- leverage <= 20x (cap bitunix)

---

## 3. Autohunt: cazar setup propio (bitunix)

**Trigger:** `/punk-hunt` corre o el usuario clickea "Hunt" en frontend.

**Pipeline:**
1. Para cada uno de los 24 assets del watchlist bitunix:
   - `POST /api/v1/agents/regime/run` con `input={"symbol": <asset>}`
2. Filtrar assets con régimen `RANGE_CHOP` o `TREND_LEVE`
3. Para los que pasan: `POST /api/v1/agents/multifactor/run`
4. Top 1 por score: si score≥70 → `POST /api/v1/signals` con `source="self_generated"`
5. Notificar al usuario (push / email / Discord)

**Reglas:**
- Max 1 self-generated signal por hora (evita oversignaling)
- Aplican las mismas reglas de límite que en escenario 2

---

## 4. Cerrar trade y journal (cualquier profile)

**Trigger:** Trade cerrado en exchange / fin del día.

**Pipeline:**
1. `PATCH /api/v1/signals/{id}/outcome` con outcome (`TP1`/`TP2`/`TP3`/`SL`/`MANUAL`/`CANCELLED`) + `exit_price` + `pnl_usd` + `learning`
2. `POST /api/v1/agents/journal/run` con `input={"profile_id": <id>, "date": <today>}` — genera markdown del día
3. Mostrar el `output_md` al usuario, opcionalmente guardar en `JournalEntry` (no hay endpoint todavía)
4. `POST /api/v1/equity/upsert` con `equity` actualizado, `daily_pnl_pct`, `dd_pct`, `trade_count`

---

## 5. Dashboard multi-profile (frontend)

**Trigger:** Usuario abre la app, ya autenticado.

**Pipeline:**
1. `GET /api/v1/profiles?include_metrics=true` (server-side render o SWR)
2. Por cada profile mostrar tarjeta: capital, WR, PF, PnL día (delta vs ayer), max DD
3. Sparkline: `GET /api/v1/equity?profile_id=<id>&from_date=<today-30d>`
4. Botón "Hunt" → escenario 3; botón "Journal" → escenario 4

---

## 6. Gestionar LLM keys (BYOK setup inicial)

**Trigger:** Usuario nuevo en `/settings/keys`.

**Pipeline:**
1. `GET /api/v1/keys/llm` — ver qué providers ya configurados
2. Para cada provider faltante (anthropic, openai, google, ollama opcional):
   - `POST /api/v1/keys/llm` con `{provider, api_key, label}`
3. Test post-setup: `POST /api/v1/agents/regime/run` con un input mínimo para validar que la key funciona
4. Rotación: `DELETE /api/v1/keys/llm/{id}` + `POST /api/v1/keys/llm` con la nueva

---

## 7. Recuperar agent run histórico

**Trigger:** El SSE de un run anterior se cortó (cliente desconectado, navegador cerrado).

**Pipeline:**
1. El cliente debe haber guardado el `run_id` que llegó en el primer evento `run_started`
2. `GET /api/v1/agents/runs/{run_id}` — devuelve el output completo + cost + tokens + status
3. Si `status=running`, polling cada 2s hasta `completed` o `failed`

---

## 8. Equity tracking manual (FTMO / FundingPips)

**Trigger:** Operador cierra el día y quiere registrar el balance MT5.

**Pipeline:**
1. Operador anota balance MT5 al cierre + PnL día + drawdown
2. `POST /api/v1/equity/upsert` con `{profile_id, date, equity, daily_pnl_pct, dd_pct, trade_count}`
3. El endpoint auto-mirror a `profile.capital_current` si la fecha es la última registrada
4. (Futuro #2) Cuando el broker bridge esté wired, este flow se automatiza
