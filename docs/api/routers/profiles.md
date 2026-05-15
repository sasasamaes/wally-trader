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

