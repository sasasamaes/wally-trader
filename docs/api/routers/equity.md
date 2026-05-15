# Equity router


## `GET /api/v1/equity`

<!-- AUTOGEN:START name=GET-api-v1-equity -->
- **Method** `GET`
- **Path** `/api/v1/equity`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 200

**Request body:**

_No request body._

**Response:** `EquitySeriesResponse`
<!-- AUTOGEN:END name=GET-api-v1-equity -->

**Cuándo usar:**
- Chart de equity en frontend (línea / área plot) — toda la curva del profile
- Export para review semanal/mensual — datos crudos por día
- Comparar curva vs HODL en profile `quantfury` (campo `outperformance_vs_hodl_pct`)
- Estadísticas agregadas vía `summary`: max DD, total return, días tradeados

**Reglas Wally Trader que aplican:**
- `profile_id` REQUIRED, opcional `from_date` / `to_date` (formato `date`, no datetime)
- `summary` siempre se calcula con `compute_equity_summary` — incluye `capital_initial`, `capital_current`, `total_pnl_usd`, `total_pnl_pct`, `max_dd_pct`, `trading_days`, `last_updated`
- Orden por `date ASC` (más antigua primero — facilita plot directo)
- Si no hay puntos en el rango, devuelve `points: []` con summary degradado (no error)

**Ejemplo curl:**

```bash
curl -s -H "X-User-Id: 550e8400-..." \
  "http://localhost:8000/api/v1/equity?profile_id=f7e6...&from_date=2026-04-01"
```

**Ejemplo TypeScript (fetch):**

```typescript
type EquityPointView = {
  date: string;
  equity: number;
  daily_pnl_pct: number | null;
  dd_pct: number | null;
  outperformance_vs_hodl_pct: number | null;
  win_rate_pct: number | null;
  trade_count: number;
};
type EquitySummary = {
  capital_initial: number;
  capital_current: number;
  total_pnl_usd: number;
  total_pnl_pct: number;
  max_dd_pct: number | null;
  trading_days: number;
  last_updated: string | null;  // ISO yyyy-mm-dd
};
type EquitySeriesResponse = { points: EquityPointView[]; summary: EquitySummary };

const params = new URLSearchParams({ profile_id: profileId, from_date: "2026-04-01" });
const series: EquitySeriesResponse = await fetch(`${API}/api/v1/equity?${params}`, {
  headers: { "X-User-Id": userId },
}).then(r => r.json());
```

**Errores típicos en este endpoint:**
- `400 Invalid profile_id` — UUID mal formado
- `404 Profile not found` — profile_id no es del usuario actual

**Ver también:**
- `POST /equity/upsert` para registrar puntos manualmente
- [SCENARIOS.md#8-equity-tracking-manual](../SCENARIOS.md)


## `POST /api/v1/equity/upsert`

<!-- AUTOGEN:START name=POST-api-v1-equity-upsert -->
- **Method** `POST`
- **Path** `/api/v1/equity/upsert`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 200

**Request body:**

| Campo | Tipo | Required | Default | Descripción |
|---|---|---|---|---|
| `profile_id` | string | ✓ | `—` | Profile Id |
| `date` | string (date) | ✓ | `—` | Date |
| `equity` | number | ✓ | `—` | Equity |
| `daily_pnl_pct` | number \| null | — | `null` | Daily Pnl Pct |
| `dd_pct` | number \| null | — | `null` | Dd Pct |
| `win_rate_pct` | number \| null | — | `null` | Win Rate Pct |
| `trade_count` | integer | — | `0` | Trade Count |

**Response:** `EquityPointView`
<!-- AUTOGEN:END name=POST-api-v1-equity-upsert -->

**Cuándo usar:**
- Cierre diario operador FTMO/FundingPips (anota balance MT5 al final del día)
- Comando CLI `/equity <value>` actualiza el día actual
- Backfill histórico: registrar varios días offline desde un export del broker
- El campo `outperformance_vs_hodl_pct` se calcula automáticamente en background para profile quantfury (no se setea por POST aquí)

**Reglas Wally Trader que aplican:**
- ⚠️ **Side-effect:** si `body.date` es la fecha MÁS RECIENTE registrada para el profile, auto-actualiza `profile.capital_current = body.equity`. Si es fecha anterior, NO toca capital_current (solo guarda el punto histórico)
- **Idempotente** sobre `(profile_id, date)` — POST repetido sobre la misma fecha sobreescribe el row (no duplica)
- `equity` debe ser > 0 (validation Pydantic)
- `daily_pnl_pct`, `dd_pct`, `win_rate_pct` son opcionales — si los pasás se almacenan, si no se quedan null
- `trade_count` default 0

**Ejemplo curl:**

```bash
curl -X POST http://localhost:8000/api/v1/equity/upsert \
  -H "X-User-Id: 550e8400-..." \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "f7e6...",
    "date": "2026-05-13",
    "equity": 18.45,
    "daily_pnl_pct": 1.99,
    "dd_pct": -0.5,
    "win_rate_pct": 71.4,
    "trade_count": 3
  }'
```

**Ejemplo TypeScript (fetch):**

```typescript
type EquityPointUpsert = {
  profile_id: string;
  date: string;  // YYYY-MM-DD
  equity: number;
  daily_pnl_pct?: number | null;
  dd_pct?: number | null;
  win_rate_pct?: number | null;
  trade_count?: number;
};

const point: EquityPointView = await fetch(`${API}/api/v1/equity/upsert`, {
  method: "POST",
  headers: { "X-User-Id": userId, "Content-Type": "application/json" },
  body: JSON.stringify({
    profile_id: profileId,
    date: "2026-05-13",
    equity: 18.45,
    daily_pnl_pct: 1.99,
  } as EquityPointUpsert),
}).then(r => r.json());
```

**Errores típicos en este endpoint:**
- `400 Invalid profile_id`
- `404 Profile not found`
- `409 Conflict` — race condition rara entre dos POSTs simultáneos sobre la misma fecha
- `422` Pydantic — `equity<=0`, `date` mal formada (debe ser `YYYY-MM-DD`)

**Ver también:**
- `GET /equity` para series chart
- `PATCH /profiles/{slug}` si solo querés actualizar capital_current sin grabar punto histórico

