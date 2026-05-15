# Agents router


## `GET /api/v1/agents`

<!-- AUTOGEN:START name=GET-api-v1-agents -->
- **Method** `GET`
- **Path** `/api/v1/agents`
- **Auth** Pública
- **Status codes** 200

**Request body:**

_No request body._

**Response:** `_(no body)_`
<!-- AUTOGEN:END name=GET-api-v1-agents -->

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


## `POST /api/v1/agents/name/run`

<!-- AUTOGEN:START name=POST-api-v1-agents-name-run -->
- **Method** `POST`
- **Path** `/api/v1/agents/{name}/run`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 200, 200, 404

**Request body:**

| Campo | Tipo | Required | Default | Descripción |
|---|---|---|---|---|
| `provider` | LLMProvider | ✓ | `—` |  |
| `model` | string | ✓ | `—` | Provider-specific model id, e.g. claude-sonnet-4-6 |
| `input` | object | — | `—` | Agent-specific input payload (symbol, bars, etc.). |
| `profile_id` | string \| null | — | `null` | Optional profile UUID for context isolation. |
| `temperature` | number | — | `0.4` | Temperature |
| `max_tokens` | integer | — | `2048` | Max Tokens |

**Response:** `_(no body)_`
<!-- AUTOGEN:END name=POST-api-v1-agents-name-run -->

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


## `GET /api/v1/agents/runs/run_id`

<!-- AUTOGEN:START name=GET-api-v1-agents-runs-run_id -->
- **Method** `GET`
- **Path** `/api/v1/agents/runs/{run_id}`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 200

**Request body:**

_No request body._

**Response:** `AgentRunSummary`
<!-- AUTOGEN:END name=GET-api-v1-agents-runs-run_id -->

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

