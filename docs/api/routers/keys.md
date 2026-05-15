# Keys router


## `GET /api/v1/keys/llm`

<!-- AUTOGEN:START name=GET-api-v1-keys-llm -->
- **Method** `GET`
- **Path** `/api/v1/keys/llm`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 200

**Request body:**

_No request body._

**Response:** `_(no body)_`
<!-- AUTOGEN:END name=GET-api-v1-keys-llm -->

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


## `POST /api/v1/keys/llm`

<!-- AUTOGEN:START name=POST-api-v1-keys-llm -->
- **Method** `POST`
- **Path** `/api/v1/keys/llm`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 201

**Request body:**

| Campo | Tipo | Required | Default | Descripción |
|---|---|---|---|---|
| `provider` | LLMProvider | ✓ | `—` |  |
| `api_key` | string | ✓ | `—` | Raw API key — never logged. |
| `label` | string \| null | — | `null` | Label |

**Response:** `LLMKeyView`
<!-- AUTOGEN:END name=POST-api-v1-keys-llm -->

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


## `DELETE /api/v1/keys/llm/key_id`

<!-- AUTOGEN:START name=DELETE-api-v1-keys-llm-key_id -->
- **Method** `DELETE`
- **Path** `/api/v1/keys/llm/{key_id}`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 204

**Request body:**

_No request body._

**Response:** `_(no body)_`
<!-- AUTOGEN:END name=DELETE-api-v1-keys-llm-key_id -->

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

