# Profiles router


## `GET /api/v1/profiles`

<!-- AUTOGEN:START name=GET-api-v1-profiles -->
- **Method** `GET`
- **Path** `/api/v1/profiles`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 200

**Request body:**

_No request body._

**Response:** `ProfileList`
<!-- AUTOGEN:END name=GET-api-v1-profiles -->

**Cuándo usar:**
- Dashboard multi-profile: traer TODOS los profiles del usuario en una sola call (`include_metrics=true` para ver capital, WR, PF)
- Statusline / sidebar: refresh periódico para mostrar capital actual de cada profile

**Reglas Wally Trader que aplican:**
- Cross-profile guard: el sistema asume max 1 profile haciendo BTC simultáneamente — el frontend debe mostrar warning visual si ve 2 profiles con trade BTC abierto el mismo día
- `include_metrics=true` corre `compute_signal_stats` por cada profile (puede ser lento con muchas signals)

**Ejemplo curl:**

```bash
curl -s -H "X-User-Id: 550e8400-..." \
  "http://localhost:8000/api/v1/profiles?include_metrics=true"
```

**Ejemplo TypeScript (fetch):**

```typescript
type ProfileKind = "retail" | "retail-bingx" | "ftmo" | "fundingpips" | "fotmarkets" | "bitunix" | "quantfury";
type Metrics = { trade_count: number; win_rate_pct: number; profit_factor: number | null; capital_current: number };
type Profile = { id: string; slug: string; name: string; kind: ProfileKind; capital_current: number; metrics?: Metrics };

const list = await fetch(`${API}/api/v1/profiles?include_metrics=true`, {
  headers: { "X-User-Id": userId },
}).then(r => r.json());
const profiles: Profile[] = list.profiles;
```

**Errores típicos en este endpoint:**
- `401` si falta `X-User-Id`
- Lista vacía si el usuario no creó profiles todavía — flow esperado en onboarding

**Ver también:**
- `GET /profiles/{slug}` para uno solo
- `POST /profiles` para crear
- [SCENARIOS.md#5-dashboard-multi-profile](../SCENARIOS.md)


## `POST /api/v1/profiles`

<!-- AUTOGEN:START name=POST-api-v1-profiles -->
- **Method** `POST`
- **Path** `/api/v1/profiles`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 201

**Request body:**

| Campo | Tipo | Required | Default | Descripción |
|---|---|---|---|---|
| `slug` | string | ✓ | `—` | Slug |
| `name` | string | ✓ | `—` | Name |
| `kind` | ProfileKind | ✓ | `—` |  |
| `capital_initial` | number | ✓ | `—` | Capital Initial |
| `currency` | string | — | `USD` | Currency |
| `config_json` | object | — | `—` | Config Json |
| `strategy_json` | object | — | `—` | Strategy Json |
| `rules_json` | object | — | `—` | Rules Json |

**Response:** `ProfileView`
<!-- AUTOGEN:END name=POST-api-v1-profiles -->

**Cuándo usar:**
- Onboarding: el usuario crea sus profiles iniciales (uno por exchange / challenge)
- Migrar usuario de CLI Wally Trader local al SaaS — crear los 7 profiles según `.claude/profiles/<name>/config.md`

**Reglas Wally Trader que aplican:**
- `kind` debe ser uno de los 7 valores operativos del enum `ProfileKind`: `retail`, `retail-bingx`, `ftmo`, `fundingpips`, `fotmarkets`, `bitunix`, `quantfury` (El enum incluye un 8º valor `custom` reservado para uso interno futuro — no usar en producción).
- `slug` es único POR USUARIO (no global) — dos usuarios pueden tener `slug=retail`
- `capital_initial` se copia automáticamente a `capital_current` al crear
- `kind` es INMUTABLE después de crear (no se puede convertir un retail en ftmo) — para cambiar tienes que DELETE + POST

**Ejemplo curl:**

```bash
curl -X POST http://localhost:8000/api/v1/profiles \
  -H "X-User-Id: 550e8400-..." \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "retail",
    "name": "Binance Main",
    "kind": "retail",
    "capital_initial": 18.09,
    "currency": "USD",
    "config_json": {"leverage_cap": 10, "max_trades_day": 3},
    "strategy_json": {"name": "MeanReversion15m", "rsi_ob": 65, "rsi_os": 35},
    "rules_json": {"daily_loss_block_pct": -2.0, "max_dd_pct": -10.0}
  }'
# 201 Created → ProfileView
```

**Ejemplo TypeScript (fetch):**

```typescript
const profile = await fetch(`${API}/api/v1/profiles`, {
  method: "POST",
  headers: { "X-User-Id": userId, "Content-Type": "application/json" },
  body: JSON.stringify({
    slug: "bitunix",
    name: "Bitunix Copy Trading",
    kind: "bitunix",
    capital_initial: 200,
    currency: "USD",
    config_json: { leverage_cap: 20, max_signals_day: 7 },
    strategy_json: { source: "punkchainer_discord" },
    rules_json: { daily_loss_block_pct: -6.0 },
  }),
}).then(r => r.json());
```

**Errores típicos en este endpoint:**
- `409 Conflict` "Profile with slug 'retail' already exists" — slug duplicado para este user
- `422 Unprocessable Entity` si `kind` no está en el enum o `capital_initial<=0`

**Ver también:**
- `PATCH /profiles/{slug}` para actualizar campos mutables
- `DELETE /profiles/{slug}` para eliminar (y recrear con otro `kind`)


## `GET /api/v1/profiles/slug`

<!-- AUTOGEN:START name=GET-api-v1-profiles-slug -->
- **Method** `GET`
- **Path** `/api/v1/profiles/{slug}`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 200

**Request body:**

_No request body._

**Response:** `ProfileView`
<!-- AUTOGEN:END name=GET-api-v1-profiles-slug -->

**Cuándo usar:**
- Pantalla de detalle de un profile (route frontend `/profiles/:slug`)
- Click "ver más" desde el dashboard
- Equivalente API del comando CLI `/status` cuando ese profile está activo

**Reglas Wally Trader que aplican:**
- `slug` es human-readable (no UUID) — usar slug en URLs facilita compartir links: `/profiles/retail` vs `/profiles/9f8b-...`
- A diferencia de `GET /profiles?include_metrics=...`, esta ruta SIEMPRE devuelve `metrics` populado (no es opcional aquí)

**Ejemplo curl:**

```bash
curl -s -H "X-User-Id: 550e8400-..." \
  http://localhost:8000/api/v1/profiles/bitunix
```

**Ejemplo TypeScript (fetch):**

```typescript
const profile: ProfileWithMetrics = await fetch(
  `${API}/api/v1/profiles/${slug}`,
  { headers: { "X-User-Id": userId } },
).then(r => r.json());
```

**Errores típicos en este endpoint:**
- `404 Profile not found` — el slug no existe O es de otro usuario (información leak protection)

**Ver también:**
- `PATCH /profiles/{slug}` para update de campos mutables
- `GET /equity?profile_id=<id>` para la curva del profile


## `PATCH /api/v1/profiles/slug`

<!-- AUTOGEN:START name=PATCH-api-v1-profiles-slug -->
- **Method** `PATCH`
- **Path** `/api/v1/profiles/{slug}`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 200

**Request body:**

| Campo | Tipo | Required | Default | Descripción |
|---|---|---|---|---|
| `name` | string \| null | — | `null` | Name |
| `capital_current` | number \| null | — | `null` | Capital Current |
| `config_json` | object \| null | — | `null` | Config Json |
| `strategy_json` | object \| null | — | `null` | Strategy Json |
| `rules_json` | object \| null | — | `null` | Rules Json |

**Response:** `ProfileView`
<!-- AUTOGEN:END name=PATCH-api-v1-profiles-slug -->

**Cuándo usar:**
- Ajustar `capital_current` manualmente (ej. después de retiro o depósito)
- Cambiar `config_json` / `strategy_json` / `rules_json` en runtime sin redeploy
- Renombrar profile (`name`, no `slug`)

**Reglas Wally Trader que aplican:**
- Solo 5 campos son MUTABLES: `name`, `capital_current`, `config_json`, `strategy_json`, `rules_json`
- INMUTABLES (cambiarlos requiere `DELETE` + `POST` con nuevo profile): `kind`, `slug`, `capital_initial`, `currency`
- Pasar campos inmutables en el body se IGNORA silenciosamente (no error) — TODO: futuro sub-proyecto debería devolver `400` para flagear esto
- Para tracking diario de equity, usa `POST /equity/upsert` en vez de PATCH manual del capital

**Ejemplo curl:**

```bash
curl -X PATCH http://localhost:8000/api/v1/profiles/retail \
  -H "X-User-Id: 550e8400-..." \
  -H "Content-Type: application/json" \
  -d '{"capital_current": 22.50, "name": "Binance Main (post-deposit)"}'
```

**Ejemplo TypeScript (fetch):**

```typescript
type ProfilePatch = Partial<{
  name: string;
  capital_current: number;
  config_json: Record<string, unknown>;
  strategy_json: Record<string, unknown>;
  rules_json: Record<string, unknown>;
}>;

const updated = await fetch(`${API}/api/v1/profiles/${slug}`, {
  method: "PATCH",
  headers: { "X-User-Id": userId, "Content-Type": "application/json" },
  body: JSON.stringify({ capital_current: 22.50 } as ProfilePatch),
}).then(r => r.json());
```

**Errores típicos en este endpoint:**
- `404 Profile not found` — slug no existe para el usuario actual

**Ver también:**
- `POST /equity/upsert` para tracking diario en lugar de PATCH manual
- `DELETE /profiles/{slug}` si querés cambiar `kind`/`slug` (recrea)


## `DELETE /api/v1/profiles/slug`

<!-- AUTOGEN:START name=DELETE-api-v1-profiles-slug -->
- **Method** `DELETE`
- **Path** `/api/v1/profiles/{slug}`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 204

**Request body:**

_No request body._

**Response:** `_(no body)_`
<!-- AUTOGEN:END name=DELETE-api-v1-profiles-slug -->

**Cuándo usar:**
- Usuario abandona un challenge (FTMO breach, FundingPips terminado)
- Cierre definitivo de cuenta retail
- Cleanup de profile de prueba antes de producción

**Reglas Wally Trader que aplican:**
- ⚠️ **Cascade delete IRREVERSIBLE**: destruye `signals` + `equity_points` asociados al profile (FK `ON DELETE CASCADE` en `app/models/profile.py` relationships)
- El frontend DEBE confirmar dos veces antes de ejecutar (ej. modal "Escribe el nombre del profile para confirmar")
- Si solo querés "pausar" sin destruir history, usá `PATCH` y agrega `config_json.paused=true` (convención frontend-side, no enforced por API)

**Ejemplo curl:**

```bash
curl -X DELETE -H "X-User-Id: 550e8400-..." \
  http://localhost:8000/api/v1/profiles/test-profile
# 204 No Content
```

**Ejemplo TypeScript (fetch):**

```typescript
await fetch(`${API}/api/v1/profiles/${slug}`, {
  method: "DELETE",
  headers: { "X-User-Id": userId },
});
```

**Errores típicos en este endpoint:**
- `404 Profile not found` — slug no existe o es de otro usuario

**Ver también:**
- `PATCH /profiles/{slug}` para soft-pause via `config_json.paused`
- `GET /signals?profile_id=<id>` para exportar history ANTES de borrar

