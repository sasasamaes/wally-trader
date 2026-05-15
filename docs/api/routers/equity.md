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

