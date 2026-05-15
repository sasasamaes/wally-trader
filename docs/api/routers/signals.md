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
- _(rellenar — escenarios concretos Wally Trader)_

**Reglas Wally Trader que aplican:**
- _(rellenar — caps por profile, rate limits, etc.)_

**Ejemplo curl:**

```bash
# (rellenar)
```

**Ejemplo TypeScript (fetch):**

```typescript
// (rellenar)
```

**Errores típicos en este endpoint:**
- _(rellenar)_

**Ver también:**
- _(rellenar)_


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
- _(rellenar — escenarios concretos Wally Trader)_

**Reglas Wally Trader que aplican:**
- _(rellenar — caps por profile, rate limits, etc.)_

**Ejemplo curl:**

```bash
# (rellenar)
```

**Ejemplo TypeScript (fetch):**

```typescript
// (rellenar)
```

**Errores típicos en este endpoint:**
- _(rellenar)_

**Ver también:**
- _(rellenar)_


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
- _(rellenar — escenarios concretos Wally Trader)_

**Reglas Wally Trader que aplican:**
- _(rellenar — caps por profile, rate limits, etc.)_

**Ejemplo curl:**

```bash
# (rellenar)
```

**Ejemplo TypeScript (fetch):**

```typescript
// (rellenar)
```

**Errores típicos en este endpoint:**
- _(rellenar)_

**Ver también:**
- _(rellenar)_


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
- _(rellenar — escenarios concretos Wally Trader)_

**Reglas Wally Trader que aplican:**
- _(rellenar — caps por profile, rate limits, etc.)_

**Ejemplo curl:**

```bash
# (rellenar)
```

**Ejemplo TypeScript (fetch):**

```typescript
// (rellenar)
```

**Errores típicos en este endpoint:**
- _(rellenar)_

**Ver también:**
- _(rellenar)_

