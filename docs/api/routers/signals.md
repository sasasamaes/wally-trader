# Signals router


## `GET /api/v1/signals`

<!-- AUTOGEN:START name=GET-api-v1-signals -->
- **Method** `GET`
- **Path** `/api/v1/signals`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 200

**Request body:**

_No request body._

**Response:** `SignalList`
<!-- AUTOGEN:END name=GET-api-v1-signals -->

**Cuándo usar:**
- Dashboard "history" page con tabla de todas las señales del profile activo
- Pre-flight check antes de POST: bitunix max 7/día → consultar `from_date=<today>` y verificar count<7
- Export CSV / Review semanal `/review` — paginar con `limit`+`offset`
- Filtrar por outcome=pending para ver trades activos abiertos

**Reglas Wally Trader que aplican:**
- `profile_id` es REQUIRED — no se puede listar sin scope a un profile
- Filtros opcionales: `symbol`, `side`, `outcome`, `from_date`, `to_date`, `limit` (default 200, max 1000), `offset`
- `stats` SIEMPRE se calcula (no opcional) y devuelve: total, open, closed, wins, losses, win_rate_pct, avg_win/loss_usd, total_pnl_usd, profit_factor (None si no hay losses)
- El orden es `opened_at DESC` (más reciente primero)

**Ejemplo curl:**

```bash
# Trades cerrados con outcome=tp1 desde 1ro de mayo
curl -s -H "X-User-Id: 550e8400-..." \
  "http://localhost:8000/api/v1/signals?profile_id=f7e6...&from_date=2026-05-01&outcome=tp1&limit=50"
```

**Ejemplo TypeScript (fetch):**

```typescript
type SignalSide = "long" | "short";
type SignalOutcome = "pending" | "win" | "loss" | "breakeven" | "tp1" | "tp2" | "tp3" | "manual";
type SignalView = {
  id: string; profile_id: string; symbol: string; side: SignalSide;
  entry: number; sl: number | null; tp1: number | null; tp2: number | null; tp3: number | null;
  leverage: number | null; source: string; outcome: SignalOutcome;
  pnl_usd: number | null; multifactor_score: number | null; ml_score: number | null;
  opened_at: string; closed_at: string | null;
};
type SignalStats = {
  total: number; open: number; closed: number; wins: number; losses: number;
  win_rate_pct: number; avg_win_usd: number; avg_loss_usd: number;
  total_pnl_usd: number; profit_factor: number | null;
};
type SignalList = { signals: SignalView[]; stats: SignalStats; total: number };

const params = new URLSearchParams({
  profile_id: profileId,
  from_date: "2026-05-01",
  outcome: "tp1",
  limit: "50",
});
const data: SignalList = await fetch(`${API}/api/v1/signals?${params}`, {
  headers: { "X-User-Id": userId },
}).then(r => r.json());
```

**Errores típicos en este endpoint:**
- `400 Invalid profile_id` — UUID mal formado
- `404 Profile not found` — profile_id existe pero pertenece a otro user (info-leak protection)

**Ver también:**
- `POST /signals` para crear nueva
- [SCENARIOS.md#5-dashboard-multi-profile](../SCENARIOS.md)


## `POST /api/v1/signals`

<!-- AUTOGEN:START name=POST-api-v1-signals -->
- **Method** `POST`
- **Path** `/api/v1/signals`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 201

**Request body:**

| Campo | Tipo | Required | Default | Descripción |
|---|---|---|---|---|
| `symbol` | string | ✓ | `—` | Symbol |
| `side` | SignalSide | ✓ | `—` |  |
| `entry` | number | ✓ | `—` | Entry |
| `sl` | number \| null | — | `null` | Sl |
| `tp1` | number \| null | — | `null` | Tp1 |
| `tp2` | number \| null | — | `null` | Tp2 |
| `tp3` | number \| null | — | `null` | Tp3 |
| `leverage` | integer \| null | — | `null` | Leverage |
| `profile_id` | string | ✓ | `—` | Profile Id |
| `source` | string | — | `self_generated` | Source |
| `verdict` | SignalVerdict \| null | — | `null` |  |
| `multifactor_score` | number \| null | — | `null` | Multifactor Score |
| `ml_score` | number \| null | — | `null` | Ml Score |
| `regime` | string \| null | — | `null` | Regime |
| `filters_4_count` | integer \| null | — | `null` | Filters 4 Count |
| `pillars_4_count` | integer \| null | — | `null` | Pillars 4 Count |
| `saturday` | boolean | — | `False` | Saturday |
| `opened_at` | string (date-time) \| null | — | `null` | Opened At |
| `extra` | object | — | `—` | Extra |

**Response:** `SignalView`
<!-- AUTOGEN:END name=POST-api-v1-signals -->

**Cuándo usar:**
- Después de ejecutar `/signal SYMBOL SIDE entry sl=X tp=Y` en CLI (auto-log via pipeline bitunix)
- Cuando recibes call en Discord punkchainer's y quieres trackearla con `source="punkchainer_discord"`
- Cuando `/punk-hunt` autohunt encontró setup propio (score≥70) — `source="self_generated"`
- Cuando ejecutaste trade manual en Bitunix UI y quieres registro retroactivo — `source="manual"`
- Para tracking de bot externo como Dragno — `source="dragno_ai"`

**Reglas Wally Trader que aplican:**
- **Profile bitunix:** max 7 signals/día → ANTES de POST consultá `GET /signals?profile_id=X&from_date=<today>` y verificá count<7. También max 2 con `outcome=pending` simultáneamente
- **Profile retail:** leverage cap 10x. **Profile bitunix:** cap 20x. **Profile ftmo:** según `config_json.leverage_cap`
- **Daily loss BLOCK:** si daily PnL <= -6% del profile (bitunix) o -2% (retail), el frontend debería mostrar warning antes de POST
- **Cross-profile BTC exclusion:** si otro profile del mismo user ya tiene un trade BTC abierto hoy, mostrar warning (no enforced server-side todavía)
- Si `multifactor_score<50` Y `ml_score<55`, el frontend debe mostrar warning "low confluence"
- `outcome` se setea a `"pending"` automáticamente; `opened_at` default = now

**Ejemplo curl:**

```bash
curl -X POST http://localhost:8000/api/v1/signals \
  -H "X-User-Id: 550e8400-..." \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "f7e6...",
    "symbol": "BTCUSDT",
    "side": "long",
    "entry": 67500,
    "sl": 66800,
    "tp1": 68900,
    "tp2": 70200,
    "leverage": 20,
    "source": "punkchainer_discord",
    "multifactor_score": 72.4,
    "ml_score": 68.1,
    "regime": "RANGE_CHOP",
    "filters_4_count": 4,
    "pillars_4_count": 3,
    "saturday": false
  }'
# 201 Created → SignalView with id + opened_at + outcome="pending"
```

**Ejemplo TypeScript (fetch):**

```typescript
type SignalCreate = {
  profile_id: string;
  symbol: string;
  side: "long" | "short";
  entry: number;
  sl?: number | null;
  tp1?: number | null;
  tp2?: number | null;
  tp3?: number | null;
  leverage?: number | null;
  source?: string;
  multifactor_score?: number | null;
  ml_score?: number | null;
  regime?: string | null;
  filters_4_count?: number | null;
  pillars_4_count?: number | null;
  saturday?: boolean;
};

const body: SignalCreate = {
  profile_id, symbol: "BTCUSDT", side: "long",
  entry: 67500, sl: 66800, tp1: 68900,
  leverage: 20, source: "punkchainer_discord",
  multifactor_score: 72.4, ml_score: 68.1,
};
const created: SignalView = await fetch(`${API}/api/v1/signals`, {
  method: "POST",
  headers: { "X-User-Id": userId, "Content-Type": "application/json" },
  body: JSON.stringify(body),
}).then(r => r.json());
```

**Errores típicos en este endpoint:**
- `400 Invalid profile_id` — UUID mal formado
- `404 Profile not found` — el profile_id no es del usuario actual
- `422` Pydantic validation — `leverage>125`, `side` no es `long`/`short`, `entry<=0`, `tp1<=0`, etc.

**Ver también:**
- `PATCH /signals/{id}/outcome` para cerrar
- `GET /signals?profile_id=X&from_date=<today>` para verificar count<7 (bitunix)
- [SCENARIOS.md#2-validar-señal-discord](../SCENARIOS.md)


## `PATCH /api/v1/signals/signal_id/outcome`

<!-- AUTOGEN:START name=PATCH-api-v1-signals-signal_id-outcome -->
- **Method** `PATCH`
- **Path** `/api/v1/signals/{signal_id}/outcome`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 200

**Request body:**

| Campo | Tipo | Required | Default | Descripción |
|---|---|---|---|---|
| `outcome` | SignalOutcome | ✓ | `—` |  |
| `exit_price` | number | ✓ | `—` | Exit Price |
| `exit_reason` | string \| null | — | `null` | Exit Reason |
| `pnl_usd` | number | ✓ | `—` | Pnl Usd |
| `duration_h` | number \| null | — | `null` | Duration H |
| `learning` | string \| null | — | `null` | Learning |
| `closed_at` | string (date-time) \| null | — | `null` | Closed At |

**Response:** `SignalView`
<!-- AUTOGEN:END name=PATCH-api-v1-signals-signal_id-outcome -->

**Cuándo usar:**
- Trade cerrado en exchange (TP hit, SL hit, manual close)
- Comando CLI `/log-outcome SYMBOL TP1 EXIT_PRICE --pnl 1.50`
- Reconciliación retroactiva: subiste un trade viejo y ahora le agregás el outcome

**Reglas Wally Trader que aplican:**
- ⚠️ **Side-effect crítico:** auto-actualiza `profile.capital_current` con `+= pnl_usd`. Si pasás `pnl_usd` mal, el capital queda corrupto y necesitarás `PATCH /profiles/{slug}` para corregirlo manualmente
- Outcomes válidos: `win`, `loss`, `breakeven`, `tp1`, `tp2`, `tp3`, `manual` (NO uses `pending` — esa es solo el estado inicial)
- `pnl_usd` es REQUIRED (puede ser 0 para breakeven, o negativo para losses)
- `closed_at` default = now si no lo pasás
- `learning` es opcional pero útil — alimenta los reviews semanales

**Ejemplo curl:**

```bash
curl -X PATCH http://localhost:8000/api/v1/signals/9f8b.../outcome \
  -H "X-User-Id: 550e8400-..." \
  -H "Content-Type: application/json" \
  -d '{
    "outcome": "tp1",
    "exit_price": 68900,
    "exit_reason": "TP1 hit",
    "pnl_usd": 1.45,
    "duration_h": 2.3,
    "learning": "Limpio, RSI confirmó la zona OS antes del rebote"
  }'
```

**Ejemplo TypeScript (fetch):**

```typescript
type SignalUpdateOutcome = {
  outcome: "win" | "loss" | "breakeven" | "tp1" | "tp2" | "tp3" | "manual";
  exit_price: number;
  exit_reason?: string | null;
  pnl_usd: number;
  duration_h?: number | null;
  learning?: string | null;
  closed_at?: string | null;
};

const closed: SignalView = await fetch(`${API}/api/v1/signals/${signalId}/outcome`, {
  method: "PATCH",
  headers: { "X-User-Id": userId, "Content-Type": "application/json" },
  body: JSON.stringify({
    outcome: "tp1",
    exit_price: 68900,
    pnl_usd: 1.45,
    duration_h: 2.3,
  } as SignalUpdateOutcome),
}).then(r => r.json());
```

**Errores típicos en este endpoint:**
- `400 Invalid signal_id` — UUID mal formado
- `404 Signal not found` — la signal no existe O pertenece a otro user (info-leak protection vía join con `profiles.user_id`)
- `422` si `outcome` no está en el enum o `exit_price<=0`

**Ver también:**
- `POST /agents/journal/run` después de cerrar trades para generar markdown del día
- `POST /equity/upsert` para registrar punto histórico de equity post-cierre
- [SCENARIOS.md#4-cerrar-trade-y-journal](../SCENARIOS.md)


## `GET /api/v1/signals/signal_id`

<!-- AUTOGEN:START name=GET-api-v1-signals-signal_id -->
- **Method** `GET`
- **Path** `/api/v1/signals/{signal_id}`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 200

**Request body:**

_No request body._

**Response:** `SignalView`
<!-- AUTOGEN:END name=GET-api-v1-signals-signal_id -->

**Cuándo usar:**
- Deep-link compartible al detalle de una signal (frontend route `/signals/:id`)
- Review post-cierre: ver scores originales (`multifactor_score`, `ml_score`) vs outcome real
- Debugging: ¿por qué este trade ganó/perdió? Inspeccionar `regime`, `filters_4_count`, `pillars_4_count`

**Reglas Wally Trader que aplican:**
- User-scope vía join con `profiles.user_id` — no expone signals de otros usuarios

**Ejemplo curl:**

```bash
curl -s -H "X-User-Id: 550e8400-..." \
  http://localhost:8000/api/v1/signals/9f8b... | jq
```

**Ejemplo TypeScript (fetch):**

```typescript
const signal: SignalView = await fetch(`${API}/api/v1/signals/${signalId}`, {
  headers: { "X-User-Id": userId },
}).then(r => r.json());
```

**Errores típicos en este endpoint:**
- `400 Invalid signal_id` — UUID mal formado
- `404 Signal not found` — no existe O es de otro user

**Ver también:**
- `PATCH /signals/{id}/outcome` para cerrar
- `GET /signals` para listar

